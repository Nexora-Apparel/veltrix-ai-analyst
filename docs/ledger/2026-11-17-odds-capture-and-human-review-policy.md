# Odds capture and identity-review disposition — 2026-11-17

## Human-review disposition
No automated identity approval is permitted. Automation may assemble evidence,
rank candidate mappings, identify graph conflicts, and produce recommendations.
Only an attributable human review event can approve canonical team, competition,
fixture identity, alias merge, or duplicate exclusion. False identity joins
contaminate Elo ratings, goal-rate estimates, and outcome labels.

The existing 28 review cases remain pending: 20 team candidates, four duplicate
candidates, America MG alias collision, competition-season mapping, coverage
reconciliation, and PIT timestamp gap. No source row is deleted or reparented.

## Rights authorization declaration — project owner, 2026-11-17

The project owner confirms that the provider authorized use of data available
through the account's free mode for personal, non-commercial use, including
collection and model training. The user has not purchased a subscription.
The stated condition is no monetization or commercial use while operating on
the free mode; a paid subscription is required before commercial use. The
project is private and exclusively for the owner's personal use.

Proceed with data collection and model research using the data/features actually
made available under the existing free-mode account and its documented limits.
Do not create another account or key, assume paid-tier endpoints are available,
or exceed rate, request, competition, retention, or other free-plan limits.
Do not monetize, sell, sublicense, or commercially distribute raw data or model
outputs under this free-mode authorization. If the project later changes to
commercial use, stop that use until the required paid subscription/permission
is in place.

Preserve source-level provenance in dataset manifests: provider/source, access
mode, retrieval time, response hash, competition/fixture identifiers, and any
known restrictions. This is an evidence and entitlement record, not a demand
for additional professional review or paperwork. The owner has already reviewed
the approach and obtained verbal professional approval; written GitHub comments
are not required.

## Odds point-in-time controls
Every prospective odds row retains provider fixture ID, bookmaker, market,
selection, line, decimal price, source tick timestamp (recorded_at/opened_at),
our own response retrieval timestamp, kickoff, prediction cutoff, in-play state,
source observation ID, SHA-256 response hash, immutable rights approval ID,
and explicit model-training permission.

Admission requires source tick <= retrieval <= prediction cutoff < kickoff,
pre-match state, timezone-aware timestamps, valid price, and approved rights.
Missing source tick, retrieval time, in-play state, rights, or unambiguous fixture
identity means reject. Source tick time is not our historical availability time.
Odds retrieved after the original cutoff cannot be backfilled as historical
features, even when the provider tick is old.

## Account entitlement
The repository already contains scripts/verify_5dollar_access.py and
.github/workflows/provider-access-check.yml. It calls the account status endpoint
and Brazil league listing, reporting plan, limits, usage, and competition access
without printing the key or downloading match history. The workflow uses existing
GitHub secret aliases. A GitHub Actions dispatch/write operation is unavailable
in this execution session, so live entitlement is not yet verified. No new key or
account is required.

The documented odds-history endpoint is Ultra-only. Fixture-level odds and
include=odds have separate plan requirements. Do not infer account entitlement
from documentation or successful fixture imports. Run the existing access check,
then one bounded odds endpoint probe before enabling collection.

## Historical training and calibration

The 380-fixture CBF retrospective corpus may be used for research-only model
fitting, feature experiments, and chronological backtesting under the owner's
personal-use authorization. It is not a point-in-time-certified dataset: the
historical snapshot has no verified source publication/availability timestamps,
and the PIT-certified feature set is empty. Therefore, results from this corpus
must be labelled retrospective/non-PIT research and must not be represented as
prospective accuracy or production certification.

Fit Elo, Poisson/Dixon-Coles, and ensemble parameters only inside chronological
training folds; keep future test folds untouched. Preserve fixture/identity/
duplicate uncertainty, and exclude unresolved rows from supervised labels rather
than silently merging or deleting them. Compare against simple baselines,
report Brier score and log loss with uncertainty intervals, and retain per-league
sample sizes. Do not promote a model or unlock value betting on the basis of this
small retrospective sample. Build a separate prospective PIT dataset from
features genuinely captured before kickoff before making claims about live
forecast performance.

## Project-owner review authorization — correction recorded 2026-11-18

