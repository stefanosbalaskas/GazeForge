# Research recipes

Start here when you have a **study task**, not a module name. Each recipe points to the smallest defensible GazeForge route, names the reviewable artifacts you should retain, and states the scientific boundary that must travel with the result.

!!! warning "Recipes are workflows, not automatic validity"
    A function running successfully establishes software compatibility with the supplied inputs. It does not, by itself, establish device validity, construct validity, label validity, threshold optimality, or substantive psychological interpretation.

## Choose a route

| Research task | Start with | Keep as artifacts | Principal boundary |
| --- | --- | --- | --- |
| Static-stimulus AOI study | [`AOI`](api-reference.md), `map_fixations_to_aois()` | frozen AOI table, review record, fixation assignments, scanpaths | AOI membership is not a psychological state |
| Dynamic/video AOI study | `DynamicAOIKeyframe`, `map_fixations_to_dynamic_aois()` | keyframes, interpolation policy, assignments, review record | bounded interpolation only; no silent extrapolation |
| Real tracker → canonical table → QC | [Real-data import clinic](data-import-clinic.md) | untouched source, canonical table, metadata, QC table | import compatibility is not device validation |
| Transparent event baseline | `ivt_classify_events()` or angular I-VT | explicit threshold, sample labels, event intervals | example thresholds are not universal cutoffs |
| Learned event validation | grouped validation + calibration + event metrics | fold assignments, predictions, calibration/event tables | name the held-out unit and native/derived rate |
| Scanpath / transition analysis | `to_semantic_scanpaths()` | ordered fixation assignments, sequences, motifs/embeddings | sequence structure does not establish motive or intent |
| Manuscript / archive handoff | [Publication readiness](publication-readiness.md) | software identity, manifest, fingerprints, evidence boundary | report only what the design and evidence support |

## Recipe 1 · Static-stimulus semantic AOIs

**Use when:** the relevant regions do not move during the analysed trial.

**Prerequisites:** timestamped fixations or fixation centroids in pixels; explicit stimulus geometry; a documented AOI definition/review process.

```python
from gazeforge import AOI, map_fixations_to_aois, to_semantic_scanpaths

aois = [
    AOI("brand", "brand", 80, 80, 520, 280, source="researcher_defined"),
    AOI("claim", "claim", 80, 340, 940, 650, source="researcher_defined"),
]
assigned = map_fixations_to_aois(fixations, aois, overlap_rule="first")
scanpaths = to_semantic_scanpaths(assigned)
```

**Retain:** AOI definitions, stimulus/version identity, overlap rule, any accept/reject/edit decisions, fixation assignments, semantic scanpaths, and source fingerprints.

**Boundary:** assigning a fixation to `claim` or `brand` records observable gaze-region correspondence. It does not by itself establish comprehension, persuasion, liking, memory, or purchase intention.

[Worked static study →](worked-advertising-study.md) · [Study templates →](study-design-templates.md)

## Recipe 2 · Dynamic/video AOIs

**Use when:** an object, label, product, interface element, or other semantic region changes position or size over time.

```python
from gazeforge import DynamicAOIKeyframe, map_fixations_to_dynamic_aois

keyframes = [
    DynamicAOIKeyframe("product", "product", 0.0, 500, 320, 980, 800),
    DynamicAOIKeyframe("product", "product", 100.0, 620, 320, 1100, 800),
]
assigned = map_fixations_to_dynamic_aois(
    fixations,
    keyframes,
    max_interpolation_gap_ms=100.0,
    overlap_rule="highest_confidence",
)
```

GazeForge interpolates only between observed keyframes whose gap is within the explicit maximum. It **does not extrapolate** before the first or after the last keyframe.

**Retain:** original keyframes/tracks, timestamps, geometry, confidence/source/model metadata, interpolation-gap rule, overlap rule, review decisions, and fixation assignments.

**Boundary:** a detector or tracker can propose dynamic AOIs, but proposal accuracy and fixation-assignment validity require task-appropriate empirical validation. A software demo is not detector validation.

[Worked dynamic study →](worked-dynamic-aoi-study.md) · [Dynamic AOI method →](dynamic-aois.md) · [Dynamic AOI evaluation →](dynamic-aoi-evaluation.md)

## Recipe 3 · Real tracker import → canonical schema → QC

Start with the [Real-data import clinic](data-import-clinic.md). Preserve the raw export and make these values explicit before analysis:

