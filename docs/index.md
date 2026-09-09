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
[Frozen evidence](frozen-evidence.md){ .md-button }
[For Gazepoint / GP3](gazepoint-gp3.md){ .md-button }
[PyPI](https://pypi.org/project/gazeforge/){ .md-button }
[DOI](https://doi.org/10.5281/zenodo.22650013){ .md-button }
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

## Public alpha release

**GazeForge 0.1.0a1** is the first public alpha release. It is available from [PyPI](https://pypi.org/project/gazeforge/0.1.0a1/) and archived on Zenodo with version DOI [`10.5281/zenodo.22650013`](https://doi.org/10.5281/zenodo.22650013). The release remains intentionally alpha: APIs may change while native 60 Hz/GP3-class validation, broader external benchmark qualification, and remaining dynamic-detection validation are completed.

## First frozen empirical checkpoint

GazeForge now contains its first reviewed external evidence suite from **Lund2013**, pinned to an exact upstream commit and verified file-by-file before analysis. The primary lower-rate analysis derives a 60 Hz human-reference condition from the native 500 Hz expert labels and evaluates all methods on identical participant-held-out folds.

| Model | Balanced accuracy | Macro-F1 | Event-F1 |
| --- | ---: | ---: | ---: |
| **I-VT** | 0.388 | 0.287 | **0.626** |
| **RandomForest** | 0.670 | 0.595 | 0.440 |
| **ContextMLP** | **0.679** | **0.649** | 0.535 |

The result is intentionally multi-criterion: **ContextMLP leads sample-level multiclass classification, while I-VT leads event segmentation and boundary fidelity.** The independent MN annotator sensitivity analysis reproduces that broad pattern. Human MN–RA agreement remains high from native 500 Hz (κ = 0.815) to derived 60 Hz (κ = 0.799).

!!! warning "Derived 60 Hz is not native GP3 validation"
    Lund2013 is a native 500 Hz corpus. These lower-rate results quantify a controlled derivation from expert annotations; they do not establish device-specific validity for a native 60 Hz Gazepoint GP3 recording. Native GP3-class expert-labelled event validation remains a major open evidence gate.

[Inspect all verified Lund tables →](frozen-evidence.md) · [Read the validation interpretation →](validation-status.md)

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
| **Lund2013** | paired expert event labels | 500 Hz | **frozen external event evidence available**; native/derived human agreement, derived 60 Hz modelling, annotator and sampling/purity sensitivity |
| **Hollywood2EM** | sequential student labels with expert-corrected final labels | ≈500 Hz | **reviewed aggregate source-token-held-out evidence available**; token-disjoint only, not participant-disjoint; exact annotation-repository licence and token→participant mapping remain unresolved |
| **Gaze-in-the-Wild** | distributed trained human labellers | published 120 Hz hardware acquisition; exact ProcessData nominal 300 Hz | **frozen exact-distribution participant-disjoint evidence available** on a derived 60-Hz task-agnostic grid; first-party RIT code now verifies task-separated extraction structure and ACE-DNV secondarily corroborates `TrIdx` 1–3, while the complete authoritative numeric `TrIdx`→task mapping, task-stratified validation, native-60-Hz/GP3 validity, acquisition-hardware cadence verification, and quarantine exit remain open |
| **VISUS** | one published curated dynamic-AOI annotation process involving two contributors | 60 Hz | **infrastructure validated, empirical execution pending**; current authoritative distribution and reuse terms unresolved |

</div>

GazeForge never silently upgrades evidence strength. Resampled lower-rate evidence remains labelled as derived, human-human agreement is not treated as an error-free ceiling, and unresolved coordinate or identity evidence blocks stronger cross-dataset claims. For Gaze-in-the-Wild, the reviewed participant-disjoint benchmark remains task-agnostic: first-party task-separated extraction structure and secondary numeric corroboration do not substitute for a complete authoritative `TrIdx`→task mapping, and `TrIdx 4 → Tea_Making` is not inferred by elimination. Published 120 Hz hardware acquisition provenance also remains distinct from the official 300 Hz processed-stream target and from the derived analysis grid; for VISUS, two contributors to one curation process are not treated as two independent annotation streams.

[See the full validation matrix →](validation-status.md) · [Gaze-in-the-Wild task-mapping evidence →](gaze-in-wild-task-mapping-corroboration.md) · [Gaze-in-the-Wild source-resolution status →](gaze-in-wild-source-resolution.md) · [VISUS source-resolution status →](visus-source-resolution.md) · [See frozen empirical evidence →](frozen-evidence.md)

## Quick start

Install the exact public alpha from PyPI:

```bash
python -m pip install "gazeforge==0.1.0a1"
```

For development or commit-pinned research work:

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

GazeForge is **public alpha research software with its first frozen external empirical tranche**. Version `0.1.0a1` is published through PyPI Trusted Publishing and archived on Zenodo, but a stable scientific-performance claim still requires broader independent validation.

- CI spans Python 3.10, 3.12, and 3.14 on Linux, Windows, and macOS.
- Documentation is built strictly and deployed through GitHub Pages.
- External benchmark files are not silently bundled or relicensed.
- Frozen benchmark reports carry deterministic SHA-256 fingerprints and are revalidated before website display.
- The highest-priority event-model evidence gap is a native 60 Hz/GP3-class expert-labelled corpus.

[Scientific governance →](scientific-governance.md) · [Benchmark evidence →](benchmark-evidence.md) · [Roadmap on GitHub →](https://github.com/stefanosbalaskas/GazeForge/issues)
