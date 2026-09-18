<p align="center">
  <img src="docs/assets/python-suite-logo.png" width="240" alt="Python Suite research packages logo">
</p>

<h1 align="center">GazeForge</h1>

<p align="center"><strong>Auditable AI for eye-tracking research.</strong></p>
<p align="center">Import · QC · eye events · AOIs · scanpaths · validation · provenance · reproducible reporting</p>

<p align="center">
  <a href="https://github.com/stefanosbalaskas/GazeForge/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/stefanosbalaskas/GazeForge/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/stefanosbalaskas/GazeForge/actions/workflows/docs.yml"><img alt="Documentation" src="https://github.com/stefanosbalaskas/GazeForge/actions/workflows/docs.yml/badge.svg"></a>
  <a href="https://pypi.org/project/gazeforge/0.1.0a1/"><img alt="PyPI" src="https://img.shields.io/badge/PyPI-0.1.0a1-blue"></a>
  <a href="https://www.python.org/"><img alt="Python" src="https://img.shields.io/badge/Python-3.10%20%7C%203.12%20%7C%203.14-blue"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-green.svg"></a>
  <a href="https://doi.org/10.5281/zenodo.22650012"><img alt="DOI" src="https://zenodo.org/badge/1355235505.svg"></a>
  <a href="CHANGELOG.md"><img alt="Status" src="https://img.shields.io/badge/status-alpha-orange"></a>
</p>

<p align="center">
  <a href="https://stefanosbalaskas.github.io/GazeForge/"><strong>Website</strong></a> ·
  <a href="docs/gazeforge-tour.md"><strong>Start here</strong></a> ·
  <a href="docs/documentation-map.md"><strong>Task map</strong></a> ·
  <a href="docs/method-chooser.md"><strong>Method chooser</strong></a> ·
  <a href="docs/runnable-examples.md"><strong>Examples</strong></a> ·
  <a href="docs/learning-paths.md"><strong>Learning paths</strong></a> ·
  <a href="docs/evidence-status.md"><strong>Evidence status</strong></a> ·
  <a href="docs/api-reference.md"><strong>API</strong></a>
</p>

---

## New to GazeForge? Start with the tour

If you are asking **“What does GazeForge actually do?”**, do not start with the API reference.

Read the **[GazeForge Tour](docs/gazeforge-tour.md)** and run the smallest package-wide example:

```bash
python examples/00_gazeforge_tour.py --output-dir gazeforge-tour-demo
```

The tour shows one gaze table moving through:

```text
source gaze
   ↓
canonical gaze
   ↓
non-destructive QC
   ↓
transparent eye events
   ↓
researcher-defined AOIs
   ↓
semantic scanpaths
   ↓
provenance + reviewable output bundle
```

It creates ordinary CSV/JSON files you can inspect side-by-side. It also verifies that the source table is unchanged and that sample rows are preserved through non-destructive sample-level stages.

> **Tour boundary:** the tour uses deterministic synthetic/demo data. It is not empirical validation evidence, a tracker-validity result, or a claim that QC flags should automatically become exclusions.

## What GazeForge is

GazeForge is a vendor-neutral Python research-software package for integrating **auditable AI and reproducible workflows into eye-tracking analysis**.

It is not one detector or one classifier. It connects the analysis stages that researchers normally have to manage separately while keeping transformations, uncertainty, model identity, sampling assumptions, human review, and provenance visible.

> **Scientific contract:** AI may propose, score, classify, embed, or flag. It must not silently alter the empirical record.

GazeForge does **not** infer diagnoses, emotions, personality, protected traits, or unsupported latent mental states from gaze.

## Choose the path you need

| Your task | Start here |
| --- | --- |
| I do not yet understand the package | **[GazeForge Tour](docs/gazeforge-tour.md)** |
| I have a tracker export | [Worked tracker import + QC](docs/worked-tracker-import.md) |
| QC found problems and I need defensible exclusions | [QC review + exclusion ledger](docs/qc-review-exclusion-ledger.md) |
| I need an inspectable eye-event baseline | [I-VT tutorial](docs/tutorial-ivt-baseline.md) |
| I want to train or compare learned event models | [Event-model validation clinic](docs/event-model-validation-clinic.md) |
| I need static or moving AOIs | [Research recipes](docs/research-recipes.md) / [Dynamic AOI study](docs/worked-dynamic-aoi-study.md) |
| I know the task but need to choose the method | [Method chooser](docs/method-chooser.md) |
| I need to understand a CSV/JSON output | [Artifact & output dictionary](docs/artifact-dictionary.md) |
| I have reviewed gaze outputs and need model-ready statistical tables | [Analysis handoff](docs/analysis-handoff.md) |
| I have a gaze metric and need to know what it supports saying | [Measurement & interpretation clinic](docs/measurement-interpretation.md) |
| I need a study from acquisition to publication | [Study lifecycle](docs/study-lifecycle.md) |
| I need a reviewable manuscript/archive bundle | [Research evidence bundle](docs/research-evidence-bundle.md) |
| I need claim-safe Methods/Results/archive wording | [Reporting & interpretation clinic](docs/reporting-clinic.md) |
| I need to hand the frozen study to a reviewer/replicator | [Reviewer & replication handoff](docs/reviewer-replication-handoff.md) |
| I am preparing a manuscript | [Publication readiness](docs/publication-readiness.md) |
| I need to know what is empirically supported | [Evidence status](docs/evidence-status.md) |

