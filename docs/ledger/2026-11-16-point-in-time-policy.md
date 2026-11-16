# Point-in-time feature eligibility policy merged — 2026-11-16

- PR [#9](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/9) merged to `main`.
- Merge commit: `9e72b4a4bf6b6e03a642237c9fe3716ee837d80c`.
- Added `docs/FEATURE_ELIGIBILITY_AND_POINT_IN_TIME_POLICY.md`.
- The policy distinguishes event time from source publication/availability time, and requires `available_at <= prediction_cutoff` before any feature can enter a pre-match training view.
- 5Dollar post-match statistics and its four-day availability proxy remain non-PIT-certified.
- AI Midas Brazil Serie B CSV remains descriptive-only absent independent publication/availability evidence.
- Post-match settled results may be target labels; this does not make them valid pre-match features.
- Defines feature registry, chronological split and embargo controls, leakage prevention, and model-training acceptance gate.
- Documentation-only change; no CI workflow was triggered.
- No provider requests, database writes, fixture imports, odds calls or model training occurred.
- Historical collection remains LOCKED pending the operator's explicit manual dispatch confirmation.
