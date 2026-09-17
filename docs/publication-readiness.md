# Publication-readiness checklist

Use this checklist before preregistration, analysis freeze, manuscript submission, or release of a supplementary archive. It is designed to catch evidence inflation and reproducibility gaps before they become manuscript claims.

!!! note "Checklist ≠ certification"
    Completing this page is a reporting and audit aid. It does not independently validate a tracker, dataset, model, or scientific conclusion.

## Before preregistration or data collection

- ☐ The observable gaze construct and unit of analysis are defined.
- ☐ Participant, trial, stimulus, and repeated-measure identifiers are specified.
- ☐ Tracker/model, native acquisition rate, screen/stimulus geometry, and required viewing-distance assumptions are recorded.
- ☐ The primary QC review/exclusion rule is specified separately from anomaly detection.
- ☐ The event method and any threshold or learned-model plan are named.
- ☐ The AOI source is defined as researcher/manual, AI-proposed + reviewed, or another traceable source.
- ☐ Primary gaze outcomes are separated from exploratory process measures.
- ☐ The intended validation split unit is explicit: participant, stimulus, dataset, source token, or another defensible unit.
- ☐ Planned model/threshold selection is separated from final confirmatory evaluation where required.
- ☐ Planned sampling-rate transformations are distinguished from native acquisition conditions.
- ☐ The planned archive includes software/environment identity and provenance artifacts.

## Before analysis freeze

### Source and canonicalisation

- ☐ The original acquisition/export files are retained.
- ☐ The exact analysed source table/file has a checksum or deterministic fingerprint.
- ☐ Timestamp units and coordinate semantics are documented from an authoritative source or study record.
- ☐ Screen/stimulus geometry is recorded where coordinate conversion or bounds QC depends on it.
- ☐ Participant/trial identity mapping has not been guessed or silently reconstructed.
- ☐ Duplicate or non-increasing sample keys have been reviewed explicitly rather than silently collapsed.

### QC and exclusions

- ☐ QC flags remain separate from exclusion decisions.
- ☐ Any excluded participants, trials, or samples are traceable to a documented rule.
- ☐ The pre-exclusion table is retained when exclusions occur.
- ☐ Exploratory thresholds are labelled exploratory.

### Events, AOIs, and sequences

- ☐ Event model/algorithm identity, version, threshold, training rate, and confidence/abstention rule are recorded where applicable.
- ☐ Learned-model evaluation uses an explicit leakage-safe held-out design.
- ☐ A split ledger or equivalent record identifies which participants/stimuli/tokens/datasets were train versus test in every fold.
- ☐ Compared models use the same held-out rows/folds when the comparison is intended to be matched.
- ☐ Model or threshold selection is separated from the final confirmatory test set, or the resulting choice is explicitly labelled exploratory.
- ☐ Reference labels and annotator provenance are recorded where validation depends on them.
- ☐ AI-proposed AOIs retain model/confidence provenance and explicit review decisions.
- ☐ Final AOI geometry is frozen before manuscript-facing aggregation when the design requires fixed AOIs.
- ☐ Scanpath/transition outputs retain participant/trial identity and their AOI-label source.

### Validation and metrics

- ☐ The held-out unit is named rather than described only as “held out”.
- ☐ Participant-disjoint, stimulus-disjoint, source-token-disjoint, and dataset-held-out claims are not treated as interchangeable.
- ☐ Sample-level metrics are not substituted for event-level temporal performance when boundary fidelity matters.
- ☐ Calibration metrics are reported for probabilistic confidence claims where relevant.
- ☐ Selective accuracy or abstention results are reported together with coverage.
- ☐ Confidence thresholds are described as study-specific unless independently justified for broader use.
- ☐ Matched model comparisons use the same held-out rows/folds when the comparison requires paired evidence.
- ☐ **Native versus derived** sampling-rate status is stated explicitly wherever acquisition and analysis rates differ.
- ☐ Native and derived sampling-rate conditions are labelled separately.
- ☐ Sensitivity analyses preserve the derivation rule and source provenance.

