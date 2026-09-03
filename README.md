<div align="center">

# GazeForge

### Auditable AI for eye-tracking research

**Machine learning, computer vision, event modelling, semantic AOIs, scanpaths, validation, and provenance — without turning eye-tracking analysis into a black box.**

[![CI](https://github.com/stefanosbalaskas/GazeForge/actions/workflows/ci.yml/badge.svg)](https://github.com/stefanosbalaskas/GazeForge/actions/workflows/ci.yml)
[![Docs](https://github.com/stefanosbalaskas/GazeForge/actions/workflows/docs.yml/badge.svg)](https://github.com/stefanosbalaskas/GazeForge/actions/workflows/docs.yml)
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.12%20%7C%203.14-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-alpha-orange)](CHANGELOG.md)

[Website](https://stefanosbalaskas.github.io/GazeForge/) · [Getting started](docs/getting-started.md) · [Architecture](docs/architecture.md) · [Validation status](docs/validation-status.md) · [Roadmap](https://github.com/stefanosbalaskas/GazeForge/issues)

</div>

---

GazeForge is a vendor-neutral Python research-software package for integrating **AI into the analysis of eye-tracking data**. It is designed for research workflows where machine learning can assist with quality control, event classification, AOI construction, sequence analysis, and benchmark validation while every important transformation remains observable and auditable.

> **Scientific contract:** AI may propose, score, classify, embed, or flag. It must not silently alter the empirical record.

GazeForge does **not** infer diagnoses, emotions, personality, protected traits, or unsupported latent mental states from gaze.

## What GazeForge adds to eye-tracking analysis

| Layer | Capabilities |
| --- | --- |
| **Data & QC** | Canonical gaze schema, Gazepoint adapters, sampling-rate inference, anomaly flags, trial-quality scores, calibration-drift diagnostics |
| **Eye events** | Transparent I-VT, angular I-VT, Random Forest classification, temporal-context MLP, calibrated probabilities, abstention metadata |
| **Semantic AOIs** | Human-defined AOIs, optional OWL-ViT proposals, review/correction logs, dynamic AOI keyframes, guarded interpolation |
| **Sequences** | Semantic scanpaths, motifs, TF-IDF/SVD embeddings, cosine similarity, clustering |
| **Validation** | Participant-held-out folds, leave-one-dataset-out validation, calibration, event-level temporal matching, sampling/purity sensitivity |
| **Auditability** | Data fingerprints, model cards, benchmark cards, provenance records, deterministic frozen benchmark reports |

## Why this is different

Many AI-assisted workflows collapse prediction and analysis into a single opaque step. GazeForge separates them.

```text
raw eye-tracking data
        │
        ▼
canonical gaze table
        │
        ├── QC / anomaly scores ─────────────┐
        ├── eye-event probabilities ─────────┤
        ├── semantic AOI proposals ── review ┤
        └── scanpath representations ────────┤
                                             ▼
                                  reviewed analytic table
                                             │
                                             ▼
                              statistics / modelling / report
```

AI outputs remain ordinary data structures with confidence, source, model, sampling-rate, and review metadata. Researchers can inspect or correct them before downstream statistics.

## Validation is part of the package

GazeForge treats validation infrastructure as a core feature rather than a post-hoc demonstration.

| Benchmark | Reference | Native rate | GazeForge status |
| --- | --- | ---: | --- |
| **Lund2013** | paired expert manual event labels | 500 Hz | adapter, human-human agreement, 60 Hz derivation, matched-fold benchmark and sensitivity tooling implemented; frozen empirical reports pending |
| **Hollywood2EM** | expert-corrected manual event labels | 500 Hz | adapter and Lund↔Hollywood cross-dataset infrastructure implemented; coordinate/identity audit required before frozen cross-dataset results |
| **Gaze-in-the-Wild** | five trained human annotators | published 120 Hz acquisition | native human-reference adapter and protocol implemented; file cadence inferred from timestamps; authoritative data audit pending |
| **VISUS** | two human dynamic-AOI annotators | 60 Hz | dynamic-AOI evaluation infrastructure and candidate protocol implemented; authoritative current dataset copy pending |

**Derived 60 Hz evidence is never described as native 60 Hz validation.** A genuinely native 60 Hz/GP3-class manually event-labelled corpus remains an explicit open requirement before device-specific validity claims.

See the [validation status](docs/validation-status.md) and [benchmark evidence model](docs/benchmark-evidence.md).

## Installation

GazeForge is currently alpha research software and is developed from GitHub.

```bash
git clone https://github.com/stefanosbalaskas/GazeForge.git
cd GazeForge
python -m pip install -e ".[dev]"
pytest
```

Optional open-vocabulary semantic AOI detection:

```bash
python -m pip install -e ".[vision]"
```

## Minimal workflow

```python
from gazeforge import ai_flag_anomalies, canonicalize_gaze, simulate_gaze, score_trial_quality

raw = simulate_gaze(n_participants=3, n_trials=2, samples_per_trial=180)
gaze = canonicalize_gaze(raw, sampling_rate_hz=60)
flagged = ai_flag_anomalies(gaze.data, sampling_rate_hz=gaze.sampling_rate_hz)
quality = score_trial_quality(flagged)

print(quality)
```

The input samples remain intact. QC adds scores and flags rather than deleting observations.

## Probabilistic eye-event modelling

```python
from gazeforge import ai_classify_events, train_event_classifier

model = train_event_classifier(
    labelled_samples,
    label_col="event_label",
    sampling_rate_hz=60,
)
classified = ai_classify_events(new_samples, model, sampling_rate_hz=60)
```

A model trained at one sampling rate is not silently applied at an incompatible rate. Temporal-context models build their context windows separately inside each participant/trial boundary.

## Semantic and dynamic AOIs

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

AI AOIs can be accepted, rejected, relabelled, or geometrically corrected while retaining the review history. Dynamic AOIs use timestamped keyframes, bounded interpolation, and no silent temporal extrapolation.

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

Learned models are refitted inside every fold. GazeForge also provides leave-one-dataset-out validation, calibration diagnostics, matched-model comparisons, and event-level temporal IoU / boundary-error metrics.

## Reproducible Lund2013 workflows

Primary 60 Hz benchmark:

```bash
gazeforge lund2013-benchmark /path/to/lund \
  --annotator RA \
  --target-rate 60 \
  --ivt-threshold-deg-s 45 \
  --n-splits 5 \
  --output validation/lund2013-ra-60hz.json
```

Sampling-rate × boundary-purity sensitivity analysis:

```bash
gazeforge lund2013-sensitivity /path/to/lund \
  --annotator RA \
  --target-rates 120,90,60,30 \
  --purities 0.60,0.75,0.90 \
  --ivt-threshold-deg-s 45 \
  --output validation/lund2013-ra-sensitivity.json
```

Every frozen report carries a deterministic SHA-256 fingerprint. Ambiguous event-boundary samples are counted before exclusion, and non-evaluable rate/purity settings remain visible in the sensitivity ledger.

## Project status

GazeForge is under active alpha development. The software architecture, tests, CI, benchmark adapters, validation layers, and documentation are being built before any claim of mature scientific performance.

### Implemented

- vendor-neutral gaze schema and Gazepoint interoperability
- auditable QC and anomaly scoring
- classical, probabilistic, and temporal eye-event models
- calibration and confidence/coverage diagnostics
- static and dynamic semantic AOIs with human review
- semantic scanpaths, motifs, embeddings, and clustering
- participant-held-out and dataset-held-out validation
- sample-level and event-level benchmark metrics
- evidence-aware benchmark taxonomy
- Lund2013, Hollywood2EM, Gaze-in-the-Wild, and VISUS validation infrastructure
- sampling-rate × annotation-purity sensitivity analysis
- deterministic model/data/benchmark provenance

### Still required before a stable scientific release

- frozen empirical reports from audited external dataset copies
- native 60 Hz/GP3-class human event validation
- validated dynamic object-detection/tracking backend results
- broader cross-dataset validation after coordinate and identity audits
- final API stability and release packaging

The active benchmark plan is tracked in [Issue #1](https://github.com/stefanosbalaskas/GazeForge/issues/1).

## Relationship to the wider research-software ecosystem

GazeForge is intended to complement, not replace, deterministic eye-tracking and psychophysiology tooling. Its role is the **auditable AI layer**: prediction, semantic interpretation, representation learning, validation, and provenance around ordinary research tables.

## Scientific governance

Confirmatory workflows should lock model/version information, sampling rates, analysis exclusions, validation splits, and human review decisions before final inference. External benchmark files remain external unless their reuse terms clearly permit redistribution.

See [Scientific governance](docs/scientific-governance.md).

## Documentation

The documentation source lives under `docs/` and is built with MkDocs Material. The project website is configured for:

**https://stefanosbalaskas.github.io/GazeForge/**

Until GitHub Pages is enabled for the repository, the same documentation is continuously checked with `mkdocs build --strict` in CI.

## Citation

A software paper/citation record will be added once the first empirical benchmark tranche and public release are frozen. Until then, use the repository and version/commit SHA in reproducible work. Machine-readable citation metadata is available in [`CITATION.cff`](CITATION.cff).

## License

MIT License. External validation datasets retain their own licenses and are not silently redistributed by GazeForge.