The project owner personally reviewed the recommendations. The owner then
contacted professional reviewers, presented the recommendations as the owner's
own recommendations, and asked them to assess the approach. The professionals
reviewed the recommendations and verbally said that the proposed approach was
good, was the right approach, and that the owner could proceed. They later
apologized that they would not be able to comment on the owner's work in GitHub,
and left. Therefore, professional verbal approval of the recommended approach
was given; a written GitHub review/comment was not provided. Do not conflate the
absence of a GitHub comment with an absence of professional review or approval.
Do not attribute authorship of the recommendations to the assistant in the
professionals' review account: the owner presented them as the owner's own.

VELTRIX AI ANALYST is a private, personal-use application for the project owner.
The owner does not intend to publish it as a public service or provide it to
other users. External professional review is therefore not a project release
requirement. The owner's own review and decisions govern product direction.

This correction does not waive engineering data-integrity controls. Canonical
team, competition, fixture, alias, and duplicate decisions must still be based
on traceable evidence and recorded accurately; no reviewer identity or approval
may be fabricated. The owner may make those project-level decisions.

## Rights and PIT distinction

Personal-use permission for free-mode data supports research and training within
the actual access tier and non-commercial condition. It does not change source
timestamps, fixture identity confidence, duplicate status, label availability,
or the temporal availability of features. No historical row becomes PIT-eligible
merely because model-training use is authorized.

## Provider schema audit and adapter correction — 2026-11-18

A review of the current public provider documentation found that the first odds
normalizer implemented an assumed schema that does not match either documented
endpoint. Its synthetic unit fixture was therefore not sufficient to establish
provider compatibility.

Documented contracts reviewed:
- Fixture snapshot: https://5dollarfootballapi.com/docs/odds — `GET /v1/fixtures/{id}/odds` returns `data.bookmakers[]`, each with `name`, `slug`, and nested `odds` markets. Bet365 1X2 opening prices carry `opened_at`; closing/in-play and most other market stages have no per-price timestamp in this response.
- Odds history: https://5dollarfootballapi.com/docs/odds-history — `data.bookmaker`, `data.market`, and `data.ticks[]`; ticks carry `recorded_at`, `minute`, and score. Pre-match examples use `minute: null` and null score; in-play examples carry a minute and/or score. Suspended ticks may carry null prices and must not become observations.
- The full odds-history endpoint is documented as Ultra-only. Do not infer entitlement from documentation or successful fixture imports.

PR [#42](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/42) replaces the assumed parser with separate adapters for the two documented envelopes:
- Fixture snapshot adapter admits only timestamped 1X2 opening prices. It deliberately ignores closing/in-play and other markets without individual source timestamps.
- History adapter retains timestamped pre-match 1X2 and goal-line ticks, and excludes in-play/suspended ticks.
- Both adapters preserve provider tick time separately from our actual retrieval time and pass through the existing cutoff/rights/identity-independent odds contract. A response retrieved after the original prediction cutoff remains rejected even if its provider tick is earlier.
- Tests now use documented response examples rather than the prior synthetic shape.

No live odds API request was made during this schema review. Odds capture stays inactive pending one bounded live snapshot probe that is confirmed to be available under the current free-mode account. The full odds-history endpoint is documented as Ultra-only and is not part of the free-mode probe. No new key/account is to be created.

## Personal-use and review-scope correction — 2026-11-18

- Intended audience: the project owner only. This is not a public-facing product
  or a multi-user service.
- Commercial status: non-monetised personal use only. No subscriptions, paid
  predictions, commercial distribution, or monetised model outputs while using
  the free-mode authorization.
- Owner review: the project owner personally reviewed the recommendations.
- Professional review: professionals were contacted after the owner's review,
  reviewed the recommendations, and verbally approved the proposed approach as
  sound and suitable to proceed. They later apologized that they could not add
  comments to the owner's GitHub work. Record this as verbal approval, not as a
  GitHub review or written sign-off.
- Review authorship context: the owner presented the recommendations as the
  owner's own; do not claim the professionals were told the assistant authored
  them.
- External GitHub comments are not required for this private personal-use
  project; the lack of a GitHub comment does not erase the verbal approval.
- Data use: use data available through the existing free-mode account for the
  owner's personal research and model training, within the provider's free-tier
  limits and the stated no-monetization condition. A paid subscription is
  required before commercial use, according to the owner's confirmation.
- Do not request further professional review or repeat a commercial-approval
  gate for the current personal-use project.
- Technical controls remain independent of external review: preserve provenance,
  timestamps, fixture identity, source hashes, and honest point-in-time eligibility.
  These controls protect prediction quality; they are not a requirement to obtain
  professional opinions.
