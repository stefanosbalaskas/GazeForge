# GazeForge

**Auditable AI for eye-tracking analysis.**

GazeForge is a vendor-neutral Python research-software package for integrating machine learning
and computer vision into eye-tracking analysis without turning the workflow into a black box.

The project is intentionally built around a scientific rule:

> AI may propose, score, classify, embed, or flag; it must not silently alter the empirical record.

## Current alpha capabilities

- Canonical gaze schema and sampling-rate inference.
- Gazepoint plus explicit processed-table adapters for ecosystem interoperability.
- Stable data fingerprints and operation-level provenance.
- Isolation-Forest quality-control flags that never delete samples.
- Sampling-rate-aware probabilistic eye-event classification.
- Boundary-safe temporal-context MLP event classification with explicit abstention metadata.
- Classical pixel I-VT plus geometry-normalized angular I-VT for transparent benchmarking.
- Participant/group-held-out validation with explicit leakage checks.
- Leave-one-dataset-out validation and probability-calibration diagnostics.
- Semantic rectangular AOIs with confidence, source, and model metadata.
- Optional local Hugging Face OWL-ViT open-vocabulary AOI proposals.
- Human review/correction of AI AOIs with a retained review log.
- Timestamped dynamic AOI tracks with gap-limited interpolation and no extrapolation.
- Fixation-to-AOI mapping with explicit overlap rules.
- Semantic scanpaths, n-gram motifs, learned TF-IDF/SVD embeddings, similarity, and clustering.
- AOI agreement, fixation-assignment agreement, and boundary-sensitivity evaluation.
- Benchmark dataset cards and deterministic frozen validation-report infrastructure.
- Native Lund2013 MATLAB ingestion, RA/MN agreement, and explicit 500-to-60-Hz resampling.
- One-command matched-fold Lund2013 angular I-VT/Random Forest/ContextMLP benchmark reports.
- Trial-level quality scores and synthetic gaze generation for examples/tests.
- Machine-readable model cards and audit reports.

## Why this is not "ChatGPT for eye tracking"

GazeForge separates **AI inference** from **scientific execution**. AI outputs are ordinary tables
with confidence scores and model metadata. Researchers can review them before downstream
statistics. The package does not infer diagnoses, emotions, personality, protected traits, or
other unsupported latent mental states from gaze.

## Install for development

```bash
git clone https://github.com/stefanosbalaskas/GazeForge.git
cd GazeForge
python -m pip install -e ".[dev]"
pytest
```

Optional semantic AOI detection:

```bash
python -m pip install -e ".[vision]"
```

The optional provider uses the Transformers zero-shot object-detection pipeline. Model weights are
not bundled into GazeForge.

## Minimal example

```python
from gazeforge import (
    ai_flag_anomalies,
    canonicalize_gaze,
    simulate_gaze,
    score_trial_quality,
)

raw = simulate_gaze(n_participants=3, n_trials=2, samples_per_trial=180)
gaze = canonicalize_gaze(raw, sampling_rate_hz=60)
flagged = ai_flag_anomalies(gaze.data, sampling_rate_hz=gaze.sampling_rate_hz)
quality = score_trial_quality(flagged)

print(quality)
```

## Semantic AOIs

```python
from gazeforge.aoi import HuggingFaceZeroShotAOIProvider, detect_semantic_aois

provider = HuggingFaceZeroShotAOIProvider()
aois = detect_semantic_aois(
    "stimulus.png",
    labels=["logo", "price", "sustainability claim", "product"],
    provider=provider,
    min_confidence=0.10,
)
```

AI-generated AOIs should be reviewed before they are locked for confirmatory analyses.

## Event classification

GazeForge stores the sampling rate used to train each event model and checks it at inference.
A model trained at 250 Hz is therefore not silently applied to a 60 Hz GP3 recording.

```python
from gazeforge.events import ai_classify_events, train_event_classifier

model = train_event_classifier(
    labelled_samples,
    label_col="event_label",
    sampling_rate_hz=60,
)
classified = ai_classify_events(new_samples, model, sampling_rate_hz=60)
```

The first temporal baseline uses boundary-safe context windows:

```python
from gazeforge import ai_classify_events_context, train_context_event_classifier

model = train_context_event_classifier(
    labelled_samples,
    label_col="event_label",
    sampling_rate_hz=60,
    context_radius_ms=50,
)
classified = ai_classify_events_context(new_samples, model, sampling_rate_hz=60)
```

Temporal windows are built separately within each participant/trial and never cross those
boundaries. They are specified in milliseconds and converted to samples using the recording rate.

## Leakage-safe validation

```python
from gazeforge import grouped_event_cross_validate

validation = grouped_event_cross_validate(
    labelled_samples,
    label_col="event_label",
    group_col="participant_id",
    n_splits=5,
    sampling_rate_hz=60,
)
```

A fresh event model is fitted inside every fold, and participants are kept out of the training
partition for the fold in which they are evaluated. Equivalent grouped and dataset-held-out
validators are available for the temporal-context model.

## Lund2013 empirical benchmark

GazeForge can ingest the externally maintained Lund2013 expert-labelled MATLAB recordings,
quantify MN-vs-RA human agreement, derive a label-purity-aware 60 Hz tranche, and compare angular
I-VT at 45°/s, Random Forest, and ContextMLP on identical participant-held-out folds. Raw benchmark
files are not bundled or relicensed by GazeForge.

```bash
gazeforge lund2013-benchmark /path/to/lund \
  --annotator RA --target-rate 60 --ivt-threshold-deg-s 45 --n-splits 5 \
  --output validation/lund2013-ra-60hz.json
```

See `docs/lund2013-benchmark.md` for the ambiguity protocol and planned sensitivity analyses.

## Scientific roadmap

### v0.1 — auditable AI core
- [x] canonical gaze layer
- [x] QC anomaly scoring
- [x] probabilistic event-model API
- [x] semantic AOI provider API
- [x] optional open-vocabulary vision provider
- [x] human AOI review
- [x] semantic scanpaths and learned embeddings
- [x] provenance/model cards
- [x] GP3/eyeprocesspy/gpbiometricspy-compatible adapters
- [x] participant/group-held-out validation utilities
- [x] benchmark cards, evaluation metrics, and frozen validation-report infrastructure
- [x] Lund2013 empirical benchmark ingestion, 60 Hz derivation, and report runner
- [ ] frozen empirical performance reports from a pinned Lund2013 checkout

### v0.2 — validated temporal AI
- [x] temporal-context MLP baseline with boundary-safe windows
- [x] probability calibration and confidence/coverage diagnostics
- [x] participant-held-out and dataset-held-out validation
- [ ] temporal CNN / transformer event models under identical frozen splits
- [x] derived 60 Hz Lund2013 benchmark protocol and runner
- [ ] native 60 Hz expert-labelled GP3-class validation corpus
- [x] dynamic AOI keyframes, interpolation guardrails, and fixation mapping
- [ ] validated video/object-tracking provider implementations

### v0.3 — multimodal and orchestration
- gaze + pupil + EDA + PPG/HRV fusion
- constrained natural-language analysis specifications
- deterministic execution engine
- ONNX export for cross-language inference

## Governance

GazeForge is designed for observable eye-tracking outcomes and reproducible methodological
research. Predictions must be evaluated with participant-level and, where relevant,
stimulus-level holdouts. Model cards should state training data, sampling rates, intended use,
known limitations, and validation evidence.

See `docs/scientific-governance.md`.

## License

MIT.
