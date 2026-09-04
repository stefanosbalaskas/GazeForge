# Source-resolution validation contract

GazeForge separates **source resolution** from **source audit** and from **empirical validation**.
A source-resolution checkpoint records what public-source research has established about an external
benchmark before any local data copy is allowed into the empirical evidence pipeline.

The unified validator covers the current v1 checkpoints for:

| Dataset | Current resolution state | Empirical status |
| --- | --- | --- |
| VISUS | current authoritative distribution unresolved | non-empirical |
| Hollywood2EM | canonical distribution identifier established; exact current copy unverified | non-empirical |
| Gaze-in-the-Wild | published distribution identifier and current institutional listing established; exact direct copy unverified | non-empirical |

The validator deliberately refuses to convert publication metadata, historical download links,
article licenses, contributor counts, or secondary catalog metadata into stronger evidence.

## Unified command

Validate one checkpoint:

```bash
gazeforge-source-resolution \
  validation/protocols/hollywood2-source-resolution-2026-09-04.json
```

Validate the current three-dataset resolution set together:

```bash
gazeforge-source-resolution \
  validation/protocols/visus-source-resolution-2026-09-04.json \
  validation/protocols/hollywood2-source-resolution-2026-09-04.json \
  validation/protocols/gaze-in-wild-source-resolution-2026-09-04.json
```

The CLI emits JSON only. A multi-record invocation returns a deterministic
`source-resolution-validation-bundle-v1` object containing each validated record fingerprint and a
bundle fingerprint.

The existing `gazeforge-visus-source-resolution` command remains available for backward-compatible
single-record VISUS validation.

## Continuous-integration gate

The main CI workflow executes the unified command against all three committed checkpoints in a
separate `source-resolution-governance` job. A pull request therefore fails before merge if a status
record drifts into an unsupported evidence state, promotes unresolved rights, weakens an
annotation-independence guard, reconciles conflicting sampling-rate provenance without review, or
otherwise violates the dataset-specific v1 contract.

The clean-wheel smoke job also invokes `gazeforge-source-resolution` after installing the built
wheel. This checks that the governance CLI is actually present in the distributable package rather
than working only from an editable source checkout.

The CI-generated JSON is a validation summary, not frozen empirical evidence. It is not committed to
the evidence tree and does not upgrade any benchmark's scientific status.

## What the common validator enforces

Every accepted checkpoint must:

- use `record_type: source-resolution-status-v1`;
- identify a benchmark with a reviewed dataset-specific validator;
- contain an ISO `checked_on` date;
- remain `source_audit_ready: false` and `empirical_evidence_created: false` at the current recorded
  state;
- keep analysis-use terms and raw-data redistribution terms separately unresolved;
- prohibit inference of dataset licensing from publication or descriptive metadata;
- carry explicit claim limits and next required actions; and
- produce a deterministic SHA-256 content fingerprint.

Unknown datasets are rejected rather than accepted under a generic permissive schema. Moving a
benchmark to a new source-resolution state therefore requires an explicit reviewed validator change.

## Dataset-specific safeguards

### VISUS

The existing strict VISUS validator remains authoritative for the VISUS checkpoint. It preserves the
key scientific boundary that two contributors to one curation workflow do **not** establish two
independent annotation streams. Human-human agreement remains blocked unless separately recoverable
independent streams are verified from an exact authoritative copy.

### Hollywood2EM

The Hollywood2EM validator preserves the sequential annotation provenance: a novice/student review
was subsequently corrected by an expert. Student-versus-expert comparison is therefore annotation
sensitivity, not independent human-human reliability. The validator also keeps participant mapping,
trial mapping, coordinate units, exact repository licensing, and the current local copy unverified
until the exact distribution is obtained and audited.

### Gaze-in-the-Wild

The Gaze-in-the-Wild validator preserves two distinctions simultaneously:

1. the publication reports five trained annotators who made decisions independently, but frozen
   human-human agreement still requires exact recoverable streams and shared underlying gaze to be
   verified from the obtained copy; and
2. the publication's 120 Hz acquisition-hardware provenance remains separate from the 300 Hz value
   reported by a later evaluation catalog. Neither value is substituted for empirical file cadence,
   which must be inferred from audited timestamps.

Gaze-in-the-Wild remains complementary head-mounted evidence and is not Gazepoint GP3-equivalent
validation.

## Python API

```python
from gazeforge.source_resolution import (
    load_source_resolution_record,
    validate_source_resolution_record,
    validate_source_resolution_records,
)

summary = validate_source_resolution_record(
    "validation/protocols/hollywood2-source-resolution-2026-09-04.json"
)
record = load_source_resolution_record(
    "validation/protocols/gaze-in-wild-source-resolution-2026-09-04.json"
)
```

Dataset-specific validators are also available for Hollywood2EM and Gaze-in-the-Wild. VISUS keeps
its existing `validate_visus_source_resolution_record()` implementation and the unified dispatcher
calls it directly.

## Scientific boundary

Passing this validator means only that the **status checkpoint itself is internally consistent with
GazeForge's current governance rules**. It does not prove that the external dataset has been
obtained, that its exact files have been fingerprinted, that analysis use is permitted, that raw-data
redistribution is permitted, that coordinate semantics have been verified, or that any model or
human-agreement metric is empirically valid.

Those stronger claims remain the responsibility of the dataset-specific source audit and subsequent
frozen empirical workflow.
