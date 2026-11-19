"""Leakage-safe expanding-window evaluation of all prospective V1 markets."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime

from app.models.hierarchical_poisson import (
    HierarchicalGoalResult,
    fit_hierarchical_poisson,
)
from app.models.hierarchical_scoreline import forecast_hierarchical_fixture
from app.models.scoreline import build_scoreline_distribution
from app.validation.binary_market_metrics import (
    BinaryForecast,
    evaluate_paired_binary_market,
)
from app.validation.dixon_coles import (
    DixonColesObservation,
    estimate_dixon_coles_rho,
)
from app.validation.paired_baselines import (
    ProbabilityForecast,
    evaluate_paired_multiclass,
)
from app.validation.prospective_dataset import (
    ExpandingFold,
    ProspectiveDatasetRow,
    build_expanding_window_folds,
)

MODEL_NAME = "prospective_hierarchical_poisson_dc"
BASELINE_NAME = "prospective_smoothed_competition_poisson"
HALF_LIFE_DAYS = 365.0
TEAM_RIDGE = 0.5
COMPETITION_RIDGE = 0.5
BASELINE_PRIOR_MATCH_STRENGTH = 5.0
MIN_RHO_OOF_FIXTURES = 20
MINIMUM_TRAINING_FIXTURES = 30
INNER_VALIDATION_BLOCK = 25
SCORELINE_MASS_TARGET = 0.99999


def _lineage_rights_valid(
    lineage: dict | None,
    cutoff: datetime,
    required_uses: tuple[str, ...],
) -> bool:
    if not isinstance(lineage, dict):
        return False
    if lineage.get("rights_status") != "APPROVED":
        return False
    valid_from = lineage.get("rights_valid_from")
    valid_until = lineage.get("rights_valid_until")
    if not isinstance(valid_from, str):
        return False
    try:
        valid_from_at = datetime.fromisoformat(valid_from)
        valid_until_at = datetime.fromisoformat(valid_until) if valid_until else None
    except ValueError:
        return False
    if (
        valid_from_at.utcoffset() is None
        or valid_from_at > cutoff
        or (valid_until_at is not None and (
            valid_until_at.utcoffset() is None or valid_until_at <= cutoff
        ))
    ):
        return False
    if not set(required_uses).issubset(set(lineage.get("rights_permitted_uses") or [])):
        return False
    effective_events = []
    for event in lineage.get("rights_status_events") or []:
        if not isinstance(event, dict) or not isinstance(event.get("effective_at"), str):
            return False
        try:
            effective_at = datetime.fromisoformat(event["effective_at"])
        except ValueError:
            return False
        if effective_at.utcoffset() is None:
            return False
        if effective_at <= cutoff:
            event_id = event.get("id", 0)
            if isinstance(event_id, bool) or not isinstance(event_id, int):
                return False
            effective_events.append((effective_at, event_id, event.get("status")))
    return not effective_events or max(
        effective_events, key=lambda item: (item[0], item[1])
    )[2] == "APPROVED"


def _label_evidence_valid(row: ProspectiveDatasetRow) -> bool:
    """Validate label availability without treating history as pre-match data."""
    if row.label is None or row.label_observed_at is None:
        return False
    lineage = row.label_lineage
    if not isinstance(lineage, dict):
        return False
    if row.label_observed_at <= row.kickoff_at:
        return False
    basis = lineage.get("availability_basis")
    if basis == "SYSTEM_OBSERVED_AT":
        observed = lineage.get("system_observed_at")
        if not isinstance(observed, str):
            return False
        try:
            observed_at = datetime.fromisoformat(observed)
        except ValueError:
            return False
        return (
            observed_at.utcoffset() is not None
            and observed_at == row.label_observed_at
            and lineage.get("point_in_time_certifiable") is True
        )
    if (
        not row.validation_eligible
        and basis == "IMPORT_RUN_COMPLETED_AT_TRAINING_ONLY"
        and lineage.get("point_in_time_certifiable") is False
    ):
        inserted = lineage.get("import_run_finished_at")
        import_run_id = lineage.get("import_run_id")
        if not isinstance(inserted, str):
            return False
        try:
            inserted_at = datetime.fromisoformat(inserted)
        except ValueError:
            return False
        return (
            inserted_at.utcoffset() is not None
            and inserted_at == row.label_observed_at
            and isinstance(import_run_id, int)
            and not isinstance(import_run_id, bool)
            and import_run_id > 0
        )
    return False


def _goal_result(row: ProspectiveDatasetRow) -> HierarchicalGoalResult:
    if row.label is None or row.label_observed_at is None:
        raise ValueError("settled prospective label is required")
    return HierarchicalGoalResult(
        fixture_id=row.fixture_id,
        kickoff_at=row.kickoff_at,
        competition_id=row.competition_id,
        home_team_id=row.home_team_id,
        away_team_id=row.away_team_id,
        home_goals=int(row.label["home_goals"]),
        away_goals=int(row.label["away_goals"]),
    )


def _baseline_rates(
    training_rows: Sequence[ProspectiveDatasetRow],
) -> dict[str, tuple[float, float]]:
    if not training_rows:
        raise ValueError("competition baseline requires training rows")
    global_home = sum(int(row.label["home_goals"]) for row in training_rows) / len(training_rows)
    global_away = sum(int(row.label["away_goals"]) for row in training_rows) / len(training_rows)
    if global_home <= 0 or global_away <= 0:
        raise ValueError("training labels do not support positive Poisson baseline rates")
    grouped: dict[str, list[ProspectiveDatasetRow]] = defaultdict(list)
    for row in training_rows:
        grouped[row.competition_id].append(row)
    output = {"__GLOBAL__": (global_home, global_away)}
    for competition_id, rows in grouped.items():
        count = len(rows)
        home_sum = sum(int(row.label["home_goals"]) for row in rows)
        away_sum = sum(int(row.label["away_goals"]) for row in rows)
        strength = BASELINE_PRIOR_MATCH_STRENGTH
        output[competition_id] = (
            (home_sum + strength * global_home) / (count + strength),
            (away_sum + strength * global_away) / (count + strength),
        )
    return output


def _estimate_inner_rho(
    training_rows: Sequence[ProspectiveDatasetRow],
) -> tuple[float, int, str]:
    inner_folds = build_expanding_window_folds(
        training_rows,
        minimum_training_fixtures=MINIMUM_TRAINING_FIXTURES,
        validation_block_fixtures=INNER_VALIDATION_BLOCK,
    )
    row_by_id = {row.fixture_id: row for row in training_rows}
    oof: list[DixonColesObservation] = []
    for fold in inner_folds:
        inner_train = [row_by_id[key] for key in fold.train_fixture_ids]
        inner_validation = [row_by_id[key] for key in fold.validation_fixture_ids]
        if any(
            row.label_observed_at is None
            or row.label_observed_at >= fold.validation_start_at
            or row.kickoff_at >= fold.validation_start_at
            for row in inner_train
        ):
            raise ValueError("inner OOF training label was not available before validation")
        fitted = fit_hierarchical_poisson(
            [_goal_result(row) for row in inner_train],
            as_of=fold.validation_start_at,
            half_life_days=HALF_LIFE_DAYS,
            team_ridge=TEAM_RIDGE,
            competition_ridge=COMPETITION_RIDGE,
        )
        for row in inner_validation:
            rates = fitted.predict(row.home_team_id, row.away_team_id, row.competition_id)
            oof.append(
                DixonColesObservation(
                    home_goals=int(row.label["home_goals"]),
                    away_goals=int(row.label["away_goals"]),
                    home_lambda=rates.home_lambda,
                    away_lambda=rates.away_lambda,
                )
            )
    if len(oof) < MIN_RHO_OOF_FIXTURES:
        return 0.0, len(oof), "ZERO_RHO_INSUFFICIENT_INNER_OOF"
    estimate = estimate_dixon_coles_rho(oof)
    return estimate.rho, len(oof), "INNER_EXPANDING_WINDOW_OOF_ESTIMATED"


def _effective_rho(requested: float, home_lambda: float, away_lambda: float) -> float:
    lower = max(-1.0 / home_lambda, -1.0 / away_lambda, -1.0)
    upper = 1.0 / (home_lambda * away_lambda)
    return min(upper, max(lower, requested))


def _model_distribution(model, row, rho: float):
    rates = model.predict(row.home_team_id, row.away_team_id, row.competition_id)
    applied_rho = _effective_rho(rho, rates.home_lambda, rates.away_lambda)
    for maximum in (12, 16, 20, 24, 30):
        forecast = forecast_hierarchical_fixture(
            model,
            row.home_team_id,
            row.away_team_id,
            row.competition_id,
            rho=applied_rho,
            max_goals=maximum,
        )
        if forecast.scoreline.normalization_mass_before >= SCORELINE_MASS_TARGET:
            return forecast, applied_rho, maximum
    raise ArithmeticError("model scoreline tail mass remains truncated at 30 goals")


def _baseline_distribution(home_lambda: float, away_lambda: float):
    for maximum in (12, 16, 20, 24, 30):
        distribution = build_scoreline_distribution(
            home_lambda, away_lambda, rho=0.0, max_goals=maximum
        )
        if distribution.normalization_mass_before >= SCORELINE_MASS_TARGET:
            return distribution, maximum
    raise ArithmeticError("baseline scoreline tail mass remains truncated at 30 goals")


def evaluate_prospective_model(
    rows: Sequence[ProspectiveDatasetRow],
    folds: Sequence[ExpandingFold],
    *,
    bootstrap_replicates: int = 2000,
    seed: int = 20261118,
) -> dict:
    """Evaluate only labels and features proven available at each fold cutoff."""
    if bootstrap_replicates < 200:
        raise ValueError("at least 200 bootstrap replicates are required")
    row_by_id = {row.fixture_id: row for row in rows}
    if len(row_by_id) != len(rows):
        raise ValueError("duplicate prospective fixture IDs are not allowed")

    multiclass: list[ProbabilityForecast] = []
    model_btts: list[BinaryForecast] = []
    baseline_btts: list[BinaryForecast] = []
    model_totals: dict[str, list[BinaryForecast]] = {
        "OVER_UNDER_1_5": [],
        "OVER_UNDER_2_5": [],
        "OVER_UNDER_3_5": [],
    }
    baseline_totals: dict[str, list[BinaryForecast]] = {
        "OVER_UNDER_1_5": [],
        "OVER_UNDER_2_5": [],
        "OVER_UNDER_3_5": [],
    }
    fold_reports = []
    total_rho_clipped = 0
    evaluation_time = datetime.now(UTC)

    for fold in folds:
        training = [row_by_id[key] for key in fold.train_fixture_ids]
        validation = [row_by_id[key] for key in fold.validation_fixture_ids]
        if not training or not validation:
            raise ValueError("prospective fold cannot have empty training or validation rows")
        if any(
            not _label_evidence_valid(row)
            or row.label_observed_at is None
            or row.label_observed_at >= fold.validation_start_at
            or row.kickoff_at >= fold.validation_start_at
            or not _lineage_rights_valid(
                row.label_lineage, fold.validation_start_at, ("MODEL_TRAINING",)
            )
            for row in training
        ):
            raise ValueError("training labels are not available or rights-valid before validation")
        if any(
            not row.validation_eligible
            or row.prediction_cutoff_at is None
            or row.prediction_cutoff_at >= row.kickoff_at
            or not _label_evidence_valid(row)
            or not _lineage_rights_valid(
                row.label_lineage, evaluation_time, ("MODEL_VALIDATION",)
            )
            for row in validation
        ):
            raise ValueError("validation row lacks a strict pre-match cutoff, settled label or valid rights")
        if len(training) < MINIMUM_TRAINING_FIXTURES:
            raise ValueError("prospective fold is below minimum training sample size")

        rho, rho_oof_count, rho_status = _estimate_inner_rho(training)
        fitted = fit_hierarchical_poisson(
            [_goal_result(row) for row in training],
            as_of=fold.validation_start_at,
            half_life_days=HALF_LIFE_DAYS,
            team_ridge=TEAM_RIDGE,
            competition_ridge=COMPETITION_RIDGE,
        )
        baseline = _baseline_rates(training)
        clipped = 0
        fold_caps_model = 0
        fold_caps_baseline = 0

        for row in validation:
            model_forecast, applied_rho, model_cap = _model_distribution(fitted, row, rho)
            if abs(applied_rho - rho) > 1e-12:
                clipped += 1
            rates = baseline.get(row.competition_id, baseline["__GLOBAL__"])
            baseline_forecast, baseline_cap = _baseline_distribution(*rates)
            fold_caps_model = max(fold_caps_model, model_cap)
            fold_caps_baseline = max(fold_caps_baseline, baseline_cap)

            actual_outcome = (
                "HOME" if row.label["home_win"]
                else "DRAW" if row.label["draw"]
                else "AWAY"
            )
            model_markets = model_forecast.markets
            baseline_markets = baseline_forecast.market_probabilities()
            multiclass.extend((
                ProbabilityForecast(
                    fixture_id=row.fixture_id,
                    model_name=MODEL_NAME,
                    probabilities=model_markets["1X2"],
                    outcome=actual_outcome,
                    competition_id=row.competition_id,
                ),
                ProbabilityForecast(
                    fixture_id=row.fixture_id,
                    model_name=BASELINE_NAME,
                    probabilities=baseline_markets["1X2"],
                    outcome=actual_outcome,
                    competition_id=row.competition_id,
                ),
            ))
            model_btts.append(BinaryForecast(
                row.fixture_id, row.competition_id, bool(row.label["btts"]),
                model_markets["BTTS"]["YES"],
            ))
            baseline_btts.append(BinaryForecast(
                row.fixture_id, row.competition_id, bool(row.label["btts"]),
                baseline_markets["BTTS"]["YES"],
            ))
            total_goals = int(row.label["home_goals"]) + int(row.label["away_goals"])
            for market_name, line in (
                ("OVER_UNDER_1_5", 1.5),
                ("OVER_UNDER_2_5", 2.5),
                ("OVER_UNDER_3_5", 3.5),
            ):
                actual_over = total_goals > line
                totals_key = f"TOTALS_{str(line).replace('.', '_')}"
                model_totals[market_name].append(BinaryForecast(
                    row.fixture_id,
                    row.competition_id,
                    actual_over,
                    model_markets[totals_key]["OVER"],
                ))
                baseline_totals[market_name].append(BinaryForecast(
                    row.fixture_id,
                    row.competition_id,
                    actual_over,
                    baseline_markets[totals_key]["OVER"],
                ))

        total_rho_clipped += clipped
        fold_reports.append({
            "fold_number": fold.fold_number,
            "training_fixtures": len(training),
            "validation_fixtures": len(validation),
            "training_label_observed_cutoff": fold.train_cutoff_at.isoformat(),
            "validation_start": fold.validation_start_at.isoformat(),
            "validation_end": fold.validation_end_at.isoformat(),
            "rho": rho,
            "rho_estimation_status": rho_status,
            "rho_inner_oof_fixtures": rho_oof_count,
            "rho_clipped_validation_fixtures": clipped,
            "optimizer": {
                "converged": fitted.optimizer_converged,
                "iterations": fitted.optimizer_iterations,
                "gradient_norm": fitted.optimizer_gradient_norm,
            },
            "maximum_scoreline_grid_model": fold_caps_model,
            "maximum_scoreline_grid_baseline": fold_caps_baseline,
        })

    if not model_btts:
        return {
            "evaluation_type": "PROSPECTIVE_EXPANDING_WINDOW_MARKET_EVALUATION",
            "status": "INSUFFICIENT_PROSPECTIVE_DATA",
            "fixtures": 0,
            "folds": fold_reports,
            "production_promotion": "LOCKED",
            "value_betting": "LOCKED",
            "release_eligible": False,
        }

    multiclass_report = evaluate_paired_multiclass(
        multiclass,
        model_name=MODEL_NAME,
        baseline_name=BASELINE_NAME,
        bootstrap_replicates=bootstrap_replicates,
        seed=seed,
    )
    btts_report = evaluate_paired_binary_market(
        model_btts, baseline_btts,
        bootstrap_replicates=bootstrap_replicates,
        seed=seed + 1,
    )
    totals_reports = {
        market_name: evaluate_paired_binary_market(
            model_totals[market_name],
            baseline_totals[market_name],
            bootstrap_replicates=bootstrap_replicates,
            seed=seed + index + 2,
        )
        for index, market_name in enumerate(
            ("OVER_UNDER_1_5", "OVER_UNDER_2_5", "OVER_UNDER_3_5")
        )
    }
    return {
        "evaluation_type": "PROSPECTIVE_EXPANDING_WINDOW_MARKET_EVALUATION",
        "status": "RESEARCH_ONLY_NOT_PRODUCTION_APPROVAL",
        "evaluation_time": evaluation_time.isoformat(),
        "fixtures": len(model_btts),
        "historical_training_only_rows": sum(
            1 for row in rows if not row.validation_eligible
        ),
        "folds": fold_reports,
        "markets": {
            "1X2": multiclass_report,
            "BTTS": btts_report,
            **totals_reports,
        },
        "scoreline_grid": {
            "minimum_tail_mass": SCORELINE_MASS_TARGET,
            "max_model_rho_clipped_fixtures": total_rho_clipped,
        },
        "training_protocol": {
            "outer": "PROSPECTIVE_EXPANDING_WINDOW",
            "inner_rho": "INNER_EXPANDING_WINDOW_OUT_OF_FOLD",
            "label_availability": "SYSTEM_OBSERVED_AT_STRICTLY_BEFORE_OUTER_VALIDATION_START",
            "pre_match_features": "STRICTLY_BEFORE_TARGET_KICKOFF",
            "historical_training_labels": "DATABASE_INSERTED_AT_TRAINING_ONLY; NEVER_USED_AS_PRE_MATCH_FEATURES_OR_VALIDATION_ROWS",
            "hyperparameters": {
                "half_life_days": HALF_LIFE_DAYS,
                "team_ridge": TEAM_RIDGE,
                "competition_ridge": COMPETITION_RIDGE,
            },
            "baseline": "COMPETITION_ONLY_POISSON_WITH_GLOBAL_MEAN_PRIOR_STRENGTH_5",
            "bookmaker_odds_used": False,
        },
        "confidence_intervals": {
            "method": "PAIRED_COMPETITION_STRATIFIED_BOOTSTRAP",
            "replicates": bootstrap_replicates,
            "seed": seed,
            "descriptive_only": True,
            "release_test": False,
        },
        "production_promotion": "LOCKED",
        "value_betting": "LOCKED",
        "release_eligible": False,
    }
