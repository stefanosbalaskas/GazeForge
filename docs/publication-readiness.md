# Publication-readiness checklist

<div class="gf-doc-kind" role="note" aria-label="Documentation type">
<strong>Research checklist</strong> · Audit acquisition, exclusions, model identity, evidence class, software identity, and archive readiness before reporting.
</div>

<nav class="gf-help" aria-label="Documentation help">
<a href="gazeforge-tour.md">Tour</a>
<a href="documentation-map.md">Task map</a>
<a href="troubleshooting.md">Troubleshooting</a>
<a href="runnable-examples.md">Examples</a>
<a href="https://github.com/stefanosbalaskas/GazeForge/issues">Ask / report</a>
</nav>


Use this checklist before preregistration, analysis freeze, manuscript submission, or release of a supplementary archive. It is designed to catch evidence inflation and reproducibility gaps before they become manuscript claims.

!!! note "Checklist ≠ certification"
    Completing this page is a reporting and audit aid. It does not independently validate a tracker, dataset, model, or scientific conclusion.

For a runnable real-data handoff before using this checklist, see the [Worked tracker import and QC](worked-tracker-import.md). Before statistical modelling, use the [Analysis handoff](analysis-handoff.md) to preserve inferential units, denominators, missing-versus-zero semantics, and censoring. Before promoting a gaze-derived variable into a substantive construct, use the [Measurement & interpretation clinic](measurement-interpretation.md) to record the construct bridge, validity threats, sensitivity checks, and unsupported inferences. After the archive is frozen, use the [Reporting & interpretation clinic](reporting-clinic.md) for claim-safe Methods, Results, captions, and reporting derivatives, then use the [Reviewer & replication handoff](reviewer-replication-handoff.md) to classify rerun access and package reviewer-facing traceability without strengthening the evidence. For an archive-shaped worked example, use the [Research evidence bundle](research-evidence-bundle.md) and [Artifact & output dictionary](artifact-dictionary.md).

## Before preregistration or data collection

- ☐ The observable gaze construct and unit of analysis are defined.
- ☐ Participant, trial, stimulus, and repeated-measure identifiers are specified.
- ☐ Tracker/model, native/nominal acquisition rate, screen/stimulus geometry, and required viewing-distance assumptions are recorded.
- ☐ The plan distinguishes acquisition/native rate, observed timestamp cadence, and any derived analysis rate.
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
- ☐ Source, canonical, and pre-exclusion QC row counts have been reconciled and any differences explained.
- ☐ Nominal/native acquisition rate is reported separately from observed timestamp cadence.
- ☐ Off-screen coordinates are reviewed rather than silently clipped.
- ☐ Import compatibility is not treated as evidence of tracker/device validity.

The [Worked tracker import](worked-tracker-import.md) demonstrates this preflight with explicit Gazepoint-style columns, seconds→milliseconds conversion, normalized→pixel conversion, duplicate/bounds diagnostics, and row-count preservation.

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

### Statistical analysis handoff

- ☐ The inferential unit and repeated-measures grouping are explicit before model fitting.
- ☐ Participant/trial identity has not been aggregated away merely for convenience.
- ☐ Count, rate, proportion, and dwell outcomes retain their relevant observed exposure/denominator.
- ☐ Observed zero, absent-by-design, undefined, and missing states remain distinguishable.
- ☐ No-fixation latency retains an event indicator/censoring status rather than an invented latency.
- ☐ Descriptive participant × condition summaries are labelled separately from inferential model inputs.
- ☐ Statistical estimator choice is prespecified/justified in specialist software rather than selected automatically by GazeForge.
- ☐ Failed convergence, singularity, separation, or invalid diagnostics stop interpretation rather than being silently accepted.
- ☐ Handoff tables preserve event/AOI/QC/source provenance and exact software identity.

[Open the statistical analysis handoff →](analysis-handoff.md)

### Measurement interpretation

- ☐ Every substantive gaze interpretation names the underlying observable and unit.
- ☐ Proposed latent constructs have an explicit theoretical/empirical bridge rather than a package rule.
- ☐ No-fixation latency is retained as censoring rather than converted to zero or silently dropped.
- ☐ Event, AOI, sampling, quality, exclusion, and coverage threats have been reviewed where material.
- ☐ Sensitivity analyses are scientifically justified and not selected for favourable results.
- ☐ Confidence/probability is not treated as individual correctness without held-out calibration/validation evidence.
- ☐ Dwell, counts, latency, and scanpaths are not promoted automatically to trust, persuasion, interest, comprehension, emotion, intent, diagnosis, preference, or cognitive effort.

[Open the measurement & interpretation clinic →](measurement-interpretation.md)

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

Use the [Reporting & interpretation clinic](reporting-clinic.md) before finalizing prose. It provides explicit **Interpret / Report / Do not say / Archive / Continue to** guidance for imports, QC, events, AOIs, scanpaths, validation splits, calibration/confidence, native-versus-derived sampling, synthetic demos, and downstream statistical results.

