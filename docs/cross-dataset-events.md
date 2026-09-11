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
verified reuse terms, explicit analysis-use permission, and the matching validated
`SourceAuditLineageReceipt`. These fields are produced by the reviewed Hollywood2EM source-audit
and source-lineage workflow.

The `require_source_audits=False` switch exists for controlled development/testing of generic
preparation mechanics. It cannot be used to create publishable Lund↔Hollywood2 Frozen Evidence.

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
    source_audit_lineages={"Hollywood2EM": hollywood2_lineage_receipt},
    target_sampling_rate_hz=60,
    min_label_purity=0.75,
)

result = run_cross_dataset_event_validation(prepared)
print(result.summary)
print(result.report_fingerprint_sha256)
```

Each dataset preparation report carries the relevant source-audit and lineage fingerprints into the
cross-dataset result fingerprint. The result is therefore cryptographically dependent on the
reviewed Hollywood2EM source identity rather than only on caller-provided metadata.

## Validation design

A fresh Random Forest and temporal ContextMLP are fitted for each held-out dataset. Participants are
namespaced by dataset and the existing dataset-held-out validators enforce train/test identity
disjointness. Per-held-out-dataset accuracy, balanced accuracy, macro-F1, multiclass Brier score,
and expected calibration error are returned together with event-level precision/recall/F1,
temporal IoU, and onset/offset/duration errors from the same held-out predictions.

I-VT is not included in this cross-dataset learned-model runner. A deterministic velocity baseline
should only be compared when both corpora provide sufficiently comparable visual-angle geometry.

## Frozen Evidence publication gate

A `CrossDatasetEventValidation` result is **not** public Frozen Evidence by itself. The dedicated
publication contract in `gazeforge.cross_dataset_evidence` converts only the guarded
Lund2013↔Hollywood2 result into the closed-schema benchmark report:

```python
from gazeforge.cross_dataset_evidence import (
    build_lund_hollywood2_cross_dataset_report,
    freeze_cross_dataset_frozen_report,
)

report = build_lund_hollywood2_cross_dataset_report(
    prepared,
    result,
    hollywood2_lineage=hollywood2_lineage_receipt,
    benchmark_version="review-candidate-v1",
)
freeze_cross_dataset_frozen_report(
    report,
    "validation/cross-dataset/lund-hollywood2-cross-dataset-report.json",
)
```

The report validator recomputes the original guarded-runner validation fingerprint and requires:

- exactly Lund2013 and Hollywood2EM in the leave-one-dataset-out design;
- independently derived 60 Hz analysis rather than native-60-Hz wording;
- resolved participant identities and verified coordinate units;
- source-audit enforcement enabled;
- the exact RandomForest/ContextMLP matched design and all four model × held-out-dataset rows;
- the complete fingerprinted Hollywood2EM `SourceAuditLineageReceipt`; and
- exact agreement between that receipt and the audit/spec/manifest/receipt fingerprints carried by
  the guarded runner.

A second, separate manual scientific decision is then required before the public dashboard can show
the row:

```python
from gazeforge.cross_dataset_scientific_review import (
    write_cross_dataset_scientific_review_approval,
)

write_cross_dataset_scientific_review_approval(
    "validation/cross-dataset/lund-hollywood2-cross-dataset-report.json",
    reviewer="Reviewer name",
    reviewed_at="2026-09-11T12:00:00+00:00",
    review_rationale="Reviewed design, source lineage, metrics, and claim boundaries.",
)
```

The approval is fingerprinted and bound to the exact report filename, report fingerprint,
cross-dataset validation fingerprint, dataset identities, and Hollywood2EM lineage/audit/source
fingerprints. The Frozen Evidence dashboard fails closed if a cross-dataset-shaped report lacks this
approval, if the report is copied to a different filename, or if any of the bound identities drift.
When publication is approved, reviewer, UTC review time, review scope, and approval fingerprint are
surfaced with the report row.

## Claim limit

The current Lund2013/Hollywood2 protocol is a candidate external-generalisation design. It cannot
establish native 60 Hz tracker validity because both corpora are natively 500 Hz. The dedicated
publication gate does not create a GP3-validity claim, universal cross-dataset generalisability,
ground-truth status for a human reference, broader analysis/reuse rights, or raw-source
redistribution authorization.

The roadmap item to freeze Lund↔Hollywood2 leave-one-dataset-out results therefore remains blocked
until the authoritative Hollywood2EM participant identity and current rights prerequisites are
actually resolved and the resulting report receives separate scientific review. Software
availability alone does not satisfy those empirical/governance prerequisites.
