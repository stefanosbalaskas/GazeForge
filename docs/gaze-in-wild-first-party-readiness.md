# Gaze-in-the-Wild first-party readiness handoff

This layer connects two already reviewed, conservative Gaze-in-the-Wild inputs:

1. a privacy-safe first-party response record bound to the exact clarification request and a local correspondence SHA-256; and
2. a live-reverified quarantined candidate ProcessData screen.

Its output is a **readiness and blocker report**. It is not a quarantine-exit authorization and does not create empirical evidence.

## Why this layer exists

A first-party response may legitimately establish facts such as respondent authority, an authoritative archive location, and explicit dataset-file analysis or redistribution terms. Separately, the candidate ProcessData screen can establish that one exact quarantined file is structurally compatible with GazeForge's ProcessData adapter.

Those facts still do not establish that the candidate is byte-identical to the authoritative archive or canonical replacement. Exact-copy identity therefore remains an independent review step.

## Strongest possible state

The v1 handoff can reach:

`ready_for_independent_exact_copy_review`

only when all of the following preliminary conditions are satisfied:

- the first-party response has completed human review;
- source authority is verified;
- an authoritative archive/canonical-source location is provided;
- dataset-file analysis use is explicitly permitted;
- redistribution terms are reviewed;
- the redistribution result does not require vocabulary-mapping review; and
- the candidate kind is eligible for quarantine-exit review.

Even in that strongest state:

- `independent_exact_copy_identity_verified = false`;
- `quarantine_exit_ready = false`;
- `quarantine_exit_authorized = false`; and
- `source_audit_ready = false`.

The remaining blocker is independent exact-copy identity verification against the reviewed first-party authoritative source.

## Redistribution semantics are not silently rewritten

The first-party response vocabulary can record `redistribution_status = "prohibited"`, while the quarantine-exit authorization vocabulary uses `permitted`, `restricted`, or `unknown`.

The readiness bridge does **not** silently translate `prohibited` to `restricted`. Instead, it adds the blocker `redistribution_status_mapping_review_required`. Any later vocabulary reconciliation must be explicit and human-reviewed.

## Privacy boundary

The handoff serializes:

- the exact request fingerprint;
- the exact response fingerprint;
- the correspondence SHA-256;
- reviewed response statuses;
- the exact recovery/tree/screen/file identities; and
- deterministic readiness/blocker fields.

It does **not** serialize the raw correspondence body or the archive location itself. Live verification still requires the local correspondence file so its digest can be checked against the reviewed response.

## Scientific boundary

The handoff does not establish or create:

- exact-copy identity;
- quarantine-exit authorization;
- source-audit execution/readiness;
- participant/trial/task mapping;
- coordinate semantics;
- acquisition or corpus sampling cadence;
- separate `LabelData` recovery or independent labeller streams;
- empirical evidence eligibility;
- human-human agreement;
- participant-disjoint model validation;
- cross-dataset performance;
- GP3 validity; or
- Frozen Evidence performance claims.

The next scientific-governance action after a fully satisfied preliminary handoff is to independently verify the quarantined candidate against the authoritative first-party archive/canonical source. Only after that separate identity review may the existing quarantine-exit authorization machinery be considered.