Browse all exact commands and output inventories in the **[Runnable examples gallery](docs/runnable-examples.md)**.

## What GazeForge adds to eye-tracking analysis

| Layer | What it provides | What it does not silently do |
| --- | --- | --- |
| **Import & canonicalisation** | vendor-neutral schema, Gazepoint adapters, rate/cadence diagnostics | guess unknown source semantics |
| **QC** | anomaly flags, missingness/bounds/gap diagnostics, trial quality | delete flagged observations |
| **Review & exclusions** | explicit sample/trial/participant decision ledgers and denominators | convert flags directly into exclusions |
| **Eye events** | transparent I-VT/angular I-VT, Random Forest, temporal-context models | imply one model is universally superior |
| **AOIs** | researcher-defined and AI-proposed static/dynamic AOIs, review history | treat proposals as ground truth |
| **Scanpaths** | semantic sequences, motifs, embeddings, similarity, clustering | infer unsupported mental states |
| **Validation** | participant-held-out/dataset-held-out workflows, calibration, event metrics | hide the split or native/derived distinction |
| **Auditability** | fingerprints, provenance, manifests, benchmark/evidence records | overwrite the empirical record |

## Installation and immutable release identity

Install the exact public alpha:

```bash
python -m pip install "gazeforge==0.1.0a1"
```

