# Cross-dataset event validation

GazeForge supports leakage-aware cross-dataset validation for manually labelled eye-event corpora.
The current candidate design targets **Lund2013 ↔ Hollywood2EM**. Both are acquired at 500 Hz and
are independently reduced to 60 Hz with the same majority-window label-purity rule before model
comparison. This is derived lower-rate validation, not native-60-Hz device validation.

## Preparation guardrails

`prepare_cross_dataset_event_benchmark()` requires, by default:

- at least two source `GazeFrame` objects;
- resolved participant identities;
- a verified coordinate unit for every source;
- dataset-specific reviewed source audits where required (currently Hollywood2EM);
- the same common reference classes (fixation, saccade, pursuit);
- no upsampling;
- per-source purity-aware resampling; and
- dataset-prefixed participant/trial IDs so unrelated corpora cannot collide by name.

For Hollywood2EM, `coordinate_unit="pixels"` on the low-level loader is **not sufficient** for frozen
cross-dataset preparation. By default, the preparation gate also requires `source_audit_status` to
be verified, valid SHA-256 fingerprints for the source-audit report/specification/file manifest,
verified reuse terms, and explicit analysis-use permission. These fields are produced by the
[Hollywood2EM source audit](hollywood2-source-audit.md).

The `require_source_audits=False` switch exists for controlled development/testing of generic
preparation mechanics. It should not be used to create a frozen Hollywood2EM evidence report.

```python
from gazeforge import (
    load_audited_hollywood2_directory,
    prepare_cross_dataset_event_benchmark,
    run_cross_dataset_event_validation,
)

hollywood = load_audited_hollywood2_directory(
    "/path/to/hollywood2_em",
    hollywood_audit_spec,
    annotator="expert",
)

prepared = prepare_cross_dataset_event_benchmark(
    {"Lund2013": lund, "Hollywood2EM": hollywood},
    target_sampling_rate_hz=60,
    min_label_purity=0.75,
)

result = run_cross_dataset_event_validation(prepared)
print(result.summary)
print(result.report_fingerprint_sha256)
```

Each dataset preparation report carries any available source-audit report, specification, and
manifest fingerprints into the cross-dataset result fingerprint. This makes the future model report
cryptographically dependent on the reviewed Hollywood2EM source identity rather than only on a
caller-provided coordinate flag.

## Validation design

A fresh Random Forest and temporal ContextMLP are fitted for each held-out dataset. Participants are
namespaced by dataset and the existing dataset-held-out validators enforce train/test identity
disjointness. Per-held-out-dataset accuracy, balanced accuracy, macro-F1, multiclass Brier score,
and expected calibration error are returned together with event-level precision/recall/F1,
temporal IoU, and onset/offset/duration errors from the same held-out predictions.

I-VT is not included in this cross-dataset learned-model runner. A deterministic velocity baseline
should only be compared when both corpora provide sufficiently comparable visual-angle geometry.

## Claim limit

The current Lund2013/Hollywood2 protocol is a candidate external-generalisation design. It cannot
establish native 60 Hz tracker validity because both corpora are natively 500 Hz. Frozen empirical
reports should only be created after an authoritative Hollywood2EM copy has passed the reviewed
source audit covering exact files, participant identities, coordinate units, and current
analysis/reuse terms.
