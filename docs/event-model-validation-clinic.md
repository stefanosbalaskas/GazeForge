# Event-model validation clinic

<div class="gf-doc-kind" role="note" aria-label="Documentation type">
<strong>Validation how-to</strong> · Evaluate learned event models on explicit held-out units with sample, event, calibration, and coverage evidence.
</div>

<nav class="gf-help" aria-label="Documentation help">
<a href="gazeforge-tour.md">Tour</a>
<a href="documentation-map.md">Task map</a>
<a href="troubleshooting.md">Troubleshooting</a>
<a href="runnable-examples.md">Examples</a>
<a href="https://github.com/stefanosbalaskas/GazeForge/issues">Ask / report</a>
</nav>


Use this clinic when you have labelled gaze events and want to evaluate a learned event classifier without confusing **model fitting** with **model validation**. The route below keeps identity, leakage controls, probabilities, event timing, sampling-rate provenance, and claim strength visible from the start.

!!! warning "A successful model fit is not validation"
    Training accuracy, a clean confusion matrix on reused data, or a synthetic worked example does not establish performance for new participants, devices, tasks, populations, or sampling regimes. Validation requires a prespecified reference and a held-out design that matches the claim.

## Start with the scientific contract

Before fitting anything, write down five things:

| Question | Record explicitly |
| --- | --- |
| What is being predicted? | event classes such as fixation/saccade/noise, including any ambiguous/unlabelled state |
| What is the reference? | annotator/source, adjudication rule, label version, provenance |
| What unit must generalize? | participant, stimulus, dataset, or another defensible unit |
| What rate is analysed? | native acquisition rate versus a derived/resampled analysis rate |
| What is the estimand? | sample discrimination, contiguous event segmentation, probability calibration, or a combination |

If you cannot answer those questions, do not let a model metric substitute for the missing design decision.

## 1. Preserve participant identity before splitting

For participant-generalization claims, participant identity must be present before any train/test split is created.

```python
required = {"participant_id", "trial_id", "timestamp_ms", "event_label"}
missing = required - set(labelled_gaze.columns)
if missing:
    raise ValueError(f"Missing validation fields: {sorted(missing)}")
```

Do not reconstruct participant identity by assumption from filenames, opaque source tokens, or trial order. A **source-token-disjoint** split is not participant-disjoint unless an authoritative token→participant mapping supports that promotion.

## 2. Use group-held-out folds, not row-wise random splits

Gaze samples are repeated observations. Randomly splitting rows can place samples from the same participant in both training and test data, inflating apparent generalization.

GazeForge exposes a matched grouped comparison surface:

```python
from gazeforge import compare_event_models_grouped

comparison = compare_event_models_grouped(
    labelled_gaze,
    label_col="event_label",
    group_col="participant_id",
    n_splits=5,
    sampling_rate_hz=60.0,
    include_event_level_metrics=True,
)
```

`compare_event_models_grouped()` fits each learned model from scratch inside every fold, checks group leakage, and evaluates **I-VT, Random Forest, and ContextMLP on the same held-out rows**.

### Mechanical leakage check

Retain a split ledger and verify the participant sets explicitly:

```python
train_ids = set(train["participant_id"].astype(str))
test_ids = set(test["participant_id"].astype(str))
assert train_ids.isdisjoint(test_ids)
```

The phrase *participant-disjoint* should be backed by this identity contract, not just by a generic “cross-validation” label.

## 3. Keep a transparent baseline

A learned model should not erase the transparent reference rule.

```python
from gazeforge import ivt_classify_events

ivt = ivt_classify_events(
    heldout_gaze,
    sampling_rate_hz=60.0,
    velocity_threshold_px_s=1000.0,
)
```

The threshold is an explicit analysis parameter. It is **not** a universal physiological cutoff. If an angular I-VT rule is used, record display geometry/viewing assumptions and the threshold in degrees/second.

## 4. Retain probabilities and model identity

For learned classifiers, keep the probability columns rather than reducing output to a final label alone.

Typical held-out output contains:

```text
participant_id
trial_id
timestamp_ms
event_label
predicted_event
event_confidence
p_event_fixation
p_event_saccade
event_model
event_model_version
validation_fold
```

Those fields make thresholding, calibration, abstention, and later auditing possible without refitting the model.

## 5. Calibration is different from correctness

For probabilistic classifiers, inspect Brier score and calibration rather than interpreting confidence as self-validating.