- participant and trial identity columns;
- timestamp column and unit;
- coordinate columns and coordinate basis;
- screen width and height when normalized coordinates must be converted;
- native acquisition rate and separately observed timestamp cadence;
- pupil/validity fields if used.

Then canonicalise and add non-destructive quality flags. Do not silently guess units, rate, geometry, or identity, and do not treat anomaly flags as automatic invalidity labels.

**Retain:** untouched source file/table, canonical table, import mapping, fingerprints, acquisition metadata, QC sample table, trial-quality summary, and any reviewed exclusion decisions.

**Boundary:** successful import or adapter compatibility does **not** establish native-device, Gazepoint, GP3, or measurement validity.

[Import clinic →](data-import-clinic.md) · [Adapters & validation →](adapters-validation.md)

## Recipe 4 · Transparent event baseline

Use a deterministic baseline before a learned event model when you need an inspectable reference rule.

```python
from gazeforge import ivt_classify_events, samples_to_event_intervals

predicted = ivt_classify_events(
    gaze,
    sampling_rate_hz=60.0,
    velocity_threshold_px_s=1000.0,
)
intervals = samples_to_event_intervals(
    predicted,
    label_col="predicted_event",
    sampling_rate_hz=60.0,
)
```

**Retain:** threshold, units, rate, geometry assumptions, sample-level labels, event intervals, and sensitivity checks where the threshold materially affects inference.

**Boundary:** `1000 px/s` in an example is an explicit demonstration setting, not a universal physiological threshold or device-validity result.

[I-VT tutorial →](tutorial-ivt-baseline.md) · [Event-level evaluation →](event-level-evaluation.md)

## Recipe 5 · Learned event-model validation and calibration

A publishable learned-model result needs more than fitted predictions. Predeclare the held-out unit, prevent leakage, retain fold identity, evaluate both sample- and event-level estimands, and inspect probability calibration where probabilities are interpreted.

Use the grouped validation functions appropriate to the model and preserve whether the analysed rate is **native** or **derived**. If identity is only a source token, report a source-token-disjoint split; do not promote it to participant-disjoint.

**Retain:** reference-label provenance, fold assignments, participant/stimulus/dataset identity fields, predictions/probabilities, calibration tables, event-matching results, software/model identity, and sampling-rate provenance.

**Boundary:** good sample-level discrimination does not imply good event segmentation; good calibration does not imply every prediction is correct; derived 60 Hz evidence does not become native 60 Hz evidence.

[Research workflow patterns →](research-workflows.md) · [Calibration →](calibration.md) · [Validation guide →](validation-evidence-guide.md)

## Recipe 6 · Scanpaths, transitions, and motifs

Start from **ordered, reviewed fixation-to-AOI assignments**.

```python
from gazeforge import find_scanpath_motifs, to_semantic_scanpaths

scanpaths = to_semantic_scanpaths(assignments)
motifs = find_scanpath_motifs(scanpaths, ngram_range=(2, 3), min_count=2)
```

If you add learned embeddings or clustering, record vectorizer/reducer settings, random seed, fitted training scope, and the meaning you assign to clusters only after appropriate external or human validation.

**Retain:** fixation order, AOI labels, durations, collapse/drop-unassigned rules, semantic sequences, and any learned representation metadata.

**Boundary:** a recurring sequence is a structural pattern in the recorded representation; it is not direct evidence of strategy, cognition, preference, or intent.

[Methods overview →](methods-overview.md) · [Worked studies →](runnable-examples.md)

## Recipe 7 · Manuscript and archive handoff

Before writing a headline result, freeze the research identity of the analysis:

1. package version and exact commit when using a development checkout;
2. acquisition hardware, native rate, observed cadence, units, geometry, and participant/trial identity;
3. QC/exclusion decisions and their review provenance;
4. event/AOI/scanpath model identity and parameters;
5. validation split unit and leakage checks;
6. native-versus-derived sampling status;
7. source and output fingerprints; and
8. the explicit **evidence boundary**—what the study does not establish.

Use the [Study-design templates](study-design-templates.md) to make those values copy-ready, then run the [Publication-readiness checklist](publication-readiness.md).

## From a recipe to code

- [Runnable examples](runnable-examples.md) gives exact commands and output inventories.
- [Study lifecycle](study-lifecycle.md) connects design, acquisition, QC, modelling, validation, freeze, and publication.
- [Reproducible reporting](reproducible-reporting.md) provides manuscript-facing wording and claim-safe contrasts.
- [Evidence status](evidence-status.md) and the [Benchmark guide](benchmark-guide.md) define the current empirical boundaries.
