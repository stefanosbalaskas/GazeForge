---
tags:
  - Examples
  - Workflow
  - Tutorials
---

# Examples gallery

GazeForge includes **22 runnable Python research scripts**. Choose by scientific task rather than filename.

## Start and quality control

| Example | Purpose | Guide |
| --- | --- | --- |
| `00_gazeforge_tour.py` | Full deterministic tour | [GazeForge tour](gazeforge-tour.md) |
| `01_synthetic_qc.py` | Synthetic QC evidence | [Synthetic QC tutorial](tutorial-synthetic-qc.md) |
| `02_ivt_baseline.py` | Transparent I-VT baseline | [I-VT tutorial](tutorial-ivt-baseline.md) |
| `03_visual_diagnostics.py` | QC/event/AOI visual diagnostics | [Visual diagnostics](visual-diagnostics.md) |
| `07_worked_tracker_import_qc.py` | Real tracker import contract + QC | [Worked tracker import](worked-tracker-import.md) |
| `08_worked_qc_review_ledger.py` | Review and exclusion ledger | [QC review ledger](qc-review-exclusion-ledger.md) |

## Study workflows

| Example | Purpose | Guide |
| --- | --- | --- |
| `04_worked_advertising_study.py` | Experimental/interface workflow | [Worked advertising study](worked-advertising-study.md) |
| `05_worked_dynamic_aoi_study.py` | Dynamic AOI study | [Worked dynamic-AOI study](worked-dynamic-aoi-study.md) |
| `06_worked_event_model_validation.py` | Event-model validation | [Validation clinic](event-model-validation-clinic.md) |
| `end_to_end_research_workflow.py` | Source → analysis → evidence | [Practical workflow](practical-workflow.md) |

## Analysis and reporting handoff

| Example | Purpose | Guide |
| --- | --- | --- |
| `09_worked_research_evidence_bundle.py` | Reproducible evidence bundle | [Evidence bundle](research-evidence-bundle.md) |
| `10_worked_analysis_handoff.py` | Statistical handoff tables | [Analysis handoff](analysis-handoff.md) |
| `11_worked_manuscript_reporting_bundle.py` | Manuscript-ready evidence language | [Reporting clinic](reporting-clinic.md) |
| `12_worked_measurement_interpretation_audit.py` | Observable → construct audit | [Measurement clinic](measurement-interpretation.md) |
| `13_worked_estimand_preregistration.py` | Outcome/estimand registry | [Estimand preregistration](estimand-preregistration.md) |
| `14_worked_reviewer_replication_bundle.py` | Reviewer/replicator handoff | [Replication handoff](reviewer-replication-handoff.md) |
| `15_worked_sensitivity_robustness_audit.py` | Sensitivity registry | [Sensitivity clinic](sensitivity-robustness-clinic.md) |
| `16_worked_denominator_exposure_audit.py` | Exposure and censoring | [Denominator clinic](denominator-exposure-censoring.md) |
| `17_worked_model_diagnostics_audit.py` | Convergence/diagnostic gate | [Model diagnostics](model-diagnostics-convergence.md) |
| `18_worked_missing_data_assumptions_audit.py` | Missing-data handoff | [Missing-data guide](missing-data-assumptions.md) |
| `19_worked_inferential_reporting_audit.py` | Multiplicity/inference audit | [Inference reporting](inferential-reporting-audit.md) |
| `20_worked_grouping_pseudoreplication_audit.py` | Repeated-measures audit | [Grouping guide](grouping-repeated-measures.md) |

## Run one

```powershell
python examples/00_gazeforge_tour.py
```

Each example is a **teaching and reproducibility surface**. Synthetic examples do not establish external validity, and a successful run does not upgrade the evidence class of a method.
