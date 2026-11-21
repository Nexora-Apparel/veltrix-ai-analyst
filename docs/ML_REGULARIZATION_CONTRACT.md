# VELTRIX hierarchical goal-model regularization contract

**Status:** implementation contract draft; hyperparameter values are not approved or frozen.  
**Applies to:** candidate hierarchical Poisson / Dixon–Coles goal-rate model.  
**Release state:** all candidate fits remain quarantined and research-only.

## 1. Likelihood and objective

For fixture (i) in competition (c(i)), model the home and away goals as conditionally Poisson:

[
Y_{Hi}\sim operatorname{Poisson}(\lambda_{Hi}),\qquad
Y_{Ai}\sim operatorname{Poisson}(\lambda_{Ai}).
]

Use a competition scoring intercept (\alpha_c), team attack (a_{t,c}), team defence (d_{t,c}), global home advantage (h_0), and competition home deviation (\delta_c):

[
\log\lambda_{Hi}=\alpha_c+h_0+\delta_c+a_{H,c}-d_{A,c}
]
[
\log\lambda_{Ai}=\alpha_c+a_{A,c}-d_{H,c}.
]

The objective is the **unnormalized** recency-weighted Poisson negative log likelihood plus explicit Gaussian-prior penalties:

[
J(\theta)=\sum_i w_i\{\ell_{Hi}(\theta)+\ell_{Ai}(\theta)\}
+\frac12\sum_{c,t}\tau_{A,c}a_{t,c}^2
+\frac12\sum_{c,t}\tau_{D,c}d_{t,c}^2
+\frac12\sum_c\tau_{C,c}q_c^2
+\frac12\sum_c\tau_{H,c}\delta_c^2
+\frac12\tau_{H0}h_0^2.
]

Here (q_c) is the competition scoring deviation around the global scoring intercept. The exact identifiability constraints and parameterization must be implemented consistently with the objective; no post-optimization recentering that changes the objective is allowed.

## 2. Pseudo-match units and information scales

For each competition and training cutoff, calculate its league mean goals per team per match using only that fold's training labels:

[
\mu_c=\frac{\sum_{i:c(i)=c}w_i(Y_{Hi}+Y_{Ai})}
{2\sum_{i:c(i)=c}w_i}.
]

The mean is recomputed from the training fold only; it must never use validation/holdout labels.

Use one fixed (k) per parameter type across teams. There is no per-team (k), no match-count-dependent prior strength, and no manual adjustment for an individual team's sample size.

- **Team attack:** one team contributes one scoring observation per fixture. Its approximate information per match is (\mu_c). Set (\tau_{A,c}=k_A\mu_c).
- **Team defence:** one team contributes one opponent-scoring observation per fixture. Its approximate information per match is (\mu_c). Set (\tau_{D,c}=k_D\mu_c).
- **Competition scoring effect:** the effect enters both home and away goal rates, so it touches two scoring observations per fixture. Its approximate information per match is (2\mu_c). Set (\tau_{C,c}=k_C(2\mu_c)). Do not reuse the team scale.
- **Competition home deviation:** it enters the home-goal rate only, so its approximate information per match is (\mu_c). Set (\tau_{H,c}=k_H\mu_c), shrinking each (\delta_c) toward zero around the global home effect.
- **Global home effect:** set a separate explicit zero-centred prior (\tau_{H0}=k_{H0}\mu_{ref}), where (\mu_{ref}) is the pre-defined training-only pooled league mean. This prevents an unpenalized global home effect from absorbing all systematic home advantage.

The (k) values are prior strengths in approximate equivalent matches. They are common by parameter type and are selected only on chronological development folds. No numeric (k) is approved by this document.

The recency weights (w_i) apply only to the likelihood. They do not rescale (k), and no team receives a different prior because it has more or fewer observed matches.

## 3. Identification and competition handling