```python
from gazeforge import evaluate_event_calibration

diagnostics = evaluate_event_calibration(
    learned_predictions,
    true_label_col="event_label",
    n_bins=10,
)
```

The output contains:

- multiclass Brier score;
- expected calibration error (ECE);
- confidence-bin calibration table; and
- selective accuracy / coverage diagnostics.

A calibrated model can still make incorrect individual predictions. Calibration is a distributional relationship between predicted probability and observed frequency.

## 6. Treat abstention as a policy, not a magic threshold

Confidence thresholds trade coverage for retained-sample performance.

```python
from gazeforge import selective_accuracy_curve

curve = selective_accuracy_curve(
    learned_predictions,
    thresholds=(0.0, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95),
)
```

Do not select a threshold after inspecting the final confirmatory test set and then report it as if prespecified. If a threshold is tuned, separate **model/threshold selection data** from **final confirmatory evaluation data**, or describe the exercise as exploratory.

## 7. Separate sample-level and event-level estimands

A sample classifier can be strong while event boundaries are poor. Report the layers separately.

### Sample-level

Useful measures include:

- balanced accuracy;
- macro-F1;
- class-specific precision/recall;
- Brier score and ECE for probabilities.

### Event-level

When temporal segmentation matters, also retain:

- event precision / recall / F1;
- matched temporal IoU;
- onset error;
- offset error;
- duration error.

GazeForge's grouped comparison can calculate both families on the same held-out folds. Do not substitute one for the other.

## 8. Compare models on identical held-out observations

If model A and model B are compared, keep the folds and held-out rows matched. Otherwise an apparent difference can reflect different test composition rather than model behaviour.

The grouped comparison result contains:

```python
comparison.predictions
comparison.fold_metrics
comparison.summary
comparison.design
```

Retain `validation_fold`, `comparison_model`, and the held-out row identity in the archive.

## 9. Name the sampling-rate condition correctly

Acquisition and analysis rate are different facts.

**Native condition**

```text
tracker native rate: 60 Hz
analysis rate: 60 Hz
analysis-rate status: native
```

**Derived condition**

```text
tracker native rate: 500 Hz
analysis rate: 60 Hz
analysis-rate status: derived
resampling rule: <prespecified rule>
```

Derived 60 Hz evidence remains derived. It does not become native 60 Hz or GP3 validation because the analysis grid is 60 Hz.

## 10. Freeze a reviewable validation bundle

At minimum, archive:

```text
source/reference-label fingerprint
participant split ledger
held-out predictions + probabilities
sample-level fold metrics
event-level fold metrics
calibration bins
confidence/coverage table
threshold/abstention policy
model parameters + random seed
software version / exact commit
native/derived rate record
evidence-boundary statement
```

The executable [worked event-model validation study](runnable-examples.md#7-worked-event-model-validation-study) writes this structure from deterministic synthetic/demo data.

## Claim-safe interpretation

### Participant-disjoint validation

**Appropriate:**

> Models were fitted within four participant-disjoint folds and evaluated on participants absent from the corresponding training fold. All compared methods used the same held-out observations.

**Overstated:**

> Cross-validation proves the model generalizes to any eye tracker or population.

### Calibration

**Appropriate:**

> Held-out probabilities were evaluated using multiclass Brier score and top-label expected calibration error.

**Overstated:**

> The model was calibrated, therefore its individual predictions were correct.

### Sample versus event performance

**Appropriate:**

> Sample-level macro-F1 and event-level temporal matching metrics were reported separately.

**Overstated:**

> High sample classification accuracy demonstrates accurate event boundaries.

### Synthetic demonstration

**Appropriate:**

> The worked example demonstrates the validation software contract using deterministic synthetic labels.

**Overstated:**

> The worked example validates GazeForge for native 60 Hz or GP3 recordings.

## Before manuscript freeze

Use the [Validation reporting cookbook](validation-reporting-cookbook.md) for copy-ready wording, then check [Publication readiness](publication-readiness.md). For benchmark-specific empirical claims, use the generated [Evidence status](evidence-status.md) and [Validation guide](validation-evidence-guide.md), not this synthetic clinic.

[Run the worked validation study →](runnable-examples.md#7-worked-event-model-validation-study) · [Model comparison →](model-comparison.md) · [Calibration →](calibration.md) · [Event-level evaluation →](event-level-evaluation.md) · [Reporting cookbook →](validation-reporting-cookbook.md)