- ☐ GazeForge version is reported; development analyses also include the exact commit SHA.
- ☐ Python version and material optional dependencies are archived or reported.
- ☐ Every manuscript table/figure can be traced to a reconstructable or frozen artifact.
- ☐ Figure captions repeat evidence qualifiers when a visual could otherwise be overread.
- ☐ Model, AOI, split, rate, and metric terminology is consistent throughout methods, results, tables, and supplement.
- ☐ The manuscript does not promote a source token to participant identity without authoritative mapping.
- ☐ Observed timestamp cadence is not described as proof of native hardware sampling rate.
- ☐ Derived lower-rate evidence is not described as native-device validation.
- ☐ Synthetic/demo output is not cited as empirical validation evidence.
- ☐ Import compatibility is not described as device validity.
- ☐ A model that leads on one dataset/metric is not described as universally superior without evidence supporting that broader claim.
- ☐ Calibration is not described as proof that individual predictions are correct.
- ☐ Confidence-based abstention is not reported without the corresponding retained coverage.
- ☐ Unsupported latent-state claims are not inferred directly from gaze patterns.
- ☐ The current [Evidence status](evidence-status.md) has been checked for the benchmark/device claim being made.

## Before releasing a supplement or analysis archive

- ☐ The reviewer/replication class is explicit: fully rerunnable, rerunnable with authorized/private input, or inspectable only.
- ☐ A start-here file and rerun plan identify exact commands, required inputs, expected outputs, and access restrictions.
- ☐ Claim-supporting artifacts are named with exact file identities/hashes where available.
- ☐ The hash ledger states that checksums establish byte identity rather than scientific validity.
- ☐ Private/restricted participant or benchmark sources are not redistributed without authorization.
- ☐ Privacy/licensing status is reported separately from technical ability to package a file.
- ☐ Reviewer inspectability is not described as a complete independent rerun when source-dependent calculations cannot be reproduced.
- ☐ Reproducibility wording does not imply device, model, measurement/construct, causal, external, or latent-state validity.


- ☐ Source/reuse rights have been checked independently from article-level licensing.
- ☐ Sensitive or restricted source data are not redistributed merely because derived outputs can be shared.
- ☐ The archive records source identity without overstating access or redistribution rights.
- ☐ Final tables, figures, manifests, certificates, fingerprints, and analysis code share a consistent analysis identity.
- ☐ The archive includes the import contract/preflight when source columns or units were transformed.
- ☐ Validation archives include the split ledger, held-out predictions, probability columns where applicable, sample/event metric tables, calibration/coverage diagnostics, and model-selection/threshold policy.
- ☐ Random seeds and non-default parameters are recorded.
- ☐ The archive contains a short **evidence boundary** statement.
- ☐ An artifact index or equivalent table of contents identifies source, QC, review, analysis, validation, provenance, and reporting files.
- ☐ A human-readable README explains the intended reading order and any files that cannot be redistributed.

## Compact evidence boundary record

A manuscript or supplement can retain a short machine- and human-readable record like this:

```text
software: gazeforge <version>
analysis_commit: <full SHA if development checkout>
python: <version>
tracker: <model>
native_rate_hz: <rate>
observed_cadence_hz: <rate from analysed timestamps>
analysis_rate_hz: <rate>
analysis_rate_status: native | derived
source_mapping: <participant/trial/time/x/y fields>
source_units: <time + coordinate basis>
screen_geometry: <width × height>
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
| Acquisition | tracker/model, native/nominal rate, observed cadence, geometry, study identity structure |
| Canonicalisation | timestamp unit, coordinate basis, mapping/adaptation rule, row-count/duplicate/bounds preflight |
| QC | anomaly method, thresholds, review/exclusion rule |
| Events | algorithm/model, version, threshold, training rate, confidence rule |
| AOIs | source, geometry, model provenance if AI-assisted, human review state |
| Validation | held-out unit, folds, split ledger/leakage controls, reference labels, matched-row status |
| Model selection | selection/tuning data versus final confirmatory evaluation; exploratory choices labelled |
| Rate | native/nominal vs observed cadence vs derived analysis status and derivation/sensitivity rule |
| Metrics | sample/event/calibration metrics matched to the question; coverage with selective accuracy |
| Provenance | package version/SHA, environment, source/output fingerprints |
| Boundary | explicit statement of unsupported/generalisation claims |

For the import/QC handoff, use the [Worked tracker import](worked-tracker-import.md) and [Real-data import clinic](data-import-clinic.md). For model-ready trial/AOI/event tables, use the [Analysis handoff](analysis-handoff.md). For archive assembly, use the [Research evidence bundle](research-evidence-bundle.md) and [Artifact & output dictionary](artifact-dictionary.md). For learned event models, work through the [Event-model validation clinic](event-model-validation-clinic.md) before freezing the analysis. For copy-ready claim-safe validation wording, use the [Validation reporting cookbook](validation-reporting-cookbook.md). For terminology that is easy to overstate, use [Research terminology](research-terminology.md). For reviewer/replicator traceability and rerun access classification, use the [Reviewer & replication handoff](reviewer-replication-handoff.md). For broader prose structure, continue with [Reproducible reporting](reproducible-reporting.md).
