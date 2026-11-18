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

The project owner's permission confirmation resolves the project-side authorization
decision for the collected corpus. It does not change source timestamps, fixture
identity confidence, duplicate status, label availability, or the temporal
availability of features. In particular, no historical row becomes PIT-eligible
merely because model-training use is authorized.


## Explicit personal-use authorization clarification — project owner, 2026-11-17

The project owner clarifies that VELTRIX AI ANALYST is for personal use only,
that the owner authorizes use of the information/data already collected to train
the project's model, and that separate documentary permission evidence was not
obtained because the project is personal. Treat this as the project owner's
express project-level authorization and do not impose a new paperwork step as a
routine prerequisite for using the collected corpus.

Operational decision: proceed with personal-use model-development work on the
collected data under this owner authorization, while preserving source identity,
retrieval timestamps, payload hashes, and any known source terms/limitations.
Do not describe documentary evidence as obtained when it was not. Personal-use
authorization does not manufacture missing historical publication/availability
timestamps, resolve identity/duplicate conflicts, or turn post-event information
into pre-match features. If a source's known terms expressly prohibit the intended
use, flag that specific conflict rather than treating all data as unusable.


## Provider schema audit and adapter correction — 2026-11-18

A review of the current public provider documentation found that the first odds normalizer implemented an assumed schema that does not match either documented endpoint. Its synthetic unit fixture was therefore not sufficient to establish provider compatibility.

Documented contracts reviewed:
- Fixture snapshot: https://5dollarfootballapi.com/docs/odds — `GET /v1/fixtures/{id}/odds` returns `data.bookmakers[]`, each with `name`, `slug`, and nested `odds` markets. Bet365 1X2 opening prices carry `opened_at`; closing/in-play and most other market stages have no per-price timestamp in this response.
- Odds history: https://5dollarfootballapi.com/docs/odds-history — `data.bookmaker`, `data.market`, and `data.ticks[]`; ticks carry `recorded_at`, `minute`, and score. Pre-match examples use `minute: null` and null score; in-play examples carry a minute and/or score. Suspended ticks may carry null prices and must not become observations.
- The full odds-history endpoint is documented as Ultra-only. Do not infer entitlement from a fixture import or plan name.

PR [#42](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/42) replaces the assumed parser with separate adapters for the two documented envelopes:
- Fixture snapshot adapter admits only timestamped 1X2 opening prices. It deliberately ignores closing/in-play and other markets without individual source timestamps.
- History adapter retains timestamped pre-match 1X2 and goal-line ticks, and excludes in-play/suspended ticks.
- Both adapters preserve provider tick time separately from our actual retrieval time and pass through the existing cutoff/rights/identity-independent odds contract. A response retrieved after the original prediction cutoff remains rejected even if its provider tick is earlier.
- Tests now use documented response examples rather than the prior synthetic shape.

No live odds API request was made during this schema review. The user has explicitly confirmed project-owner authorization for all collected data, including odds, for the project's personal-use model research and training. That authorization is recorded; it does not manufacture source timestamps or override any applicable provider contract. The account plan and Brazil Serie B listing were subsequently verified as Community / visible, but the odds snapshot endpoint's account-specific response remains unverified. Odds capture stays inactive pending one bounded live snapshot probe. The full odds-history endpoint is documented as Ultra-only and is not part of the Community-plan probe. No new key/account is to be created.


## Personal-use and review-scope correction — 2026-11-18

- Intended audience: the project owner only. This is not a public-facing product
  or a multi-user service.
- Commercial status: non-monetised personal use only. No subscriptions, paid
  predictions, commercial distribution, or monetised model outputs.
- Owner review: the project owner personally reviewed the recommendations.
- Professional review: professionals were contacted after the owner's review,
  reviewed the recommendations, and verbally approved the proposed approach as
  sound and suitable to proceed. They later apologized that they could not add
  comments to the owner's GitHub work. Record this as verbal approval, not as a
  GitHub review, written sign-off, or approval of code they did not inspect.
- Review authorship context: the owner presented the recommendations as the
  owner's own; do not claim the professionals were told the assistant authored
  them.
- External GitHub comments are not required for this private personal-use
  project; the lack of a GitHub comment does not erase the verbal approval.
- Data use: continue using the already collected and authorized data for the
  owner's personal model research and training, subject to known provider terms,
  account entitlements, attribution obligations where applicable, and the
  prohibition on raw-feed resale or redistribution.
- Technical controls remain independent of external review: preserve provenance,
  timestamps, fixture identity, source hashes, and honest point-in-time eligibility.
  These controls protect prediction quality; they are not a requirement to obtain
  professional opinions.
