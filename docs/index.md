---
hide:
  - navigation
  - toc
---

<div class="gf-hero" markdown>

# GazeForge

## Auditable AI for eye-tracking research

Machine learning, computer vision, temporal event modelling, semantic AOIs, scanpaths, validation, and provenance — designed so AI can assist eye-tracking research **without silently rewriting the empirical record**.

[Get started](getting-started.md){ .md-button .md-button--primary }
[For Gazepoint / GP3](gazepoint-gp3.md){ .md-button }
[Frozen evidence](frozen-evidence.md){ .md-button }
[GitHub](https://github.com/stefanosbalaskas/GazeForge){ .md-button }

</div>

<div class="gf-contract" markdown>

### The scientific contract

> **AI may propose, score, classify, embed, or flag. It must not silently alter the empirical record.**

GazeForge keeps predictions, confidence, model identity, sampling-rate assumptions, review decisions, and benchmark provenance visible as ordinary research data.

</div>

<div class="grid cards" markdown>

-   :material-eye-check-outline:{ .lg .middle } **Eye-event AI**

    ---

    Transparent I-VT and angular I-VT baselines, Random Forest classification, temporal-context MLPs, calibrated probabilities, confidence/coverage analysis, and event-level temporal matching.

    [Event modelling →](model-comparison.md)

-   :material-vector-rectangle:{ .lg .middle } **Semantic AOIs**

    ---

    Human-defined and AI-proposed AOIs, optional OWL-ViT open-vocabulary detection, explicit review/correction, dynamic keyframes, bounded interpolation, and fixation assignment.

    [Dynamic AOIs →](dynamic-aois.md)

-   :material-chart-timeline-variant:{ .lg .middle } **Scanpaths & sequences**

    ---

    Semantic scanpaths, motifs, TF-IDF/SVD embeddings, similarity, and clustering without requiring an opaque generative model.

    [Research workflows →](research-workflows.md)

-   :material-shield-check-outline:{ .lg .middle } **Validation & provenance**

    ---

    Participant-held-out folds, leave-one-dataset-out validation, calibration, event-level metrics, evidence-aware dataset cards, fingerprints, and protected frozen reports.

    [Frozen empirical evidence →](frozen-evidence.md)

</div>

## A workflow designed for scientific review

```text
vendor / raw gaze
       │
       ▼
canonical gaze schema
       │
       ├── QC anomaly flags ────────────────┐
       ├── event probabilities ─────────────┤
       ├── semantic AOI proposals ─ review ─┤
       └── scanpath representations ────────┤
                                            ▼
                                  reviewed analytic table
                                            │
                                            ▼
                               statistics / models / report
```

The package does **not** infer diagnoses, emotions, personality, protected traits, or unsupported latent mental states from gaze.

[Choose a research workflow →](research-workflows.md)

## Validation is visible, not implied

<div class="gf-status-grid" markdown>

| Benchmark | Human reference | Native rate | Current role |
| --- | --- | ---: | --- |
| **Lund2013** | paired expert event labels | 500 Hz | primary event benchmark; derived 60 Hz and sampling/purity sensitivity tooling |
| **Hollywood2EM** | expert-corrected event labels | 500 Hz | external cross-dataset candidate after coordinate/identity audit |
| **Gaze-in-the-Wild** | five trained annotators | published 120 Hz | native naturalistic human-reference candidate; file cadence inferred directly |
| **VISUS** | two dynamic-AOI annotators | 60 Hz | native dynamic-AOI candidate |

</div>

**Derived 60 Hz evidence is not treated as native 60 Hz validation.** A native 60 Hz/GP3-class manually labelled event corpus remains an explicit requirement before device-specific validity claims.

[See the full validation matrix →](validation-status.md) · [See frozen empirical evidence →](frozen-evidence.md)

## Quick start

```bash
git clone https://github.com/stefanosbalaskas/GazeForge.git
cd GazeForge
python -m pip install -e ".[dev]"
pytest
```

```python
from gazeforge import ai_flag_anomalies, canonicalize_gaze, simulate_gaze

raw = simulate_gaze(n_participants=3, n_trials=2, samples_per_trial=180)
gaze = canonicalize_gaze(raw, sampling_rate_hz=60)
flagged = ai_flag_anomalies(gaze.data, sampling_rate_hz=60)
```

[Continue with the getting-started guide →](getting-started.md)

## Current project phase

GazeForge is **alpha research software**. The architecture, tests, validation machinery, external benchmark adapters, and governance are being established before a stable scientific-performance claim or package paper is frozen.

- CI spans Python 3.10, 3.12, and 3.14 on Linux, Windows, and macOS.
- Documentation is built with `mkdocs build --strict`.
- External benchmark files are not silently bundled or relicensed.
- Frozen benchmark reports carry deterministic SHA-256 fingerprints and are revalidated before website display.

[Scientific governance →](scientific-governance.md) · [Benchmark evidence →](benchmark-evidence.md) · [Roadmap on GitHub →](https://github.com/stefanosbalaskas/GazeForge/issues)
