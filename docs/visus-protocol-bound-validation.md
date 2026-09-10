# VISUS protocol-bound validation handoff

GazeForge can now connect a **complete protocol-bound Grounding DINO + SAM 2 prediction batch** directly to the existing VISUS dynamic-AOI validation suite without reopening scoring choices after model inference.

This layer is intentionally an orchestration and lineage gate. It does **not** introduce a new metric implementation and it does not replace the existing VISUS model-human, human-human, suite, authority, execution-provenance, or Frozen Evidence machinery.

## Why this layer exists

The repository already had three separate capabilities:

1. the VISUS pre-execution protocol freezes model and evaluation choices before inference;
2. the complete protocol-bound batch executes every frozen stimulus and produces the canonical prediction intake; and
3. the VISUS validation suite computes and freezes model-human metrics, with conditional human-human agreement when genuinely independent streams exist.

Without an explicit bridge, a caller could still manually pass the batch prediction intake into the suite while separately re-entering the reference stream, timestamp grid, interpolation gap, IoU threshold, semantic-match rule, and fixation overlap rule. Even if those values were intended to match the frozen protocol, that manual handoff was not itself mechanically bound to the protocol fingerprint.

`run_visus_protocol_bound_validation_suite()` closes that gap.

## No post-inference scoring controls

The protocol-bound handoff deliberately does not accept caller arguments for:

- the human reference stream;
- evaluation timestamps;
- timestamp-grid basis;
- maximum interpolation gap;
- IoU threshold;
- semantic-label matching;
- fixation overlap rule;
- inclusion of model-human diagnostic match rows; or
- a manually selected human-human stream pair.

Instead, it reloads the exact pre-execution protocol carried by the batch and recovers the frozen evaluation settings through `validation_settings_from_preexecution_protocol()`.

Diagnostic match rows are always included by this layer so that the protocol-bound result retains the most inspectable version of the existing validation output without changing the scoring rule.

## Required lineage

Before the existing validation suite is called, the handoff revalidates the complete protocol-bound batch. That replay includes the frozen protocol, current source audit, current source/checkpoint/frame identities, prediction CSV bytes, prediction table fingerprint, prediction-intake fingerprint, and every per-stimulus protocol/frame binding.

The supplied canonical human-reference intake must then:

- be a verified `VisusCanonicalAOIIntakeRun`;
- have a valid report fingerprint;
- share the exact source-audit report, specification, and manifest fingerprints carried by the protocol-bound batch;
- contain the exact reference stream frozen before inference; and
- cover every frozen protocol stimulus for that stream.

The existing `run_visus_dynamic_aoi_validation_suite()` then receives the batch prediction intake and only the evaluation settings recovered from the protocol.

## Fixation-assignment rule

Whether fixation-to-AOI assignment is planned is frozen in the pre-execution protocol.

The handoff therefore fails closed in both directions:

```text
frozen plan = false + fixation tables supplied  -> reject
frozen plan = true  + fixation tables missing   -> reject
```

When fixation assignment was frozen as planned and complete fixation inputs are supplied, the existing suite runs it with the exact frozen overlap rule.

## Human-human agreement

This layer preserves the repository's existing independence guard.

If the source audit does **not** verify separately recoverable independent annotation streams, no human-human agreement child is created.

If the source audit does verify human-human readiness, the protocol-bound handoff will automatically proceed only when exactly two canonical streams are available. That removes post-hoc pair selection from this v1 handoff.

If more than two independent streams are available, the handoff fails closed because a larger candidate set would require the stream pair to be frozen explicitly in a future protocol revision.

Neither human stream is treated as error-free ground truth.

## Output binding

A successful call writes the ordinary VISUS validation-suite reports and completion manifest, plus:

```text
visus-protocol-bound-validation.json
```

The binding records and fingerprints:

- source-audit report/specification/manifest identity;
- pre-execution protocol fingerprint;
- complete protocol-batch fingerprint;
- prediction CSV filename and SHA-256;
- prediction-intake report fingerprint;
- human-reference intake and canonical-table fingerprints;
- exact frozen evaluation handoff;
- completed validation-suite fingerprint;
- model-human report fingerprint; and
- human-human report fingerprint when independently verified streams make that child applicable.

The validator rereads and revalidates the protocol-bound batch, human-reference intake, suite manifest and child reports, and the binding file itself.

## Example

```python
from gazeforge.visus_protocol_validation import (
    run_visus_protocol_bound_validation_suite,
)

validation = run_visus_protocol_bound_validation_suite(
    batch,
    human_reference_intake,
    "outputs/visus-protocol-validation",
)

print(validation.binding_fingerprint_sha256)
print(validation.suite.suite_fingerprint_sha256)
```

If fixation assignment was frozen as planned:

```python
validation = run_visus_protocol_bound_validation_suite(
    batch,
    human_reference_intake,
    "outputs/visus-protocol-validation",
    fixations_by_stimulus=fixation_tables,
)
```

No scoring threshold or evaluation-grid argument is re-entered at this stage.

## Scientific interpretation

A successful binding can establish that:

- the exact protocol-bound model batch was used;
- the human-reference intake shares the same audited source identity;
- the existing VISUS model-human suite actually executed;
- the suite consumed the exact evaluation settings frozen before inference; and
- the resulting suite and model-human report fingerprints are bound back to the batch and protocol.

The binding sets:

```text
model_human_validation_executed = true
empirical_performance_claim_created = false
source_authority_certificate_required_separately = true
source_authority_certificate_bound_by_this_layer = false
formal_preregistration_verified = false
dataset_source_authority_promoted = false
dataset_rights_promoted = false
frozen_evidence_created = false
```

This distinction is important. Computing model-human metrics is not the same as establishing that the underlying VISUS copy is authoritative, that current reuse/distribution rights have been verified, that the result has passed scientific review, or that it is eligible for public Frozen Evidence publication.

## Authority and publication boundary

Source authority remains governed by the existing VISUS authoritative-source intake, manual review, certificate, and authority-bound execution provenance.

This handoff does not self-certify that gate and does not infer authority from historical mirrors, article licenses, historical research-purpose wording, or the existence of a technically valid source audit.

Accordingly, the open VISUS roadmap item for a current authoritative copy and reuse/distribution terms remains open until the separately requested source response/evidence is reviewed and certified.

Likewise, implementation of this handoff alone does not satisfy the roadmap item to validate a dynamic backend empirically. That item should be closed only after a real authoritative VISUS execution is run, reviewed, and frozen through the complete governed path.