## Before manuscript submission

- ☐ GazeForge version is reported; development analyses also include the exact commit SHA.
- ☐ Python version and material optional dependencies are archived or reported.
- ☐ Every manuscript table/figure can be traced to a reconstructable or frozen artifact.
- ☐ Figure captions repeat evidence qualifiers when a visual could otherwise be overread.
- ☐ Model, AOI, split, rate, and metric terminology is consistent throughout methods, results, tables, and supplement.
- ☐ The manuscript does not promote a source token to participant identity without authoritative mapping.
- ☐ Derived lower-rate evidence is not described as native-device validation.
- ☐ Synthetic/demo output is not cited as empirical validation evidence.
- ☐ Import compatibility is not described as device validity.
- ☐ A model that leads on one dataset/metric is not described as universally superior without evidence supporting that broader claim.
- ☐ Calibration is not described as proof that individual predictions are correct.
- ☐ Confidence-based abstention is not reported without the corresponding retained coverage.
- ☐ Unsupported latent-state claims are not inferred directly from gaze patterns.
- ☐ The current [Evidence status](evidence-status.md) has been checked for the benchmark/device claim being made.

## Before releasing a supplement or analysis archive

- ☐ Source/reuse rights have been checked independently from article-level licensing.
- ☐ Sensitive or restricted source data are not redistributed merely because derived outputs can be shared.
- ☐ The archive records source identity without overstating access or redistribution rights.
- ☐ Final tables, figures, manifests, certificates, fingerprints, and analysis code share a consistent analysis identity.
- ☐ Validation archives include the split ledger, held-out predictions, probability columns where applicable, sample/event metric tables, calibration/coverage diagnostics, and model-selection/threshold policy.
- ☐ Random seeds and non-default parameters are recorded.
- ☐ The archive contains a short **evidence boundary** statement.

## Compact evidence boundary record

A manuscript or supplement can retain a short machine- and human-readable record like this:

```text
software: gazeforge <version>
analysis_commit: <full SHA if development checkout>
python: <version>
tracker: <model>
native_rate_hz: <rate>
analysis_rate_hz: <rate>
analysis_rate_status: native | derived
split_unit: participant | stimulus | source_token | dataset | other
reference_labels: <source / annotator provenance>
primary_metrics: <metrics matching the estimand>
source_fingerprint: <SHA-256 or archive identity>
output_manifest: <manifest identity>
evidence_boundary: <what this design does not establish>
```

## Manuscript-facing minimum methods record

| Area | Minimum record |
| --- | --- |
| Acquisition | tracker/model, native rate, geometry, study identity structure |
| Canonicalisation | timestamp unit, coordinate basis, mapping/adaptation rule |
| QC | anomaly method, thresholds, review/exclusion rule |
| Events | algorithm/model, version, threshold, training rate, confidence rule |
| AOIs | source, geometry, model provenance if AI-assisted, human review state |
| Validation | held-out unit, folds, split ledger/leakage controls, reference labels, matched-row status |
| Model selection | selection/tuning data versus final confirmatory evaluation; exploratory choices labelled |
| Rate | native vs derived status and derivation/sensitivity rule |
| Metrics | sample/event/calibration metrics matched to the question; coverage with selective accuracy |
| Provenance | package version/SHA, environment, source/output fingerprints |
| Boundary | explicit statement of unsupported/generalisation claims |

For learned event models, work through the [Event-model validation clinic](event-model-validation-clinic.md) before freezing the analysis. For copy-ready claim-safe validation wording, use the [Validation reporting cookbook](validation-reporting-cookbook.md). For terminology that is easy to overstate, use [Research terminology](research-terminology.md). For broader prose structure, continue with [Reproducible reporting](reproducible-reporting.md).
