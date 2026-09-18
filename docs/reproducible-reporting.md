# Reproducible reporting guide

A GazeForge analysis should be reproducible at two levels: **software identity** and **scientific evidence identity**. Reporting only a package name is not enough when the result depends on sampling-rate transformations, held-out grouping, source provenance, or frozen benchmark artifacts.

If you are still designing the study, begin with the [Study lifecycle](study-lifecycle.md). If you already have frozen artifacts and need task-first guidance on what to interpret, report, avoid saying, and archive, use the [Reporting & interpretation clinic](reporting-interpretation-clinic.md). If the analysis is approaching submission or archive freeze, use [Publication readiness](publication-readiness.md) as the final audit. The [Research terminology](research-terminology.md) guide keeps acquisition, split, validation, QC, and evidence-status wording consistent, while the [worked advertising/interface study](worked-advertising-study.md) and [worked dynamic-AOI study](worked-dynamic-aoi-study.md) show the reporting artifacts in concrete synthetic examples.

## Minimum methods checklist

| Item | Record |
| --- | --- |
| Software | GazeForge version and, for development analyses, exact commit SHA |
| Environment | Python version and relevant optional dependencies |
| Acquisition | tracker/model, native sampling rate, screen geometry, viewing distance where required |
| Canonicalisation | coordinate basis, timestamp unit, participant/trial identity mapping |
| QC | anomaly method, seed, thresholds/review rule, exclusions after review |
| Event model | method, model identity/version, training sampling rate, confidence/abstention rule |
| Validation | split unit, fold count, participant/stimulus/dataset disjointness, leakage checks |
| Rate handling | native versus derived rate, resampling rule, label-purity rule |
| Metrics | sample-level metrics, calibration where relevant, event-level temporal metrics |
| Human reference | annotator provenance and agreement when available |
| Evidence | report/suite fingerprint, source manifest/certificate where applicable |

## Native and derived evidence must be named differently

Use language that preserves acquisition provenance.

**Appropriate:**

> Event models were evaluated on a derived 60 Hz condition constructed from the native 500 Hz human-labelled corpus using the prespecified resampling and label-purity procedure.

**Not appropriate:**

> The models were validated at 60 Hz.

The second sentence can be read as native 60 Hz device validation even when the source was acquired at a higher rate.

## Describe the split unit explicitly

Do not use "held out" without naming what was held out.

Prefer one of:

- participant-disjoint;
- stimulus-disjoint;
- dataset-held-out;
- source-token-disjoint when identity cannot be promoted beyond an opaque source token;
- matched folds when multiple models are evaluated on exactly the same held-out rows.

A source-token split must not be relabelled as participant-disjoint unless the token→participant mapping is authoritatively established.

## Claim-safe wording pairs

### Import compatibility versus device validity

**Appropriate:**

> The Gazepoint export was successfully adapted to the canonical GazeForge schema using explicit timestamp, coordinate, participant, trial, and display-geometry mappings.

**Overstated:**

> Successful import validated the eye tracker.

Import compatibility shows that the software can interpret the declared fields. It does not establish measurement validity, calibration quality, native-rate fidelity, or device-specific event validity.

### QC flags versus invalid samples

**Appropriate:**

> Samples were flagged for review using the prespecified QC rule; exclusions were made only under the separately reported review protocol.

**Overstated:**

> The QC algorithm removed invalid samples.

A QC flag is evidence for review. Unless the study separately validates the rule, it is not an oracle label for invalidity.

### Software demo versus empirical validation

**Appropriate:**

> The synthetic example demonstrates the software workflow and output contract; it is not empirical validation evidence.

**Overstated:**

> The example validates GazeForge on dynamic AOIs.

Synthetic/demo output can test deterministic software behavior, but it does not establish detector accuracy, tracker validity, native 60 Hz validity, Gazepoint/GP3 validity, or substantive effects.

### Participant-disjoint versus source-token-disjoint

**Appropriate:**

> Evaluation was source-token-disjoint; an authoritative token→participant mapping was unavailable, so participant-disjointness was not claimed.

**Overstated:**

