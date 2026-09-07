# GazeForge 0.1.0a1

This is the first public alpha release of **GazeForge**, a vendor-neutral Python research-software package for auditable AI-assisted eye-tracking analysis.

## Included in this alpha

- canonical gaze schema, sampling-rate inference, Gazepoint adapters, and synthetic-data workflows;
- auditable anomaly/QC scoring and calibration-drift diagnostics;
- transparent I-VT and angular I-VT baselines plus Random Forest and temporal-context MLP event models;
- probabilistic output, calibration, abstention, participant-held-out validation, matched-fold comparison, and event-level temporal metrics;
- semantic and dynamic AOIs with explicit human review/correction and bounded interpolation;
- semantic scanpaths, motifs, embeddings, similarity, and clustering;
- reproducible Lund2013 acquisition and the first reviewed external empirical evidence suite;
- frozen-evidence validation, source-resolution infrastructure, and provenance/rights guardrails for additional external benchmarks;
- CI across supported Python versions and major desktop operating systems, strict documentation builds, and GitHub Pages documentation.

## Evidence boundary

The first frozen external empirical tranche is based on the public Lund2013 expert-labelled corpus. Learned models lead sample-level multiclass performance at the primary derived-60-Hz condition, while I-VT remains stronger for contiguous event segmentation and boundary fidelity. The derived 60 Hz analyses are **not native GP3/60 Hz device validation**.

The current Gaze-in-the-Wild provenance/rights tranche establishes official Figshare deposit identities, public manifests, and the deposits' stated CC BY 4.0 licences. It does **not** establish exact-byte acquisition, complete participant/task mapping, frozen multi-labeller human agreement, participant-disjoint model validation, GP3 validity, quarantine exit, or source-audit readiness.

## Release status

`0.1.0a1` is intentionally an **alpha** release. APIs may change while the validation program is completed. A stable scientific release remains gated on native 60 Hz/GP3-class expert-labelled validation, broader externally audited benchmark evidence, validated dynamic detection/tracking results, and final API stability.

## Reproducibility

The GitHub Release contains the wheel, source distribution, and `SHA256SUMS.txt`. PyPI publication is performed from those exact GitHub Release distributions through GitHub OIDC Trusted Publishing so release files can be identity-checked across GitHub and PyPI.
