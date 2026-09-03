# Research workflow patterns

GazeForge is most useful when AI is one transparent component inside a broader eye-tracking design. This page shows common workflow patterns and the evidence each one requires.

## 1. AI-assisted quality control

**Question:** Which trials or samples deserve inspection before analysis?

```text
raw gaze → canonical table → QC metrics → anomaly flags → researcher review → documented exclusions
```

Recommended components:

- canonical schema;
- missingness/off-screen/gap summaries;
- `ai_flag_anomalies()`;
- `score_trial_quality()`;
- audit/provenance record.

The AI flag should be treated as a prioritization signal, not an automatic deletion rule.

## 2. Trainable eye-event classification

**Question:** Can a labelled corpus support fixation/saccade/pursuit classification for this acquisition regime?

```text
human-labelled training data
          │
          ├── participant-held-out validation
          ▼
   event model + model card
          │
          ▼
new compatible-rate gaze → probabilities/confidence → review/analysis
```

Recommended evidence:

- participant-disjoint validation;
- sampling-rate compatibility;
- macro-F1/balanced accuracy;
- probabilistic calibration where applicable;
- event-level F1 and temporal IoU;
- human-human agreement when more than one annotator is available.

Do not evaluate only on random sample rows from participants that also appear in training.

## 3. Compare a transparent detector against learned models

**Question:** Does a learned model add value beyond a classical rule-based baseline?

Use matched test folds for:

- I-VT;
- Random Forest;
- ContextMLP.

```python
from gazeforge import compare_event_models_grouped

comparison = compare_event_models_grouped(
    labelled_samples,
    label_col="event_label",
    group_col="participant_id",
    n_splits=5,
    sampling_rate_hz=60,
)
```

The same held-out rows are used for every model. Calibration is reported only for methods that genuinely return probabilities.

## 4. Sampling-rate robustness analysis

**Question:** Would conclusions change if temporal resolution or event-boundary purity changed?

```python
from gazeforge import evaluate_sampling_purity_sensitivity

surface = evaluate_sampling_purity_sensitivity(
    high_rate_human_labels,
    target_sampling_rates_hz=(120, 90, 60, 30),
    min_label_purities=(0.60, 0.75, 0.90),
    source_sampling_rate_hz=500,
)
```

Interpret ambiguity/retention and performance together. Do not choose the apparent best cell without considering how many difficult boundary samples were excluded.

For Lund2013, use the dedicated [sensitivity workflow](lund-sensitivity.md).

## 5. Human-reviewed semantic AOIs

**Question:** Can computer vision accelerate AOI definition without making the AOI construction opaque?

```text
stimulus → semantic detector → candidate boxes + confidence
                               │
                               ▼
                         human AOI review
                               │
                               ▼
                      locked AOI definition
                               │
                               ▼
                        fixation assignment
```

Recommended practice:

- retain model name/version;
- retain candidate confidence;
- log accept/reject/relabel/edit decisions;
- freeze AOIs before confirmatory outcome testing;
- evaluate model-human IoU on a separate annotated stimulus set when possible.

## 6. Dynamic video AOIs

**Question:** How should gaze be mapped to moving objects or interface elements?

Use timestamped AOI keyframes rather than one static rectangle for the entire trial.

GazeForge supports:

- dynamic AOI keyframes;
- maximum interpolation gaps;
- no silent extrapolation beyond observed keyframes;
- fixation mapping against time-varying geometry;
- time-grid model-human/human-human IoU evaluation.

The VISUS benchmark is the current native-60-Hz human-AOI validation candidate.

## 7. Semantic scanpath analysis

**Question:** How do participants move attention between meaningful regions rather than raw coordinates?

```text
fixations → AOI assignment → semantic sequence → motifs / embedding / similarity / clustering
```

Use this layer when the scientific construct concerns transitions or ordered attentional strategies.

Available representations include:

- semantic AOI sequences;
- n-gram motifs;
- TF-IDF/SVD embeddings;
- cosine similarity;
- clustering.

Learned representations should be validated against meaningful downstream or known-group criteria rather than interpreted solely because clusters are visually separable.

## 8. Cross-dataset generalization

**Question:** Does an event model transfer beyond one laboratory dataset?

GazeForge supports leave-one-dataset-out designs, but cross-dataset validation is more demanding than concatenating tables.

Before fitting, verify:

- participant identities cannot collide across datasets;
- event labels are semantically harmonized;
- coordinate units are comparable for unit-sensitive features;
- sampling-rate differences are explicit;
- exclusions are matched;
- human versus algorithm-generated ground truth is clearly distinguished.

The Lund2013 ↔ Hollywood2EM workflow intentionally blocks unit-sensitive modelling while Hollywood2 coordinate semantics remain unaudited.

## 9. Multimodal extension

GazeForge's future multimodal layer is intended to connect gaze with pupil, EDA, PPG/HRV, and related signals without allowing an AI model to collapse those channels into unsupported psychological labels.

A defensible multimodal workflow will require:

- synchronized clocks/events;
- channel-specific QC;
- explicit feature windows;
- participant-held-out validation;
- ablation analyses showing what each modality contributes;
- calibrated uncertainty;
- interpretation at the level of observable/prespecified outcomes.

This remains roadmap work rather than a mature current claim.

## Choose the workflow from the scientific question

| Scientific need | Start with | Main validation risk |
| --- | --- | --- |
| identify suspicious recordings | QC + anomaly flags | treating flags as automatic exclusions |
| classify eye events | event models | participant leakage / sampling mismatch |
| compare detectors | matched folds | different test rows across models |
| study lower-rate robustness | sampling sensitivity | hiding ambiguity/retention trade-offs |
| define static AOIs faster | semantic AOI proposals | unreviewed model boxes |
| analyse video AOIs | dynamic AOIs | unsupported interpolation/extrapolation |
| compare attentional strategies | semantic scanpaths | overinterpreting unsupervised structure |
| transfer across datasets | dataset holdouts | incompatible labels/units/rates |

The common principle is the same: **model output should become inspectable evidence before it becomes an analytic decision.**