> The model was participant-held-out.

Identity strength must follow the source evidence. An opaque token cannot be promoted to a participant identifier by assumption.

### Sample-level versus event-level performance

**Appropriate:**

> The model achieved the reported sample-level macro-F1, while event segmentation was evaluated separately with event-F1 and temporal overlap metrics.

**Overstated:**

> High sample-level accuracy demonstrates accurate event boundaries.

Sample discrimination and contiguous event segmentation are different estimands and can rank models differently.

### Calibration versus correctness

**Appropriate:**

> Predicted probabilities showed the reported calibration error across held-out observations.

**Overstated:**

> The model was calibrated, so its individual predictions were correct.

Calibration is a distributional property of probabilities. It does not guarantee correctness for any specific prediction.

## Report multiple estimands when the scientific question requires them

For event detection, a high sample-level macro-F1 does not guarantee good contiguous event segmentation. Consider reporting:

- balanced accuracy and macro-F1 for sample-level multiclass discrimination;
- event-F1 and temporal IoU for event segmentation;
- onset/offset boundary error where timing matters;
- calibration error/Brier score for probabilistic classifiers;
- selective accuracy/coverage if abstention is used.

The [Results gallery](results-gallery.md) shows why the ranking can change across sample-level and event-level criteria.

## Record exact evidence identity

When a workflow produces a frozen report or certificate, include its deterministic fingerprint in the analysis archive or supplement.

A compact record can look like:

```text
software: gazeforge 0.1.0a1
python: 3.12.x
analysis_commit: <full git SHA>
source_manifest: <SHA-256 or certified source record>
validation_design: participant-disjoint 5-fold
native_rate_hz: 500
analysis_rate_hz: 60
analysis_rate_status: derived
report_fingerprint: <SHA-256>
```

## Suggested manuscript structure

### Data and acquisition

State tracker, acquisition rate, geometry, participant/trial structure, and the provenance of any expert labels.

### Preprocessing and QC

Describe canonicalisation, missingness handling, QC flags, review/exclusion rules, and any resampling. Make clear whether difficult boundary samples were retained, marked ambiguous, or excluded under a label-purity rule.

### Model specification

Name the event/AOI/sequence method, training rate, predictor set or geometry requirement, random seed where relevant, and compatibility guards.

### Validation design

Name the held-out unit and explain how leakage was prevented. For multiple models, state whether predictions were generated on identical folds/rows.

### Evaluation

Report the metrics that match the scientific estimand. Separate sample classification, event segmentation, calibration, human-human agreement, and sensitivity analyses rather than collapsing them into one score.

### Evidence boundary

End the methods/results interpretation with what the design does **not** establish—for example, derived rather than native-rate evidence, source-token rather than participant disjointness, or unresolved dataset reuse/identity provenance.

## Public alpha citation

For the first public alpha, record `gazeforge==0.1.0a1` and cite the archived release DOI `10.5281/zenodo.22650013`. For analyses run from a later development checkout, add the exact full commit SHA even when the public release is also cited.

## Before submission

Confirm that:

- the code in the analysis archive runs from the recorded environment;
- every reported table/figure can be traced to a frozen or reconstructable artifact;
- figures repeat critical evidence qualifiers in the caption or adjacent text;
- the manuscript does not upgrade derived, opaque-identity, or unresolved-source evidence into a stronger category;
- any external benchmark redistribution is consistent with the verified source/reuse status rather than inferred from the article licence.

Then run the broader [Publication readiness](publication-readiness.md) audit, which also checks preregistration alignment, source/data identity, exclusions, AOI review state, software/archive identity, and the boundary between software demonstrations and empirical evidence. The [Study-design templates](study-design-templates.md) provide copy-ready records for those inputs.

[Research recipes →](research-recipes.md) · [Study-design templates →](study-design-templates.md) · [Study lifecycle →](study-lifecycle.md) · [Publication readiness →](publication-readiness.md) · [Research terminology →](research-terminology.md) · [Worked static study →](worked-advertising-study.md) · [Worked dynamic study →](worked-dynamic-aoi-study.md)
