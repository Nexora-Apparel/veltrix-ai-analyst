# VELTRIX AI ANALYST — v3.2 preregistration fingerprint record

- Schema: `veltrix-shrinkage-selection-v3.2`
- Frozen configuration: `docs/research/shrinkage-selection-v3.json`
- Canonical SHA-256: `d087f3d641eccf8b81a6717d691db1edab0fd5402119182d18e01e56eadd176a`
- Canonicalization: Python `json.dumps(config, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)`, followed by one newline, encoded as UTF-8 and SHA-256 hashed.

## Correction record — 2026-11-21

The prior workflow default and immutable-input check used `90aea1d84cbe2301f71f5e3d6910d913ae2d1b79c7658319e5cf3ee0817df62a`. That value does not match the canonical serialization of the committed v3.2 JSON. The correct value is `d087f3d641eccf8b81a6717d691db1edab0fd5402119182d18e01e56eadd176a`.

The configuration file was mechanically compared at references `692e118` and `82d0f42f0cfda19442887495ef6132d22a9a187b`. Both references resolve to the same Git blob, `eb179fc5c45fa35c86c945bb3b673d7b7b73bcca` (4,824 bytes). Therefore, the JSON did not change between those two references. The earlier fingerprint was stale relative to this unchanged file; the exact earlier source of the stale value is not established.

No evaluation result existed when this correction was made. No candidate was selected and no preregistered rule was changed. The JSON itself is intentionally unmodified.

## Frozen rules unchanged

- Grid: 10 values of k × 3 half-lives × 4 blend weights = 120 configurations.
- Candidate selection: equal-fold mean development-fold log loss, then equal-fold mean multiclass Brier, then the frozen tie-break order.
- Convergence: damped Newton with the existing analytic-Hessian/backtracking implementation and the exact tolerances, consecutive accepted-step requirement, iteration cap, and failed-fit exclusion already recorded in the JSON.
- Historical availability: kickoff + 3 hours, strictly before fold cutoff.
- Admission: retrospective-only, not PIT-certified; research-only SHADOW display at most. No production or value-betting promotion.

The authoritative rule definitions remain in `shrinkage-selection-v3.json`; this document records the corrected fingerprint and audit trail only.
