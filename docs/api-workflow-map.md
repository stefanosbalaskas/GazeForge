---
description: Map GazeForge public APIs to the runnable research workflows that use them.
tags:
  - API
  - Examples
  - Workflow
  - Guide
---

# API → workflow map

Use this page when you know **what you want to do** but not which public API or runnable example shows the complete research contract.

The map below is grounded in the repository's runnable examples. It is not a ranking of methods and it does not turn software availability into scientific justification.

| Research task | Public API used in runnable examples | Example routes | Important boundary |
| --- | --- | --- | --- |
| Canonicalise synthetic or documented gaze | `simulate_gaze()`, `canonicalize_gaze()` | `00_gazeforge_tour.py`, `01_synthetic_qc.py`, `02_ivt_baseline.py` | Canonicalisation is a documented transformation, not device validation. |
| Add review-first QC evidence | `ai_flag_anomalies()`, `score_trial_quality()` | `00_gazeforge_tour.py`, `01_synthetic_qc.py`, `07_worked_tracker_import_qc.py`, `08_worked_qc_review_ledger.py` | A QC flag is evidence for review, not an automatic exclusion. |
| Import Gazepoint-shaped exports | `adapt_gazepoint_samples()`, `infer_sampling_rate_hz()` | `07_worked_tracker_import_qc.py`, `09_worked_research_evidence_bundle.py` | Import compatibility does not establish tracker or native-rate validity. |
| Build a transparent event baseline | `ivt_classify_events()`, `samples_to_event_intervals()` | `00_gazeforge_tour.py`, `02_ivt_baseline.py`, `09_worked_research_evidence_bundle.py` | A threshold is an explicit model specification, not a universal biological boundary. |
| Work with static semantic AOIs | `AOI`, `aois_to_frame()`, `map_fixations_to_aois()` | `00_gazeforge_tour.py`, `09_worked_research_evidence_bundle.py`, `10_worked_analysis_handoff.py` | AOI definitions must remain tied to stimulus geometry and study meaning. |
| Build semantic scanpaths | `to_semantic_scanpaths()` | `00_gazeforge_tour.py`, `05_worked_dynamic_aoi_study.py`, `09_worked_research_evidence_bundle.py` | Scanpath structure is observable behaviour, not an automatic latent-state inference. |
| Work with dynamic AOIs | `DynamicAOIKeyframe`, `interpolate_dynamic_aoi()`, `dynamic_aois_to_frame()`, `map_fixations_to_dynamic_aois()` | `05_worked_dynamic_aoi_study.py` | Interpolation is bounded by reviewed temporal support; no silent extrapolation. |
| Compare learned event models on held-out participants | `compare_event_models_grouped()`, `evaluate_event_calibration()`, `selective_accuracy_curve()` | `06_worked_event_model_validation.py` | The held-out grouping unit is part of the claim. Synthetic examples are not empirical validation. |
| Preserve provenance and deterministic identity | `AuditTrail`, `fingerprint_frame()`, `__version__` | tour, dynamic-AOI, validation, tracker-import, QC-review, evidence-bundle examples | Fingerprints establish identity/provenance, not scientific validity. |
| Prepare model-ready statistical inputs | AOI/fixation mapping plus explicit denominator, exposure, missingness and censoring fields | `10_worked_analysis_handoff.py` | The handoff does not choose the inferential estimator or erase repeated-measures structure. |

## Start from the runnable example

The source files are the most concrete API examples:

- [00 · GazeForge tour](https://github.com/stefanosbalaskas/GazeForge/blob/main/examples/00_gazeforge_tour.py)
- [01 · Synthetic QC](https://github.com/stefanosbalaskas/GazeForge/blob/main/examples/01_synthetic_qc.py)
- [02 · I-VT baseline](https://github.com/stefanosbalaskas/GazeForge/blob/main/examples/02_ivt_baseline.py)
- [05 · Dynamic-AOI study](https://github.com/stefanosbalaskas/GazeForge/blob/main/examples/05_worked_dynamic_aoi_study.py)
- [06 · Event-model validation](https://github.com/stefanosbalaskas/GazeForge/blob/main/examples/06_worked_event_model_validation.py)
- [07 · Tracker import + QC](https://github.com/stefanosbalaskas/GazeForge/blob/main/examples/07_worked_tracker_import_qc.py)
- [08 · QC review ledger](https://github.com/stefanosbalaskas/GazeForge/blob/main/examples/08_worked_qc_review_ledger.py)
- [09 · Research evidence bundle](https://github.com/stefanosbalaskas/GazeForge/blob/main/examples/09_worked_research_evidence_bundle.py)
- [10 · Statistical analysis handoff](https://github.com/stefanosbalaskas/GazeForge/blob/main/examples/10_worked_analysis_handoff.py)

For the complete inventory, use the [Examples gallery](examples-gallery.md). For signatures and parameter-level reference, use the [API reference](api-reference.md).

## Choose the scientific route before the function

A public function being available only tells you that GazeForge implements that operation. Before using it in a study, also establish:

1. the source measurement contract;
2. the observation/inferential/generalisation units;
3. the review or exclusion policy;
4. the native/derived sampling status;
5. the validation split needed for the intended claim; and
6. the evidence class that can actually be reported.

Use the [Method chooser](method-chooser.md) and [Scientific governance](scientific-governance.md) when that decision is not already fixed.
