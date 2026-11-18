# 2026-11-18 — Retrospective report validation gate

## Purpose

The retrospective research workflow must reject malformed or internally inconsistent output before writing the private artifact. This validator checks report integrity and structural invariants; it does not certify predictive accuracy or point-in-time eligibility.

## Checks

- Recomputes SHA-256 over the canonical unsigned report and compares it with the supplied hash.
- Requires the explicit non-PIT research dataset label.
- Reconciles source row count, FINISHED labels, UNKNOWN exclusions and invalid rows.
- Requires provider-local identity namespace and retrospective lagged-result feature semantics.
- Requires one prediction per FINISHED fixture, unique fixture IDs and timezone-aware chronological kickoffs.
- Validates non-negative actual scores, finite normalized Elo/Poisson 1X2 vectors, positive goal rates, finite rho and bounded ensemble weights.
- Validates Elo, Poisson and ensemble scorecard match counts, Brier and log loss.
- Validates ensemble weight summary ordering and finite full-corpus rho diagnostic.

## Scope boundary

The validator is a report-integrity gate only. It does not:
- establish historical feature availability or PIT certification;
- resolve provider team aliases or fixture duplicates;
- compare this full-corpus prequential scorecard directly with the existing 305-fixture nested walk-forward evaluation;
- promote a model, publish predictions, enable Android integration or unlock value betting.

The training runner invokes this validator after computing the report checksum and before writing the artifact.
