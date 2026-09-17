# Validation reporting cookbook

Use these patterns when turning an event-model validation workflow into Methods, Results, captions, tables, supplements, or archive notes. The goal is to preserve exactly what the design supports—no more and no less.

!!! note "Templates are wording aids, not evidence"
    Replace placeholders with the actual study record. A polished sentence cannot upgrade a weak split, unknown identity mapping, derived sampling condition, or synthetic demonstration into stronger evidence.

## Participant-disjoint validation

### Methods pattern

> Event models were evaluated using `<k>` participant-disjoint folds defined by `<participant identity field>`. Participants in each test fold were absent from the corresponding training fold, and all compared models were evaluated on the same held-out observations.

### Results pattern

> Held-out performance was summarized across participant-disjoint folds using `<sample metrics>` and, where temporal segmentation was relevant, `<event-level metrics>`.

### Archive note

```text
split_unit: participant
split_field: participant_id
n_splits: <k>
participant_overlap_train_test: 0 in every fold
matched_test_rows_across_models: true
```

Do not replace *participant-disjoint* with generic *cross-validated* wording if participant generalization is central to the claim.

## Source-token-disjoint evidence

### Methods pattern

> Evaluation was source-token-disjoint using `<token field>`. An authoritative token→participant mapping was unavailable; therefore participant-disjointness was not claimed.

### Results boundary

> The reported metrics quantify generalization across held-out source tokens under the available identity evidence.

Avoid wording that silently promotes opaque tokens to people.

## Calibration versus correctness

### Methods pattern

> Probabilistic predictions were evaluated using multiclass Brier score and top-label expected calibration error (ECE) on held-out observations. Confidence/coverage was examined across prespecified thresholds.

### Results pattern

> The model showed `<Brier>` multiclass Brier score and `<ECE>` ECE under the prespecified held-out design. These values describe probability calibration and do not imply that every individual prediction is correct.

### Caption qualifier

> Calibration diagnostic on held-out predictions; lower calibration error does not guarantee correct individual classifications.

## Sample-level versus event-level performance

### Methods pattern

> Sample-level discrimination and contiguous event segmentation were treated as separate estimands. Sample performance was summarized with `<balanced accuracy / macro-F1>`, while event performance was evaluated with `<event-F1 / temporal IoU / onset-offset error>`.

### Results pattern

> Model ordering differed across `<sample metric>` and `<event metric>`, so no single aggregate score was treated as a complete measure of event quality.

Avoid:

> High sample accuracy demonstrated accurate event boundaries.

## Native versus derived sampling rate

### Native condition

> Data were acquired natively at `<rate>` Hz and analysed at the same rate.

### Derived condition

> Data were acquired natively at `<native rate>` Hz and evaluated on a derived `<analysis rate>` Hz condition produced using `<resampling / label-purity rule>`.

### Mandatory qualifier for derived lower-rate evidence

> The derived condition does not establish native `<analysis rate>` Hz device validity.

If the tracker of interest is Gazepoint/GP3, do not convert derived lower-rate evidence into a GP3 validity claim.

## Model selection versus confirmatory evaluation

### Prespecified model

> The primary event model and decision threshold were prespecified before final held-out evaluation.

### Tuned model or threshold

> Model/threshold selection used `<selection data / inner folds>`, while final performance was evaluated on separate held-out `<participants/stimuli/dataset>` not used for selection.

### Exploratory analysis

> The confidence threshold was selected after inspecting validation diagnostics and is therefore reported as exploratory rather than confirmatory.

Do not tune a threshold on the final test set and then describe that same test performance as an untouched confirmatory estimate.

## Confidence-based abstention

### Methods pattern

> Predictions below confidence `<threshold>` were assigned to an abstention policy for the prespecified selective-analysis diagnostic. Coverage and retained-sample accuracy were reported together.

### Results pattern

> At confidence threshold `<threshold>`, coverage was `<coverage>` and accuracy among retained predictions was `<accuracy>`.

### Boundary

> The threshold is study-specific and is not a universal confidence cutoff.

Never report selective accuracy without the corresponding coverage.

## Synthetic demonstration versus benchmark evidence

### Software demonstration

> The deterministic synthetic example was used to verify the software workflow, output contract, leakage checks, calibration diagnostics, and provenance records. It was classified `synthetic_demo_not_empirical_evidence`.

### Empirical benchmark

> Empirical validation used `<named benchmark/corpus>` under the documented source, label, identity, rate, and split constraints.

Synthetic output can verify code paths. It cannot establish tracker validity, benchmark performance, native 60 Hz validity, Gazepoint/GP3 validity, or population generalization.

## Model comparison without a universal winner claim

### Appropriate

> Under this dataset, split design, label source, sampling condition, and metric, `<model>` produced the reported value. Results are presented across multiple estimands rather than as a universal model ranking.

### Overstated

> `<model>` is the best eye-event classifier.

A model can lead on sample macro-F1 while another leads on event boundary fidelity, calibration, latency, robustness, or a different population/device.

## Compact Methods paragraph template

> Gaze samples were labelled using `<reference source>`. Event models were evaluated with `<k>` `<participant/stimulus/source-token/dataset>`-disjoint folds. `<Models>` were fitted independently within each training fold and evaluated on matched held-out observations. The analysed sampling condition was `<native/derived>` at `<rate>` Hz; when derived, the source was acquired at `<native rate>` Hz using `<derivation rule>`. Sample-level performance was assessed using `<metrics>`, event segmentation using `<metrics>`, and probabilistic calibration using `<Brier/ECE>`. `<Threshold/abstention rule>` was `<prespecified/exploratory>` and coverage was reported with selective accuracy. Software identity, fold assignments, predictions, model parameters, source/output fingerprints, and the evidence boundary were retained in the analysis archive.

## Compact Results paragraph template

> Across the prespecified held-out folds, `<model>` achieved `<sample-level values>`, while event-level evaluation yielded `<event values>`. Probabilistic predictions showed `<calibration values>`. At confidence threshold `<threshold>`, coverage was `<coverage>` with retained-sample accuracy `<accuracy>`. These results apply to the stated label source, split unit, sampling condition, and dataset; they do not by themselves establish validity for a different device, task, population, or native sampling regime.

## Table footnote template

> **Note.** Sample-level, event-level, and calibration measures are distinct estimands. Folds are `<held-out unit>`-disjoint. `<Analysis rate>` Hz is `<native/derived>`; derived lower-rate results do not establish native-device validity. Synthetic/demo rows, if present, are software demonstrations rather than empirical validation evidence.

## Figure-caption template

> Held-out `<participant/stimulus/etc.>` validation of `<models>` under `<native/derived>` `<rate>` Hz analysis. Confidence/calibration panels apply only to probabilistic models. The figure does not imply a universal model ranking or validity outside the stated dataset, label source, device/rate condition, and split design.

## Final language check

Before submission, search the manuscript for these terms and verify each is justified by the archived design:

- `participant-disjoint`;
- `held out`;
- `validated`;
- `calibrated`;
- `native 60 Hz`;
- `60 Hz` without native/derived qualification;
- `best`, `superior`, or `outperforms`;
- `accurate event boundaries`;
- `generalizes`;
- `Gazepoint` / `GP3`.

Then cross-check the [Publication-readiness checklist](publication-readiness.md) and the generated [Evidence status](evidence-status.md).

[Validation clinic →](event-model-validation-clinic.md) · [Reproducible reporting →](reproducible-reporting.md) · [Publication readiness →](publication-readiness.md) · [Validation guide →](validation-evidence-guide.md)