- The candidate uses a prior-anchored parameterization rather than post-fit recentering or hard sum-to-zero constraints. Every competition-scoped team attack and defence effect has a proper zero-centred Gaussian prior with strictly positive precision; each competition scoring deviation has a proper zero-centred prior; each competition home deviation is shrunk toward the globally estimated home effect; and the global home effect has its own proper prior.
- These positive prior precisions anchor the otherwise likelihood-invariant common attack/defence shift and competition/global intercept shifts, yielding a unique penalized MAP solution. The global scoring intercept remains identified by the goal likelihood. The fitter rejects any zero k because it would remove the prior anchor for that parameter family.
- Competition scoring deviations are therefore identified relative to the global scoring intercept by their proper priors, not by an after-the-fact centering operation.
- Competition home effects are (h_c=h_0+\delta_c); deviations are shrunk toward the single global (h_0).
- A team is competition-scoped until canonical identity and cross-competition transfer evidence justify sharing. Promotion/relegation does not silently copy ratings across provider IDs or seasons.
- If a club has no defensible identity link into a competition/season, abstain or use a separately pre-registered prior; never infer a mapping from a name alone.

## 4. Current quarantined configuration — diagnostic baseline only

The existing implementation minimizes:

[
\frac{\text{recency-weighted Poisson NLL}}{\sum_iw_i}
+\frac12(0.5)\sum a_t^2
+\frac12(0.5)\sum d_t^2
+\frac12(0.5)\sum q_c^2.
]

The shadow job's actual runtime values are team_ridge=0.5, competition_ridge=0.5, half-life=365 days. The function's competition_ridge default of 2.0 is not the shadow runtime value. In summed-likelihood units, the team penalty coefficient is 0.5 × total recency weight; on the archived 996-label fit this was 434.2905607400909.

The independent 996-label fit audit measured median absolute fitted/reference team-effect ratios of approximately 3.01% (attack) and 3.39% (defence), with median prior/data-information ratios of 30.58× and 30.31×. This is a diagnostic baseline, not an accuracy score or a replacement hyperparameter recommendation.

## 5. Synthetic test contract — required before candidate admission

Tests must use deterministic synthetic fixtures with known team attack/defence strengths and known competition/home effects. They must exercise:

1. **Recovery:** with adequate observations, the candidate must recover strong-versus-weak team ordering and distinguish a deliberately strong favourite from a weak opponent.
2. **Shrinkage:** with abundant observations, fitted team effects must remain close to the unpenalized reference fit; shrinkage must not erase the known signal.
3. **Sparse evidence:** with few observations, estimates must shrink toward the competition prior rather than become extreme.
4. **Current-configuration rejection:** the recovery and shrinkage admission assertions must reject the quarantined runtime values team_ridge=0.5, competition_ridge=0.5, half-life=365.
5. **Excessive-prior negative control:** an intentionally enormous (k) / prior precision must also fail recovery; this prevents a vacuous test that rewards any amount of shrinkage.
6. **No per-team tuning:** all teams of the same parameter type use the same (k); a test must fail if a team-specific prior is injected.
7. **Competition information scale:** a synthetic fixture must verify the competition-effect information scale is based on two scoring observations (approximately (2\mu_c)), not (\mu_c).
8. **Home-prior behavior:** competition-specific home effects shrink toward a global value, and an extreme unregularized per-competition home effect fails the negative control.

The test suite should pass as a test suite while explicitly recording that the current quarantined candidate and the excessive-prior negative control are **rejected by the admission assertions**. Do not make CI fail merely to demonstrate that the current model is defective.

## 6. Hyperparameter selection and evaluation boundary

- Tune (k_A,k_D,k_C,k_H,k_{H0}) only on nested chronological development folds or a separate development period.
- Freeze configuration and code/data hashes before the final untouched holdout.
- The final holdout is used once. A failed candidate burns that holdout; the next attempt requires new unseen data.
- The primary metric is 1X2 log loss. Other markets are non-regression checks only until the primary passes.
- Before evaluation, calculate minimum detectable effect and statistical power. Insufficient power fails admission; no threshold relaxation after seeing results.
- Compare against both league climatology with home advantage and a tuned team-aware Poisson/Elo baseline. Use paired block-bootstrap intervals by match date.
- Numeric thresholds require explicit user approval once and are then frozen with a hash.

## 7. Non-negotiable release controls

- No candidate from this work is automatically admitted.
- SHADOW admission requires retrospective gates and permits output only on the labelled RESEARCH ONLY feed.
- PUBLISHED admission requires prospective settled evidence and explicit user sign-off.
- Every model version binds immutable config, training-data and evaluation-report hashes.
- The database, not the application alone, enforces admission and forecast-write rules.
- A quarantine transition immediately hides that model's existing forecasts from API reads.
