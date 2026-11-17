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

The project owner explicitly confirms that permission has been obtained to use
all information currently collected for training the VELTRIX AI ANALYST model,
and that the sources/information being used have been authorized. Record this as
a project-owner rights declaration covering the current collected corpus and
personal-use project scope. Do not continue to describe model-training permission
as categorically absent for that corpus.

Operational handling: preserve the owner declaration as an authorization record,
but retain source-level rights provenance (provider/source, applicable terms or
permission evidence, scope, effective date, permitted operations, and any limits)
when building the immutable dataset manifest. Where a source has an explicit
non-commercial or personal-use restriction, keep the model and resulting use
within that scope. If any source's terms conflict with the declaration or do not
cover model training, quarantine only that source pending clarification rather
than assuming blanket permission overrides third-party terms. This is a provenance
and scope check, not a demand for another account or key.

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
The production snapshot has 384 provider fixtures, zero sightings with verified
source publication and availability timestamps, and zero PIT-certified features.
All 28 review cases remain pending. Thus the eligible historical PIT training set
is empty under the Stage 3 admission contract.

Do not fit or tune Elo, Poisson goal rates, Dixon-Coles rho, ensemble weights, or
calibration parameters on these records. Synthetic tests validate code
invariants, not forecast quality. Fit parameters only inside each chronological
training fold after identity, competition, duplicate, rights, source-time, and
label-availability gates pass; evaluate on untouched future folds.

## Project-owner review authorization — 2026-11-17

The project owner reports that they reviewed the recommendations, that a peer
also reviewed them, and that a professional reviewer agreed with the conservative
approach. The project owner authorizes proceeding with the evidence-first policy
and implementation plan recorded above. This entry records the owner's report
and authorization only; it is not a substitute for named reviewer attestations,
individual case-level evidence, or the required immutable human-review events.

No case is changed to HUMAN_CONFIRMED by this authorization alone. Automated
recommendations remain recommendations. Any future identity decision must cite
specific authoritative evidence and record the actual reviewer identity and
evidence hash. Personal/non-commercial use does not alter point-in-time feature
eligibility or waive provider terms.


## Rights and PIT distinction

The project owner's permission confirmation resolves the project-side authorization
decision for the collected corpus. It does not change source timestamps, fixture
identity confidence, duplicate status, label availability, or the temporal
availability of features. In particular, no historical row becomes PIT-eligible
merely because model-training use is authorized.
