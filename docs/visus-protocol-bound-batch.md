# VISUS protocol-bound Grounded-SAM-2 batch

GazeForge can execute the complete frozen VISUS Grounding DINO + SAM 2 plan and
assemble one canonical model-prediction table while preserving the pre-execution
protocol, mechanical frame derivation, and source-audit lineage.

This layer sits **after** the VISUS pre-execution protocol and **before** model-human
scoring. Its purpose is to prevent a later benchmark from being assembled from a
mixture of unbound runs, missing stimuli, changed thresholds, changed frames, or
prediction-derived evaluation timestamps.

It is not an empirical validation result.

## Why a complete-batch layer is needed

The pre-execution protocol already protects one stimulus execution at a time. A
complete benchmark still needs a second guarantee: the final prediction table must be
assembled from exactly one valid protocol-bound execution for every frozen stimulus.

`run_visus_grounded_sam2_protocol_batch()` therefore requires the complete frozen
stimulus set and performs the following sequence:

1. reload and fingerprint-check the frozen protocol file;
2. require exactly one current plan for every frozen stimulus and no extras;
3. replay the protocol against the current source audit, checkpoint bytes, source
   videos, frame-derivation reports, and derived-frame bytes;
4. execute each frozen stimulus once through the existing protocol-bound runner;
5. revalidate each Grounded-SAM-2 backend report;
6. cross-bind the backend report, mechanical frame-derivation binding, and
   pre-execution protocol binding;
7. convert every backend run through the existing VISUS prediction schema;
8. require complete audited-stimulus coverage;
9. write a deterministic canonical prediction CSV; and
10. write a deterministic batch-lineage JSON report.

The batch validator repeats the relevant identity and byte checks when the resulting
run is reused.

## Required inputs

A batch requires:

- a `VisusGroundedSAM2PreexecutionProtocolRun` frozen before inference;
- the same verified empirical `VisusSourceAuditRun` used by that protocol;
- exactly one `VisusGroundedSAM2StimulusPlan` for every frozen VISUS stimulus;
- the current source videos and mechanically derived JPEG frames;
- the exact SAM 2 checkpoint bytes and immutable model/code revisions; and
- a Grounded-SAM-2 runtime, unless the optional default runtime is available.

The batch runner replays the frozen protocol before the first backend call. A missing
plan, extra plan, changed checkpoint, changed source video, changed frame, changed
prompt, or changed model policy therefore fails before model execution.

## Complete stimulus coverage

The frozen protocol defines the execution order. The batch runner does not infer or
re-sort a new scientific plan.

For the current VISUS protocol this means one execution per frozen stimulus. The
output prediction table must contain the same complete stimulus set in that order.
The existing `prepare_visus_dynamic_aoi_predictions()` intake is then called with:

```text
require_complete_stimulus_coverage = true
```

No partial batch is promoted as a complete model prediction artifact.

## Cross-binding the lineage

For every stimulus, the batch ledger requires the following identities to agree:

```text
frozen protocol fingerprint
        │
        ├── protocol binding ── Grounded-SAM-2 report fingerprint
        │                      │
        │                      └── exact stimulus model output
        │
        └── frame derivation report fingerprint
                               │
                               └── mechanical frame binding
                                   ├── same Grounded-SAM-2 report fingerprint
                                   ├── source-video SHA-256
                                   └── frame-manifest fingerprint
```

A binding is rejected even if a tampered JSON object has been re-fingerprinted when
it points to a different protocol/backend/derivation identity or promotes a forbidden
scientific claim.

## Deterministic artifacts

The output directory contains:

```text
visus-grounded-sam2-predictions.csv
visus-grounded-sam2-protocol-batch.json
```

The prediction CSV uses stable ordering and deterministic float serialization. The
batch report records:

- frozen protocol fingerprint;
- source-audit report/specification/manifest fingerprints;
- exact global model policy;
- ordered per-stimulus execution ledger;
- backend report fingerprints;
- frame-derivation report and manifest fingerprints;
- protocol-binding and frame-binding fingerprints;
- source-video SHA-256 values;
- prediction CSV byte count and SHA-256;
- in-memory prediction-table fingerprint;
- row and track counts;
- existing VISUS prediction-intake fingerprint; and
- the frozen downstream evaluation handoff.

`validate_visus_protocol_bound_batch_run()` rereads both the frozen protocol and the
written batch JSON report. It also rehashes the prediction CSV and replays the current
protocol/source/model/frame inputs.

## Example

```python
from gazeforge.visus_protocol_batch import (
    run_visus_grounded_sam2_protocol_batch,
    validate_visus_protocol_bound_batch_run,
)

batch = run_visus_grounded_sam2_protocol_batch(
    protocol,
    audit,
    plans,
    "outputs/visus-grounded-sam2-batch",
    runtime=runtime,
)

validate_visus_protocol_bound_batch_run(batch)

predictions = batch.predictions
prediction_intake = batch.prediction_intake
```

Existing outputs fail closed unless `overwrite=True` is explicitly supplied.

## Evaluation-grid separation

The batch prediction table contains the frames on which Grounded-SAM-2 emitted model
AOIs. Those frames are **not** the later model-human evaluation grid.

The batch carries forward the independent timestamp grids frozen by the pre-execution
protocol and records:

```text
prediction_emission_grid_used = false
evaluation_timestamp_grid_generated = false
```

The model-human evaluator must use the frozen external grids unchanged.

## Claim boundary

A successful batch establishes only that GazeForge assembled a complete prediction
artifact from the frozen protocol-bound execution path.

The report therefore keeps all of the following false:

```text
formal_preregistration_verified = false
empirical_performance_claim_created = false
model_human_validation_executed = false
human_human_agreement_claimed = false
dataset_source_authority_promoted = false
dataset_rights_promoted = false
frozen_evidence_created = false
```

In particular, this batch does **not** establish:

- authoritative/current public distribution identity for the 2014 VISUS benchmark;
- redistribution permission;
- a second independent human annotation stream;
- human-human agreement;
- Grounding DINO + SAM 2 accuracy;
- model-human validity;
- formal preregistration; or
- Frozen Evidence.

Those remain separate fail-closed gates.

## Scientific handoff

Once authoritative source/rights requirements and the human-reference prerequisites
are satisfied, the batch's existing `prediction_intake` can be supplied to the VISUS
model-human evaluation machinery together with the exact settings frozen by the
pre-execution protocol.

No evaluation metric is computed in this tranche.