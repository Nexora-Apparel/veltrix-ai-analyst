"""Competition-aware, partially pooled Poisson goal-rate model.

Parameters are fitted by minimizing recency-weighted Poisson negative
log-likelihood plus ridge penalties. Positive ridge penalties identify team
and competition effects without post-step recentering; retaining the optimizer
in the unconstrained parameterization keeps the gradient consistent with the
objective. Unseen teams receive zero team effects while retaining learned
competition/global context.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from math import exp, isfinite, lgamma, log, sqrt


@dataclass(frozen=True, slots=True)
class HierarchicalGoalResult:
    fixture_id: str
    kickoff_at: datetime
    competition_id: str
    home_team_id: str
    away_team_id: str
    home_goals: int
    away_goals: int

    def __post_init__(self) -> None:
        if any(not value.strip() for value in (
            self.fixture_id, self.competition_id, self.home_team_id, self.away_team_id
        )):
            raise ValueError("fixture, competition and team identifiers are required")
        if self.home_team_id == self.away_team_id:
            raise ValueError("home and away teams must differ")
        if self.kickoff_at.tzinfo is None or self.kickoff_at.utcoffset() is None:
            raise ValueError("kickoff_at must be timezone-aware")
        if self.home_goals < 0 or self.away_goals < 0:
            raise ValueError("goals cannot be negative")


@dataclass(frozen=True, slots=True)
class HierarchicalGoalRates:
    home_lambda: float
    away_lambda: float
    competition_seen: bool
    home_team_history: int
    away_team_history: int
    calculation_mode: str

    def __post_init__(self) -> None:
        if self.calculation_mode not in {
            "TEAM_AND_COMPETITION_HISTORY",
            "ONE_SIDED_TEAM_HISTORY",
            "COMPETITION_ONLY",
            "TEAM_HISTORY_GLOBAL_CONTEXT",
            "GLOBAL_CONTEXT_ONLY",
        }:
            raise ValueError("unknown hierarchical calculation mode")
        if self.home_team_history < 0 or self.away_team_history < 0:
            raise ValueError("team history counts cannot be negative")


@dataclass(frozen=True, slots=True)
class HierarchicalPoissonModel:
    global_intercept: float
    competition_effects: dict[str, float]
    home_advantage: float
    attack: dict[str, float]
    defence: dict[str, float]
    team_match_counts: dict[str, int]
    competition_match_counts: dict[str, int]
    training_fixtures: int
    training_cutoff_at: datetime
    half_life_days: float
    team_ridge: float
    competition_ridge: float
    optimizer_converged: bool
    optimizer_iterations: int
    optimizer_gradient_norm: float
    optimizer_relative_objective_change: float | None

    def predict(
        self, home_team_id: str, away_team_id: str, competition_id: str
    ) -> HierarchicalGoalRates:
        if not home_team_id or not away_team_id or not competition_id:
            raise ValueError("fixture identifiers are required")
        if home_team_id == away_team_id:
            raise ValueError("home and away teams must differ")
        competition_seen = competition_id in self.competition_effects
        shared = self.global_intercept + self.competition_effects.get(competition_id, 0.0)
        home_eta = (
            shared + self.home_advantage
            + self.attack.get(home_team_id, 0.0) - self.defence.get(away_team_id, 0.0)
        )
        away_eta = (
            shared + self.attack.get(away_team_id, 0.0)
            - self.defence.get(home_team_id, 0.0)
        )
        if not (-20.0 < home_eta < 20.0 and -20.0 < away_eta < 20.0):
            raise ArithmeticError("predicted goal-rate linear predictor outside safe range")
        home_history = self.team_match_counts.get(home_team_id, 0)
        away_history = self.team_match_counts.get(away_team_id, 0)
        if competition_seen and home_history > 0 and away_history > 0:
            calculation_mode = "TEAM_AND_COMPETITION_HISTORY"
        elif competition_seen and (home_history > 0 or away_history > 0):
            calculation_mode = "ONE_SIDED_TEAM_HISTORY"
        elif competition_seen:
            calculation_mode = "COMPETITION_ONLY"
        elif home_history > 0 or away_history > 0:
            calculation_mode = "TEAM_HISTORY_GLOBAL_CONTEXT"
        else:
            calculation_mode = "GLOBAL_CONTEXT_ONLY"
        return HierarchicalGoalRates(
            home_lambda=exp(home_eta),
            away_lambda=exp(away_eta),
            competition_seen=competition_seen,
            home_team_history=home_history,
            away_team_history=away_history,
            calculation_mode=calculation_mode,
        )


def _time_weight(age_days: float, half_life_days: float) -> float:
    return exp(-log(2.0) * max(0.0, age_days) / half_life_days)


def _objective(
    rows: list[HierarchicalGoalResult],
    weights: list[float],
    total_weight: float,
    team_index: dict[str, int],
    competition_index: dict[str, int],
    global_intercept: float,
    home_advantage: float,
    competition_effects: list[float],
    attack: list[float],
    defence: list[float],
    team_ridge: float,
    competition_ridge: float,
) -> float:
    loss = 0.0
    for row, weight in zip(rows, weights):
        home = team_index[row.home_team_id]
        away = team_index[row.away_team_id]
        comp = competition_index[row.competition_id]
        shared = global_intercept + competition_effects[comp]
        home_eta = shared + home_advantage + attack[home] - defence[away]
        away_eta = shared + attack[away] - defence[home]
        if not (-20.0 < home_eta < 20.0 and -20.0 < away_eta < 20.0):
            return float("inf")
        home_rate, away_rate = exp(home_eta), exp(away_eta)
        loss += weight * (
            home_rate - row.home_goals * home_eta + lgamma(row.home_goals + 1)
            + away_rate - row.away_goals * away_eta + lgamma(row.away_goals + 1)
        )
    penalty = 0.5 * competition_ridge * sum(value * value for value in competition_effects)
    penalty += 0.5 * team_ridge * (
        sum(value * value for value in attack) + sum(value * value for value in defence)
    )
    return loss / total_weight + penalty


def _lbfgs_minimize(
    rows: list[HierarchicalGoalResult],
    weights: list[float],
    total_weight: float,
    team_index: dict[str, int],
    competition_index: dict[str, int],
    initial: list[float],
    team_ridge: float,
    competition_ridge: float,
    *,
    max_iterations: int,
    tolerance: float,
    history_size: int = 10,
) -> tuple[list[float], bool, int, float]:
    """Pure-Python L-BFGS with Armijo backtracking on the unchanged averaged objective."""
    from math import sqrt

    competition_count = len(competition_index)
    team_count = len(team_index)

    def unpack(vector: list[float]):
        return (
            vector[0], vector[1],
            vector[2:2 + competition_count],
            vector[2 + competition_count:2 + competition_count + team_count],
            vector[2 + competition_count + team_count:],
        )

    def evaluate(vector: list[float]) -> tuple[float, list[float]]:
        intercept, home_advantage, competitions, attack, defence = unpack(vector)
        gradient = [0.0] * len(vector)
        gc = gradient[2:2 + competition_count]
        ga = gradient[2 + competition_count:2 + competition_count + team_count]
        gd = gradient[2 + competition_count + team_count:]
        gi = gh = 0.0
        loss = 0.0
        for row, weight in zip(rows, weights):
            h = team_index[row.home_team_id]
            a = team_index[row.away_team_id]
            c = competition_index[row.competition_id]
            shared = intercept + competitions[c]
            eh = shared + home_advantage + attack[h] - defence[a]
            ea = shared + attack[a] - defence[h]
            if not (-20.0 < eh < 20.0 and -20.0 < ea < 20.0):
                return float("inf"), [float("nan")] * len(vector)
            home_rate, away_rate = exp(eh), exp(ea)
            loss += weight * (
                home_rate - row.home_goals * eh + lgamma(row.home_goals + 1)
                + away_rate - row.away_goals * ea + lgamma(row.away_goals + 1)
            )
            error_h = weight * (home_rate - row.home_goals) / total_weight
            error_a = weight * (away_rate - row.away_goals) / total_weight
            gi += error_h + error_a
            gh += error_h
            gc[c] += error_h + error_a
            ga[h] += error_h
            gd[a] -= error_h
            ga[a] += error_a
            gd[h] -= error_a
        penalty = 0.5 * competition_ridge * sum(value * value for value in competitions)
        penalty += 0.5 * team_ridge * (
            sum(value * value for value in attack)
            + sum(value * value for value in defence)
        )
        for index, value in enumerate(competitions):
            gc[index] += competition_ridge * value
        for index, value in enumerate(attack):
            ga[index] += team_ridge * value
        for index, value in enumerate(defence):
            gd[index] += team_ridge * value
        gradient[0] = gi
        gradient[1] = gh
        gradient[2:2 + competition_count] = gc
        gradient[2 + competition_count:2 + competition_count + team_count] = ga
        gradient[2 + competition_count + team_count:] = gd
        return loss / total_weight + penalty, gradient

    def dot(left: list[float], right: list[float]) -> float:
        return sum(a * b for a, b in zip(left, right))

    def norm(vector: list[float]) -> float:
        return sqrt(dot(vector, vector))

    vector = initial[:]
    value, gradient = evaluate(vector)
    s_history: list[list[float]] = []
    y_history: list[list[float]] = []
    rho_history: list[float] = []
    gradient_norm = norm(gradient)
    if gradient_norm <= tolerance:
        return vector, True, 0, gradient_norm

    for iteration in range(1, max_iterations + 1):
        q = gradient[:]
        alphas: list[float] = []
        for s_vec, y_vec, rho in zip(
            reversed(s_history), reversed(y_history), reversed(rho_history)
        ):
            alpha = rho * dot(s_vec, q)
            alphas.append(alpha)
            q = [v - alpha * y for v, y in zip(q, y_vec)]
        if s_history:
            sy = dot(s_history[-1], y_history[-1])
            yy = dot(y_history[-1], y_history[-1])
            scale = sy / yy if yy > 0 else 1.0
        else:
            scale = 1.0
        direction = [scale * v for v in q]
        for index, (s_vec, y_vec, rho) in enumerate(
            zip(s_history, y_history, rho_history)
        ):
            beta = rho * dot(y_vec, direction)
            alpha = alphas[len(alphas) - 1 - index]
            direction = [
                value + s * (alpha - beta)
                for value, s in zip(direction, s_vec)
            ]
        direction = [-value for value in direction]
        directional_derivative = dot(gradient, direction)
        if not isfinite(directional_derivative) or directional_derivative >= 0:
            s_history.clear()
            y_history.clear()
            rho_history.clear()
            direction = [-value for value in gradient]
            directional_derivative = -dot(gradient, gradient)

        step = 1.0
        accepted = False
        for _ in range(50):
            candidate = [x + step * d for x, d in zip(vector, direction)]
            next_value, next_gradient = evaluate(candidate)
            if (
                isfinite(next_value)
                and all(isfinite(x) for x in next_gradient)
                and next_value <= value + 1e-4 * step * directional_derivative
            ):
                accepted = True
                break
            step *= 0.5
        if not accepted:
            return vector, False, iteration, gradient_norm

        s_vec = [new - old for new, old in zip(candidate, vector)]
        y_vec = [new - old for new, old in zip(next_gradient, gradient)]
        curvature = dot(s_vec, y_vec)
        if curvature > 1e-12:
            if len(s_history) == history_size:
                s_history.pop(0)
                y_history.pop(0)
                rho_history.pop(0)
            s_history.append(s_vec)
            y_history.append(y_vec)
            rho_history.append(1.0 / curvature)
        vector, value, gradient = candidate, next_value, next_gradient
        gradient_norm = norm(gradient)
        if gradient_norm <= tolerance:
            return vector, True, iteration, gradient_norm
    return vector, False, max_iterations, gradient_norm



def _solve_linear_system(matrix: list[list[float]], rhs: list[float]) -> list[float]:
    """Solve a dense system by Gaussian elimination with partial pivoting."""
    size = len(rhs)
    work = [row[:] + [rhs[i]] for i, row in enumerate(matrix)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(work[row][column]))
        pivot_value = work[pivot][column]
        if not isfinite(pivot_value) or abs(pivot_value) <= 1e-14:
            raise ArithmeticError("singular damped Newton system")
        if pivot != column:
            work[column], work[pivot] = work[pivot], work[column]
        pivot_row = work[column]
        for row_index in range(column + 1, size):
            row = work[row_index]
            factor = row[column] / pivot_row[column]
            if factor == 0.0:
                continue
            row[column] = 0.0
            for j in range(column + 1, size + 1):
                row[j] -= factor * pivot_row[j]
    solution = [0.0] * size
    for i in range(size - 1, -1, -1):
        solution[i] = (
            work[i][size] - sum(work[i][j] * solution[j] for j in range(i + 1, size))
        ) / work[i][i]
    if not all(isfinite(value) for value in solution):
        raise ArithmeticError("non-finite damped Newton direction")
    return solution


def _newton_minimize(
    rows: list[HierarchicalGoalResult],
    weights: list[float],
    total_weight: float,
    team_index: dict[str, int],
    competition_index: dict[str, int],
    initial: list[float],
    team_ridge: float,
    competition_ridge: float,
    *,
    max_iterations: int,
    tolerance: float,
    relative_objective_tolerance: float = 1e-10,
) -> tuple[list[float], bool, int, float, float]:
    """Damped Newton on the unchanged averaged Poisson objective."""
    from math import sqrt

    competition_count = len(competition_index)
    team_count = len(team_index)
    size = 2 + competition_count + 2 * team_count
    comp_start = 2
    attack_start = comp_start + competition_count
    defence_start = attack_start + team_count

    def evaluate(vector: list[float], with_hessian: bool):
        gradient = [0.0] * size
        hessian = [[0.0] * size for _ in range(size)] if with_hessian else None
        intercept, home_advantage = vector[0], vector[1]
        loss = 0.0
        for row, weight in zip(rows, weights):
            home = team_index[row.home_team_id]
            away = team_index[row.away_team_id]
            comp = competition_index[row.competition_id]
            shared = intercept + vector[comp_start + comp]
            eta_home = (
                shared + home_advantage
                + vector[attack_start + home] - vector[defence_start + away]
            )
            eta_away = (
                shared + vector[attack_start + away] - vector[defence_start + home]
            )
            if not (-20.0 < eta_home < 20.0 and -20.0 < eta_away < 20.0):
                return float("inf"), [float("nan")] * size, None
            rate_home, rate_away = exp(eta_home), exp(eta_away)
            loss += weight * (
                rate_home - row.home_goals * eta_home + lgamma(row.home_goals + 1)
                + rate_away - row.away_goals * eta_away + lgamma(row.away_goals + 1)
            )
            error_home = weight * (rate_home - row.home_goals) / total_weight
            error_away = weight * (rate_away - row.away_goals) / total_weight
            x_home = (
                (0, 1.0), (1, 1.0), (comp_start + comp, 1.0),
                (attack_start + home, 1.0), (defence_start + away, -1.0),
            )
            x_away = (
                (0, 1.0), (comp_start + comp, 1.0),
                (attack_start + away, 1.0), (defence_start + home, -1.0),
            )
            for index, value in x_home:
                gradient[index] += error_home * value
            for index, value in x_away:
                gradient[index] += error_away * value
            if hessian is not None:
                scale_home = weight * rate_home / total_weight
                scale_away = weight * rate_away / total_weight
                for i, vi in x_home:
                    for j, vj in x_home:
                        hessian[i][j] += scale_home * vi * vj
                for i, vi in x_away:
                    for j, vj in x_away:
                        hessian[i][j] += scale_away * vi * vj

        penalty = 0.0
        for index in range(comp_start, attack_start):
            value = vector[index]
            penalty += 0.5 * competition_ridge * value * value
            gradient[index] += competition_ridge * value
            if hessian is not None:
                hessian[index][index] += competition_ridge
        for index in range(attack_start, size):
            value = vector[index]
            penalty += 0.5 * team_ridge * value * value
            gradient[index] += team_ridge * value
            if hessian is not None:
                hessian[index][index] += team_ridge
        return loss / total_weight + penalty, gradient, hessian

    def norm(values: list[float]) -> float:
        return sqrt(sum(value * value for value in values))

    vector = initial[:]
    value, gradient, _ = evaluate(vector, False)
    gradient_norm = norm(gradient)
    stable_steps = 0
    relative_change = float("inf")
    if gradient_norm <= tolerance:
        # No accepted step exists to establish objective stability; require a
        # deterministic zero-step confirmation under the same fixed criteria.
        confirmed_value, confirmed_gradient, _ = evaluate(vector, False)
        confirmed_norm = norm(confirmed_gradient)
        if confirmed_norm <= tolerance and abs(confirmed_value - value) <= relative_objective_tolerance:
            return vector, True, 0, confirmed_norm, 0.0

    for iteration in range(1, max_iterations + 1):
        value, gradient, hessian = evaluate(vector, True)
        gradient_norm = norm(gradient)
        if not isfinite(value) or not isfinite(gradient_norm):
            raise ArithmeticError("non-finite Newton objective or gradient")
        accepted = False
        damping = 1e-10
        direction = None
        directional_derivative = float("inf")
        for _ in range(10):
            damped = [row[:] for row in hessian]
            for diagonal in range(size):
                damped[diagonal][diagonal] += damping
            try:
                candidate_direction = _solve_linear_system(damped, [-g for g in gradient])
            except ArithmeticError:
                damping *= 10.0
                continue
            directional = sum(g * d for g, d in zip(gradient, candidate_direction))
            if isfinite(directional) and directional < 0.0:
                direction = candidate_direction
                directional_derivative = directional
                break
            damping *= 10.0
        if direction is None:
            raise ArithmeticError("damped Newton could not obtain a descent direction")

        step = 1.0
        for _ in range(50):
            candidate = [x + step * d for x, d in zip(vector, direction)]
            next_value, next_gradient, _ = evaluate(candidate, False)
            if (
                isfinite(next_value)
                and all(isfinite(g) for g in next_gradient)
                and next_value <= value + 1e-4 * step * directional_derivative
            ):
                accepted = True
                break
            step *= 0.5
        if not accepted:
            raise ArithmeticError(
                f"damped Newton Armijo line search failed at iteration {iteration} "
                f"(gradient_norm={gradient_norm:.6g}, relative_objective_change={relative_change:.6g})"
            )

        relative_change = abs(next_value - value) / max(1.0, abs(value))
        vector = candidate
        gradient_norm = norm(next_gradient)
        if gradient_norm <= tolerance and relative_change <= relative_objective_tolerance:
            stable_steps += 1
        else:
            stable_steps = 0
        if stable_steps >= 2:
            return vector, True, iteration, gradient_norm

    raise ArithmeticError(
        f"damped Newton did not converge after {max_iterations} iterations "
        f"(gradient_norm={gradient_norm:.6g})"
    )


def fit_hierarchical_poisson(
    results: Iterable[HierarchicalGoalResult],
    *,
    as_of: datetime | None = None,
    half_life_days: float = 180.0,
    team_ridge: float = 0.5,
    competition_ridge: float = 2.0,
    learning_rate: float = 1.0,
    max_iterations: int = 4000,
    tolerance: float = 1e-7,
    optimizer: str = "gradient_descent",
) -> HierarchicalPoissonModel:
    """Fit the penalized likelihood with gradient descent, L-BFGS, or damped Newton.

    Hyperparameters are not production defaults; select them on chronological
    development folds and freeze them before prospective evaluation.
    """
    rows = list(results)
    if not rows:
        raise ValueError("at least one completed result is required")
    if (
        not isfinite(half_life_days) or half_life_days <= 0
        or not isfinite(team_ridge) or team_ridge < 0
        or not isfinite(competition_ridge) or competition_ridge < 0
        or not isfinite(learning_rate) or learning_rate <= 0
        or max_iterations < 1 or not isfinite(tolerance) or tolerance <= 0
        or optimizer not in {"gradient_descent", "lbfgs", "newton"}
    ):
        raise ValueError("invalid optimizer configuration")
    if len({row.fixture_id for row in rows}) != len(rows):
        raise ValueError("duplicate fixture IDs are not allowed")
    latest = as_of or max(row.kickoff_at for row in rows)
    if latest.tzinfo is None or latest.utcoffset() is None:
        raise ValueError("as_of must be timezone-aware")
    if any(row.kickoff_at > latest for row in rows):
        raise ValueError("training result occurs after as_of")
    rows.sort(key=lambda row: (row.kickoff_at, row.fixture_id))

    teams = tuple(sorted({team for row in rows for team in (row.home_team_id, row.away_team_id)}))
    competitions = tuple(sorted({row.competition_id for row in rows}))
    team_index = {team: index for index, team in enumerate(teams)}
    competition_index = {name: index for index, name in enumerate(competitions)}
    team_count, competition_count = len(teams), len(competitions)
    weights = [
        _time_weight((latest - row.kickoff_at).total_seconds() / 86400, half_life_days)
        for row in rows
    ]
    total_weight = sum(weights)
    weighted_goals = sum(
        weight * (row.home_goals + row.away_goals) for row, weight in zip(rows, weights)
    )
    if total_weight <= 0 or weighted_goals <= 0:
        raise ValueError("training data has no positive weighted goal signal")

    global_intercept = log(weighted_goals / (2.0 * total_weight))
    home_advantage = 0.0
    competition_effects = [0.0] * competition_count
    attack = [0.0] * team_count
    defence = [0.0] * team_count
    current_loss = _objective(
        rows, weights, total_weight, team_index, competition_index,
        global_intercept, home_advantage, competition_effects, attack, defence,
        team_ridge, competition_ridge,
    )
    converged = False
    gradient_norm = float("inf")
    relative_objective_change: float | None = None
    iterations = 0

    if optimizer in {"lbfgs", "newton"}:
        initial = [
            global_intercept, home_advantage,
            *competition_effects, *attack, *defence,
        ]
        if optimizer == "lbfgs":
            fitted, converged, iterations, gradient_norm = _lbfgs_minimize(
                rows, weights, total_weight, team_index, competition_index, initial,
                team_ridge, competition_ridge,
                max_iterations=max_iterations, tolerance=tolerance,
            )
        else:
            fitted, converged, iterations, gradient_norm, relative_objective_change = _newton_minimize(
                rows, weights, total_weight, team_index, competition_index, initial,
                team_ridge, competition_ridge,
                max_iterations=min(max_iterations, 200), tolerance=tolerance,
            )
        competition_effects = fitted[2:2 + competition_count]
        attack = fitted[2 + competition_count:2 + competition_count + team_count]
        defence = fitted[2 + competition_count + team_count:]
        global_intercept, home_advantage = fitted[0], fitted[1]
    else:
        for iteration in range(1, max_iterations + 1):
            gi = gh = 0.0
            gc = [competition_ridge * value for value in competition_effects]
            ga = [team_ridge * value for value in attack]
            gd = [team_ridge * value for value in defence]
            for row, weight in zip(rows, weights):
                h, a = team_index[row.home_team_id], team_index[row.away_team_id]
                c = competition_index[row.competition_id]
                shared = global_intercept + competition_effects[c]
                eh = shared + home_advantage + attack[h] - defence[a]
                ea = shared + attack[a] - defence[h]
                if not (-20.0 < eh < 20.0 and -20.0 < ea < 20.0):
                    raise ArithmeticError("optimizer linear predictor outside safe range")
                error_h = weight * (exp(eh) - row.home_goals) / total_weight
                error_a = weight * (exp(ea) - row.away_goals) / total_weight
                gi += error_h + error_a
                gh += error_h
                gc[c] += error_h + error_a
                ga[h] += error_h
                gd[a] -= error_h
                ga[a] += error_a
                gd[h] -= error_a
            gradient_norm = sqrt(
                gi * gi + gh * gh + sum(x*x for x in gc)
                + sum(x*x for x in ga) + sum(x*x for x in gd)
            )
            if not isfinite(gradient_norm):
                raise ArithmeticError("non-finite optimizer gradient")
            if gradient_norm <= tolerance:
                converged = True
                iterations = iteration
                break
            step = learning_rate
            accepted = False
            for _ in range(40):
                next_intercept = global_intercept - step * gi
                next_home = home_advantage - step * gh
                next_comp = [v - step * g for v, g in zip(competition_effects, gc)]
                next_attack = [v - step * g for v, g in zip(attack, ga)]
                next_defence = [v - step * g for v, g in zip(defence, gd)]
                next_loss = _objective(
                    rows, weights, total_weight, team_index, competition_index,
                    next_intercept, next_home, next_comp, next_attack, next_defence,
                    team_ridge, competition_ridge,
                )
                if isfinite(next_loss) and next_loss < current_loss:
                    global_intercept, home_advantage = next_intercept, next_home
                    competition_effects, attack, defence = next_comp, next_attack, next_defence
                    current_loss = next_loss
                    accepted = True
                    break
                step *= 0.5
            if not accepted:
                if gradient_norm <= tolerance * 10:
                    converged = True
                    iterations = iteration
                    break
                raise ArithmeticError("optimizer line search failed before convergence")
            iterations = iteration

    if not converged:
        raise ArithmeticError(
            f"hierarchical Poisson optimizer did not converge after {max_iterations} iterations "
            f"(gradient_norm={gradient_norm:.6g})"
        )

    team_counts = {team: 0 for team in teams}
    competition_counts = {name: 0 for name in competitions}
    for row in rows:
        team_counts[row.home_team_id] += 1
        team_counts[row.away_team_id] += 1
        competition_counts[row.competition_id] += 1
    return HierarchicalPoissonModel(
        global_intercept=global_intercept,
        competition_effects=dict(zip(competitions, competition_effects)),
        home_advantage=home_advantage,
        attack=dict(zip(teams, attack)),
        defence=dict(zip(teams, defence)),
        team_match_counts=team_counts,
        competition_match_counts=competition_counts,
        training_fixtures=len(rows),
        training_cutoff_at=latest,
        half_life_days=half_life_days,
        team_ridge=team_ridge,
        competition_ridge=competition_ridge,
        optimizer_converged=converged,
        optimizer_iterations=iterations,
        optimizer_gradient_norm=gradient_norm,
        optimizer_relative_objective_change=relative_objective_change,
    )
