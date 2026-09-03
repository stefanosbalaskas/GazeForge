# Empirical benchmark execution

GazeForge separates **benchmark infrastructure** from **empirical evidence**. The repository can contain adapters, validation code, metrics, and protocols without implying that scientific performance has already been established.

The Lund2013 evidence workflow provides a reproducible route from the pinned external corpus to reviewable frozen JSON without redistributing the raw benchmark.

## Lund2013 evidence pipeline

The GitHub Actions workflow `.github/workflows/lund-empirical-evidence.yml` executes the existing GazeForge command-line interfaces rather than duplicating benchmark logic in workflow code:

```text
pinned Lund2013 source
        │
        ▼
gazeforge lund2013-fetch
        │
        ├── Git blob SHA verification
        ├── byte-size verification
        └── local source manifest
        │
        ▼
gazeforge lund2013-suite
        │
        ├── native MN-vs-RA human agreement
        ├── derived 60 Hz MN-vs-RA agreement
        ├── RA-labelled 60 Hz model comparison
        ├── MN-labelled 60 Hz annotator sensitivity
        └── RA sampling-rate × label-purity sensitivity
        │
        ▼
gazeforge lund2013-suite-validate
        │
        ├── suite fingerprint verification
        └── all five child-report fingerprints verified
        │
        ▼
evidence/lund2013-auto branch
```

The default model comparison remains I-VT versus Random Forest versus ContextMLP under participant-held-out folds. The primary derived analysis rate is 60 Hz, angular I-VT remains fixed at 45 deg/s, and the sensitivity surface evaluates 120, 90, 60, and 30 Hz at label-purity thresholds 0.60, 0.75, and 0.90.

## Raw data are not published by GazeForge

The external MATLAB files are fetched into the runner's temporary directory. They are not written under the repository tree and are not included in the evidence branch or workflow artifact.

Before publication, the workflow explicitly rejects non-JSON files under `validation/evidence/lund2013` and checks that no MATLAB file appears in the evidence tree.

The evidence output contains only:

- five fingerprinted benchmark JSON reports;
- the deterministic Lund suite manifest;
- one execution-metadata JSON file recording the GazeForge commit and workflow-run identity.

External benchmark licensing remains with the source project.

## Review before publication

A successful workflow run pushes the evidence to the dedicated branch:

```text
evidence/lund2013-auto
```

It does **not** merge empirical numbers directly into `main`. The evidence branch is reviewed through an ordinary pull request. This provides an explicit checkpoint for scientific inspection of human agreement, model results, stimulus-family heterogeneity, sampling/purity sensitivity, exclusions, and provenance before the results become part of the public website.

## Website publication

The [Frozen empirical evidence](frozen-evidence.md) page is generated from the committed JSON rather than manually transcribed performance values. Only reports whose deterministic fingerprints revalidate successfully appear as empirical evidence.

GitHub Pages is configured to rebuild when `validation/**` changes. Therefore, after an evidence pull request is reviewed and merged, the public evidence tables are regenerated from the merged reports automatically.

## Interpretation boundary

A successful automated run establishes reproducible evidence for the declared Lund2013 protocol. It does not by itself establish:

- native 60 Hz or GP3-specific fixation/saccade validity;
- superiority across trackers, tasks, or populations;
- equivalence between derived lower-rate labels and labels collected natively at that rate.

Those claims require additional independently appropriate validation datasets.