The immutable `0.1.0a1` release is published at [PyPI](https://pypi.org/project/gazeforge/0.1.0a1/) and archived on Zenodo with version DOI [`10.5281/zenodo.22650013`](https://doi.org/10.5281/zenodo.22650013). The Zenodo concept/latest-release DOI is [`10.5281/zenodo.22650012`](https://doi.org/10.5281/zenodo.22650012).

The exact GitHub Release distributions are identity-matched to the published alpha:

```text
gazeforge-0.1.0a1-py3-none-any.whl  sha256:3e409fbfc3c194db30ba25fefdf7f6459a3a003aefa0ab4303555d96982fbb46
gazeforge-0.1.0a1.tar.gz            sha256:cee4e061a90d74b3a354a0fb4aa5c7bd00d53577e17167f75342cd476a5c25fa
```

Optional open-vocabulary semantic AOI detection:

```bash
python -m pip install "gazeforge[vision]==0.1.0a1"
```

For development or commit-pinned research work:

```bash
git clone https://github.com/stefanosbalaskas/GazeForge.git
cd GazeForge
python -m pip install -e ".[dev]"
pytest
```

[Release & install guidance →](docs/release-install.md)

## Minimal Python workflow

```python
from gazeforge import ai_flag_anomalies, canonicalize_gaze, simulate_gaze

raw = simulate_gaze(n_participants=3, n_trials=2, samples_per_trial=180)
gaze = canonicalize_gaze(raw, sampling_rate_hz=60)
flagged = ai_flag_anomalies(gaze.data, sampling_rate_hz=gaze.sampling_rate_hz)
```

The input rows remain present. QC adds review evidence rather than deleting observations.

For a more informative first run, use `examples/00_gazeforge_tour.py` instead of stopping at this snippet.

## Example progression

The repository now has a task-oriented learning sequence:

```text
00  package-wide GazeForge tour
01  synthetic non-destructive QC
02  transparent I-VT baseline
03  visual diagnostics
04  worked static advertising/interface study
05  worked dynamic-AOI study
06  participant-held-out event-model validation
07  tracker import + QC
08  QC review + exclusion ledger
09  archive-facing research evidence bundle
10  statistical analysis handoff + diagnostic figures
11  manuscript/reporting derivatives + claim boundaries
12  measurement/interpretation audit
13  reviewer/replication handoff
+   complete end-to-end research workflow
```

Every learning example uses deterministic synthetic/demo inputs and carries an explicit evidence boundary.

## Validation is visible, not implied

GazeForge separates software capability from empirical support. The canonical public status is generated from versioned evidence policy and integrity-checked artifacts.

| Benchmark | Reference | Native rate | Current role and boundary |
| --- | --- | ---: | --- |
| **Lund2013** | paired expert manual event labels | 500 Hz | **Frozen empirical evidence**: native/derived human agreement and derived-60-Hz modelling; derived results are not native GP3 validation |
| **Hollywood2EM** | sequential student labels with expert-corrected final labels | ≈500 Hz | **Frozen empirical evidence**: aggregate derived-60-Hz source-token-held-out evidence; source-token-disjoint, not participant-disjoint; identity/licence boundaries remain |
| **Gaze-in-the-Wild** | distributed trained human labellers | published 120 Hz acquisition; exact ProcessData nominal 300 Hz | **Reviewed empirical evidence**: exact-distribution participant-disjoint evidence on a derived 60-Hz task-agnostic grid; complete authoritative numeric task mapping and native-60-Hz/GP3 validity remain open |
| **VISUS** | one published curated dynamic-AOI annotation process involving two contributors | 60 Hz | **Bounded empirical evidence**: verified partial public-derivative Tobii 60 Hz observations; the full 25-participant × 11-stimulus benchmark is not recovered, original source licensing remains unresolved, and no full-dataset model-validation, human-human-agreement, Frozen Evidence, or native-GP3 claim is created |

GazeForge never silently upgrades derived or partial evidence into a stronger category. For VISUS specifically, the current public derivative supports bounded empirical observations only; it does not recover the original full benchmark or establish model validity, independent human-human agreement, Frozen Evidence, unrestricted source redistribution, or native GP3 validity.

[Evidence status →](docs/evidence-status.md) · [Frozen evidence →](docs/frozen-evidence.md) · [Validation matrix →](docs/validation-status.md)

## First frozen Lund2013 checkpoint

The first audited external benchmark tranche uses the public Lund2013 expert-labelled corpus with exact source verification and participant-held-out evaluation. The primary RA-labelled **derived 60 Hz** comparison is intentionally multi-criterion: learned models are stronger on sample-level multiclass classification in this checkpoint, while transparent I-VT is stronger on contiguous event segmentation/boundary fidelity.

Human MN–RA agreement remains strong from native 500 Hz to the derived 60 Hz condition. These results are **not native GP3/60 Hz device validation**; a genuinely native 60 Hz/GP3-class manually labelled event corpus remains an open evidence requirement.

[Inspect the complete frozen reports →](docs/frozen-evidence.md)

## Research workflow

```text
tracker / raw export
        │
        ▼
explicit source contract
        │
        ▼
canonical gaze table
        │
        ├── non-destructive QC ── review/exclusion ledger
        ├── eye-event labels/probabilities ── validation
        ├── static/dynamic AOIs ── human review
        └── semantic scanpaths
                         │
                         ▼
               reviewed analytic derivative
                         │
                         ▼
              statistics / models / report
                         │
                         ▼
          provenance + fingerprints + archive
```

For a manuscript-facing study, record acquisition hardware, nominal/native rate, observed timestamp cadence, source mapping/units, source fingerprints, QC and exclusion decisions, event/AOI model identity, split design, native/derived status, and the exact GazeForge version/commit. The [Research evidence bundle](docs/research-evidence-bundle.md) shows how to freeze those layers without collapsing source, QC, review decisions, and analysis derivatives into one table.

## Scientific governance

Confirmatory workflows should lock model/version information, sampling rates, exclusions, validation splits, and human review decisions before final inference. External benchmark files remain external unless their reuse terms clearly permit redistribution.

[Scientific governance →](docs/scientific-governance.md) · [Publication readiness →](docs/publication-readiness.md)

## Documentation

The strict-built MkDocs Material site is the primary long-form documentation surface:

**https://stefanosbalaskas.github.io/GazeForge/**

Recommended entry points:

- [GazeForge Tour](docs/gazeforge-tour.md)
- [Getting started](docs/getting-started.md)
- [Learning paths](docs/learning-paths.md)
- [Method chooser](docs/method-chooser.md)
- [Artifact & output dictionary](docs/artifact-dictionary.md)
- [Research evidence bundle](docs/research-evidence-bundle.md)
- [Analysis handoff](docs/analysis-handoff.md)
- [Measurement & interpretation clinic](docs/measurement-interpretation.md)
- [Reporting & interpretation clinic](docs/reporting-clinic.md)
- [Reviewer & replication handoff](docs/reviewer-replication-handoff.md)
- [Research recipes](docs/research-recipes.md)
- [Runnable examples](docs/runnable-examples.md)
- [Evidence status](docs/evidence-status.md)

## Project status

GazeForge is active public-alpha research software. The package has broad implemented workflow coverage and audited external evidence, while important scientific gates remain explicit rather than being hidden behind the software feature set.

Before a stable scientific release, key open requirements include native 60 Hz/GP3-class expert-labelled event validation, resolution of remaining benchmark identity/licensing boundaries, stronger full-source VISUS recovery/authorization, broader cross-dataset validation, validated dynamic-detection/tracking results, and final API stability beyond the alpha series.

The active benchmark plan is tracked in [Issue #1](https://github.com/stefanosbalaskas/GazeForge/issues/1).

## Citation

For work using the first public alpha:

> Balaskas, S. (2026). *GazeForge: Auditable AI for Eye-Tracking Analysis* (Version 0.1.0a1) [Computer software]. Zenodo. https://doi.org/10.5281/zenodo.22650013

Use the exact GazeForge version or full commit SHA in reproducible methods. Machine-readable citation metadata is available in [`CITATION.cff`](CITATION.cff).

## License

MIT License. External validation datasets retain their own licenses and are not silently redistributed by GazeForge.
