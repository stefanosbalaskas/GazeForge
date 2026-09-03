<div align="center">

# GazeForge

### Auditable AI for eye-tracking research

**Machine learning, computer vision, event modelling, semantic AOIs, scanpaths, validation, and provenance — without turning eye-tracking analysis into a black box.**

[![CI](https://github.com/stefanosbalaskas/GazeForge/actions/workflows/ci.yml/badge.svg)](https://github.com/stefanosbalaskas/GazeForge/actions/workflows/ci.yml)
[![Docs](https://github.com/stefanosbalaskas/GazeForge/actions/workflows/docs.yml/badge.svg)](https://github.com/stefanosbalaskas/GazeForge/actions/workflows/docs.yml)
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.12%20%7C%203.14-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-alpha-orange)](CHANGELOG.md)

[Website](https://stefanosbalaskas.github.io/GazeForge/) · [Frozen evidence](docs/frozen-evidence.md) · [Validation status](docs/validation-status.md) · [For Gazepoint / GP3](docs/gazepoint-gp3.md) · [Roadmap](https://github.com/stefanosbalaskas/GazeForge/issues)

</div>

---

GazeForge is a vendor-neutral Python research-software package for integrating **AI into the analysis of eye-tracking data**. It supports machine-learning-assisted quality control, event classification, semantic AOIs, sequence analysis, and benchmark validation while keeping transformations, uncertainty, model identity, sampling assumptions, and human review visible.

> **Scientific contract:** AI may propose, score, classify, embed, or flag. It must not silently alter the empirical record.

GazeForge does **not** infer diagnoses, emotions, personality, protected traits, or unsupported latent mental states from gaze.

## First frozen external empirical evidence

The first audited external benchmark tranche is now frozen from the public **Lund2013** expert-labelled corpus. GazeForge verifies the exact upstream source files at a pinned commit, derives lower-rate human-reference data with explicit boundary-purity rules, evaluates all models on identical participant-held-out folds, and stores only fingerprinted JSON evidence in this repository.

Primary RA-labelled **derived 60 Hz** results:

| Model | Accuracy | Balanced accuracy | Macro-F1 | Event-F1 | Event IoU |
| --- | ---: | ---: | ---: | ---: | ---: |
| **I-VT** | 0.637 | 0.388 | 0.287 | **0.626** | **0.921** |
| **RandomForest** | 0.676 | 0.670 | 0.595 | 0.440 | 0.892 |
| **ContextMLP** | **0.694** | **0.679** | **0.649** | 0.535 | 0.900 |

The result is deliberately **not** summarized as “AI beats I-VT.” Learned models are substantially stronger for sample-level multiclass classification, whereas transparent I-VT is stronger for contiguous event segmentation and boundary timing. The MN annotator sensitivity analysis reproduces this broad pattern.

Human MN–RA agreement is also strong: native 500 Hz κ = **0.815** with exact agreement **0.893**; independently derived 60 Hz κ = **0.799** with exact agreement **0.880**. Video has the lowest agreement among the benchmark stimulus families.

The frozen suite fingerprint is:

```text
5dc6d6336b505b0a2283fe64d478a27b0394c9568a86fc4eb4d2771b8d600f93
```

**Important limitation:** Lund2013 is natively 500 Hz. The 60 Hz analyses are derived lower-rate evidence and are **not native GP3/60 Hz device validation**. A genuinely native 60 Hz/GP3-class manually labelled event corpus remains a major evidence requirement.

[Inspect the frozen evidence →](docs/frozen-evidence.md) · [See the full validation matrix →](docs/validation-status.md)

## What GazeForge adds to eye-tracking analysis

| Layer | Capabilities |
| --- | --- |
| **Data & QC** | Canonical gaze schema, Gazepoint adapters, sampling-rate inference, anomaly flags, trial-quality scores, calibration-drift diagnostics |
| **Eye events** | Transparent I-VT and angular I-VT, Random Forest classification, temporal-context MLP, calibrated probabilities, abstention metadata |
| **Semantic AOIs** | Human-defined AOIs, optional OWL-ViT proposals, review/correction logs, dynamic AOI keyframes, guarded interpolation |
| **Sequences** | Semantic scanpaths, motifs, TF-IDF/SVD embeddings, cosine similarity, clustering |
| **Validation** | Participant-held-out folds, leave-one-dataset-out validation, calibration, event-level temporal matching, sampling/purity sensitivity |
| **Auditability** | Data fingerprints, model cards, benchmark cards, provenance records, verified source manifests, deterministic frozen benchmark reports |

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

## Validation matrix

| Benchmark | Reference | Native rate | GazeForge status |
| --- | --- | ---: | --- |
| **Lund2013** | paired expert manual event labels | 500 Hz | **first frozen external evidence complete**: native/derived human agreement, derived 60 Hz matched-fold modelling, MN sensitivity, stimulus-family results, sampling×purity sensitivity |
| **Hollywood2EM** | expert-corrected manual event labels | 500 Hz | adapter and Lund↔Hollywood cross-dataset infrastructure implemented; authoritative identity/coordinate audit still required |
| **Gaze-in-the-Wild** | five trained human annotators | published 120 Hz acquisition | native human-reference adapter and protocol implemented; authoritative data audit pending |
| **VISUS** | two human dynamic-AOI annotators | 60 Hz | dynamic-AOI evaluation infrastructure and candidate protocol implemented; authoritative current dataset copy pending |

GazeForge never upgrades derived evidence into a stronger evidence category. Resampled 60 Hz results remain labelled **derived human-reference evidence**, and cross-dataset results remain blocked when identity or coordinate evidence is unresolved.

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

A model trained at one sampling rate is not silently applied at an incompatible rate. Temporal-context models build context windows separately inside each participant/trial boundary.

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

Learned models are refitted inside every fold. GazeForge also provides leave-one-dataset-out validation, calibration diagnostics, matched-model comparisons, stimulus-family summaries, and event-level temporal IoU / boundary-error metrics. Cross-validation folds are not treated as independent replicates for naive significance tests.

## Reproducible Lund2013 workflows

Acquire the exact pinned external labelled-data checkout without bundling it into GazeForge:

```bash
gazeforge lund2013-fetch ./external/lund2013
```

The fetcher verifies every expected MATLAB file against the upstream Git blob SHA and byte size and writes a fingerprinted local source manifest.

Run and freeze the complete evidence suite:

```bash
gazeforge lund2013-suite \
  ./external/lund2013 \
  validation/evidence/lund2013 \
  --target-rate 60 \
  --min-label-purity 0.75 \
  --target-rates 120,90,60,30 \
  --purities 0.60,0.75,0.90 \
  --n-splits 5 \
  --n-estimators 200 \
  --ivt-threshold-deg-s 45 \
  --context-radius-ms 50 \
  --hidden-layers 64,32
```

Revalidate the frozen suite and every child report:

```bash
gazeforge lund2013-suite-validate validation/evidence/lund2013
```

Every frozen report carries a deterministic SHA-256 fingerprint. Ambiguous event-boundary samples are counted before exclusion, all sensitivity settings remain visible, and the website displays only reports whose fingerprints revalidate successfully.

## Project status

GazeForge is under active alpha development. The first external empirical benchmark tranche is now frozen and publicly rendered, but that does not establish mature performance across trackers or tasks.

### Implemented and frozen

- vendor-neutral gaze schema and Gazepoint interoperability
- auditable QC and anomaly scoring
- classical, probabilistic, and temporal eye-event models
- calibration and confidence/coverage diagnostics
- static and dynamic semantic AOIs with human review
- semantic scanpaths, motifs, embeddings, and clustering
- participant-held-out and dataset-held-out validation
- sample-level and event-level benchmark metrics
- evidence-aware benchmark taxonomy and deterministic provenance
- pinned and integrity-checked Lund2013 acquisition
- **five-report Lund2013 external empirical suite with verified fingerprints**
- native/derived MN–RA human agreement
- derived 60 Hz RA primary model comparison and MN annotator sensitivity
- stimulus-family and sampling-rate × annotation-purity sensitivity analyses
- integrity-checked frozen-evidence website generation
- CI across Python 3.10/3.12/3.14 on Linux, Windows, and macOS

### Still required before a stable scientific release

- **native 60 Hz/GP3-class expert-labelled event validation**
- authoritative audits and frozen cross-dataset results for additional external benchmarks
- validated dynamic object-detection/tracking backend results
- broader cross-dataset validation after coordinate and identity audits
- final API stability and release packaging

The active benchmark plan is tracked in [Issue #1](https://github.com/stefanosbalaskas/GazeForge/issues/1).

## Relationship to the wider research-software ecosystem

GazeForge complements rather than replaces deterministic eye-tracking and psychophysiology tooling. Its role is the **auditable AI layer**: prediction, semantic interpretation, representation learning, validation, and provenance around ordinary research tables.

## Scientific governance

Confirmatory workflows should lock model/version information, sampling rates, analysis exclusions, validation splits, and human review decisions before final inference. External benchmark files remain external unless their reuse terms clearly permit redistribution.

See [Scientific governance](docs/scientific-governance.md).

## Documentation

The documentation source lives under `docs/`, is strict-built with MkDocs Material, and deploys to GitHub Pages after successful builds:

**https://stefanosbalaskas.github.io/GazeForge/**

## Citation

A formal software-paper citation will be added with the public release/paper freeze. Until then, cite the repository together with the exact GazeForge version or commit SHA used in reproducible work. Machine-readable citation metadata is available in [`CITATION.cff`](CITATION.cff).

## License

MIT License. External validation datasets retain their own licenses and are not silently redistributed by GazeForge.
