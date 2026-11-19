# Canonical Scope Inventory and Reconciliation V1

## Purpose

Move canonical coverage from the Brazil Serie B run-specific materializer toward all approved provider competition scopes without loosening identity review, source provenance, or publication gates.

## Safe sequencing

1. Read-only scope inventory and review report.
2. Explicit scope selection and provenance validation.
3. Idempotent source placeholder/link reconciliation.
4. Identity review queue refresh.
5. Human identity decisions through the existing review mechanism.
6. PIT feature snapshot generation only after target identities are reconciled.

## Inventory contract

The inventory tool must operate read-only by default and report:

- effective source approval status as of database time (including status events);
- validity interval, scope type/values, data types and permitted uses;
- provider competition IDs in scope and whether their source observations/sightings/response provenance is complete;
- provider teams referenced by scoped fixtures and provenance completeness;
- fixture totals by status, source-local canonical link presence, and unresolved review/conflict counts;
- duplicate or collision candidates, without resolving them;
- schema/migration readiness and any missing objects.

Do not infer approval from a provider or source name alone. Use the approval record and its effective event history.

## Write gates

Any later reconciliation writer must:

- default to dry-run;
- require explicit execute flag and a separately supplied confirmation string;
- verify the expected database name and source scope at runtime;
- run planning, locking, reconciliation and post-write assertions in a single transaction;
- use advisory locking per source/scope;
- create only source-local canonical placeholders and exact provenance links;
- preserve human-reviewed mappings and reject drift rather than silently updating;
- create/retain review cases for ambiguous identities, duplicates, or collisions;
- never mark identity links VERIFIED automatically;
- never mark PIT evidence certified or promote a model;
- make zero provider requests and report that fact;
- be idempotent: rerunning must not create duplicate canonical rows, source links or review cases.

## Required reconciliation tests

- empty scope and missing approval fail closed;
- expired/revoked approval fails closed;
- provenance mismatch fails closed;
- existing reviewed mapping remains untouched;
- existing source-local placeholder is reused;
- duplicate source fixture mapping is rejected;
- conflicting canonical fixture links are preserved as conflict/review;
- missing team or competition observation creates no fabricated lineage;
- scheduled and finished fixtures are handled without assuming status completeness;
- rerun after a successful reconcile produces no additional writes;
- execute without explicit confirmation remains blocked;
- database target mismatch remains blocked;
- migration readiness is checked before reconciliation.

## Current known constraints

The current production audit showed 614 provider fixture rows without canonical links, 382 canonical fixtures marked `IDENTITY_REVIEW_REQUIRED`, 2 marked `CONFLICT`, and zero publication eligible. Those values are a prior audit snapshot, not live inventory values. This document does not change production data.

The Brazil Serie B run-3 materializer remains unchanged and first-run-only until the generalized inventory and reconciliation logic has been validated independently.

## Next implementation unit

Build a read-only scope inventory CLI against the current schema, emitting a deterministic JSON report and a human-readable summary. It should identify approved competition scopes and source evidence coverage, but it should not mutate canonical entities. This inventory becomes the input and safety evidence for the later generalized reconciliation writer.
