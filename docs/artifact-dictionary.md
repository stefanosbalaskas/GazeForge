---
description: Dictionary of the major CSV, JSON, manifest, provenance, validation, and archive artifacts produced by GazeForge worked workflows.
search:
  boost: 1.5
---

# Artifact & output dictionary

<div class="gf-doc-kind" role="note" aria-label="Documentation type">
<strong>Reference guide</strong> · Understand what each major GazeForge output contains, which unit each row represents, and what the artifact can and cannot support.
</div>

<nav class="gf-help" aria-label="Documentation help">
<a href="gazeforge-tour.md">Tour</a>
<a href="documentation-map.md">Task map</a>
<a href="troubleshooting.md">Troubleshooting</a>
<a href="runnable-examples.md">Examples</a>
<a href="https://github.com/stefanosbalaskas/GazeForge/issues">Ask / report</a>
</nav>

A GazeForge workflow deliberately produces multiple artifacts instead of collapsing source data, automated diagnostics, human review, analysis derivatives, and reporting metadata into one table.

The filename number in a worked example indicates workflow order only. **Scientific meaning comes from the artifact role and unit of observation.**

For the archive-facing composition of these artifacts, use the [Research evidence bundle](research-evidence-bundle.md). It shows the reading order, source/QC/review/analysis separation, and the minimum reporting metadata that should travel with a manuscript-facing bundle.

## Artifact classes

| Class | Meaning | Typical handling |
| --- | --- | --- |
| **Source** | closest retained representation of the input/export | immutable; fingerprint/checksum |
| **Canonical** | explicit vendor-neutral transformation | derived but traceable to source |
| **QC evidence** | non-destructive diagnostics/flags | preserve before review |
| **Review evidence** | criteria and human/researcher decisions | append/freeze; never rewrite source |
| **Analysis derivative** | rows retained/derived for a declared analysis | regenerate from frozen upstream evidence |
| **Validation evidence** | held-out predictions/metrics/calibration | preserve split/generalisation identity |
| **Provenance/reporting** | versions, settings, manifests, fingerprints | archive with manuscript/release bundle |

## Source and import

| Artifact | Row/unit | Role | Keep immutable? | Answers | Does not establish |
| --- | --- | --- | --- | --- | --- |
| `01_source_tracker_export.csv` | source sample row | Source | **Yes** | What was supplied to the import workflow? | correct units, device validity, event validity |
| `01_source_gaze.csv` | synthetic/demo source sample | Source/demo | **Yes** within bundle | What did the example start from? | empirical evidence |
| `02_canonical_gaze.csv` | canonical gaze sample | Canonical | regenerate, do not hand-edit | What are participant/trial/time/x/y values under the declared mapping? | source semantics if the mapping itself was guessed |
| `03_import_preflight.csv` | one diagnostic per row | QC/import evidence | preserve with import | Were row counts, duplicate keys, missing identity, bounds, and cadence reviewed? | that the tracker is valid |
| `import_contract.json` or `source_contract.json` | one import/source contract | Provenance | **Yes** after freeze | Which source columns/units/geometry/conversions were declared? | that declared metadata are scientifically correct without source evidence |

## QC and review

| Artifact | Row/unit | Role | Keep immutable? | Answers | Does not establish |
| --- | --- | --- | --- | --- | --- |
| `04_qc_samples.csv`, `02_pre_review_qc_samples.csv`, or `03_pre_review_qc_samples.csv` | gaze sample | QC evidence | **Yes before decisions** | Which samples were flagged/scored? | automatic invalidity |
| `05_trial_quality.csv` or `03_trial_quality.csv` | participant × trial | QC summary | preserve | What missing/off-screen/anomaly/gap burden was observed? | universal exclusion threshold |
| `04_decision_criteria.csv` | criterion | Review policy | **Yes after freeze** | Which rule, scope, status, threshold, and purpose were declared? | that the criterion is externally validated |
| `05_sample_review_ledger.csv` | reviewed sample decision | Review evidence | append/freeze | Was a flagged sample retained or excluded, by whom/why? | participant-level exclusion |
| `06_trial_review_ledger.csv` | participant × trial decision | Review evidence | append/freeze | Which trials were retained/excluded and why? | validity of the underlying threshold |
| `07_participant_review_ledger.csv` | participant | Review evidence | append/freeze | Which participants remain in the analysis denominator? | independence of repeated observations |
| `08_exclusion_flow.csv` | workflow stage | Denominator evidence | preserve | How did denominators change from QC to primary analysis? | causal or measurement validity |
| `10_primary_analysis_rows.csv` or `07_primary_analysis_rows.csv` | retained gaze sample | Analysis derivative | regenerate from ledger | Which sample rows enter the declared primary analysis? | that downstream statistics are appropriate |

## Event outputs

| Artifact | Row/unit | Role | Answers | Boundary |
| --- | --- | --- | --- | --- |
| `05_event_samples.csv` / `08_event_samples.csv` | gaze sample | Analysis derivative | Which event label/probability is attached to each sample? | label ≠ validated truth |
| `06_event_intervals.csv` / `09_event_intervals.csv` | contiguous event | Analysis derivative | What are event starts, ends, durations, and labels? | segmentation quality requires reference evidence |
| `07_fixation_centroids.csv` / `10_fixation_centroids.csv` | fixation event | Analysis derivative | Where/when are retained fixation centroids? | centroid ≠ psychological interpretation |

## AOIs and scanpaths

| Artifact | Row/unit | Role | Answers | Boundary |
| --- | --- | --- | --- | --- |
| `08_aoi_definitions.csv` / `11_aoi_definitions.csv` | AOI | Reviewed analysis definition | Which semantic region and geometry were frozen? | semantic label ≠ construct validity |
| `09_fixation_aoi_assignments.csv` / `12_fixation_aoi_assignments.csv` | fixation × assignment | Analysis derivative | Which reviewed AOI contains each fixation? | membership ≠ attention meaning beyond the declared observable |
| `10_semantic_scanpaths.csv` / `13_semantic_scanpaths.csv` | participant × trial sequence | Analysis derivative | What AOI sequence was observed? | sequence ≠ latent cognitive/emotional state |
| `05_interpolation_audit.csv` | dynamic-AOI time/support record | Review/derivation evidence | Was interpolation bounded and support explicit? | interpolated geometry ≠ ground truth outside reviewed support |

## Statistical analysis handoff

The worked [Analysis handoff](analysis-handoff.md) adds a deliberately separate layer between reviewed measurement outputs and specialist inferential software.

| Artifact | Row/unit | Role | Answers | Boundary |
| --- | --- | --- | --- | --- |
| `03_trial_design_and_coverage.csv` | participant × trial | Design / denominator registry | Which repeated unit, condition, expected duration, observed exposure, and coverage status apply? | coverage is not an outcome effect |
| `04_trial_aoi_metrics.csv` | participant × trial × AOI | Model-ready analysis handoff | What fixation count, dwell, proportion, latency, denominator, and missingness/censoring status are available? | `NA` must not be silently converted to zero |
| `05_trial_event_metrics.csv` | participant × trial × event type | Model-ready analysis handoff | What event counts/durations/rates are available with observed exposure? | fixations/events are not independent participants |
| `06_descriptive_participant_condition_summary.csv` | participant × condition × AOI | Descriptive-only summary | What compact means are useful for inspection/plots? | not automatically the inferential model input |
| `07_model_handoff_dictionary.csv` | column | Handoff dictionary | What does each identity, denominator, outcome, censoring, and governance field mean? | dictionary ≠ statistical model specification |
| `analysis_handoff_plan.json` | bundle | Statistical handoff contract | What inferential unit, repeated grouping, zero policy, censoring policy, and model-selection boundary were declared? | GazeForge does not choose the inferential estimator |

## Validation and calibration

| Artifact | Row/unit | Role | Answers | Boundary |
| --- | --- | --- | --- | --- |
| `02_participant_split_ledger.csv` | participant/fold | Validation design | Which participants were train/test in each fold? | valid only if participant identity is authoritative |
| `03_matched_heldout_predictions.csv` | held-out sample × model | Validation evidence | What did each model predict on the same held-out row? | held-out row ≠ independent participant unless split says so |
| `04_sample_level_metrics.csv` | fold/model/metric | Validation summary | How did labels perform per sample? | does not measure temporal boundaries |
| `05_event_level_metrics.csv` | fold/model/event metric | Validation summary | How well were contiguous events/boundaries recovered? | not interchangeable with sample accuracy |
| `07_calibration_bins.csv` | model × probability bin | Calibration evidence | Does confidence align with observed accuracy by bin? | sparse bins can be unstable |
| `08_confidence_coverage.csv` | model × threshold | Decision diagnostic | What accuracy/coverage trade-off occurs at confidence thresholds? | threshold is not universal policy |
| `09_illustrative_abstention_policy.csv` | illustrative policy row | Demo/reporting | How can abstention be represented explicitly? | not a validated deployment cutoff |

## Provenance and archive metadata

| Artifact | Unit | Role | Archive? | Answers |
| --- | --- | --- | --- | --- |
| `analysis_plan.json` | workflow/study | Analysis contract | **Usually yes** | What was declared as primary, exploratory, review-only, or illustrative? |
| `provenance.json` | ordered operations | Provenance | **Yes** | Which operations, parameters, model identities, warnings, and fingerprints connected inputs to outputs? |
| `workflow_manifest.json` | bundle | Manifest | **Yes** | Which files, versions, fingerprints, denominators, and evidence boundaries define the bundle? |
| `artifact_index.csv` | artifact/file | Archive dictionary | **Yes** | What role, unit, mutability, and archive recommendation applies to each file? |
| `README.md` inside a bundle | bundle | Human-readable context | **Yes** | How should a reviewer/user navigate the evidence bundle? |

## What should usually go into a manuscript archive?

For a study using these layers, a reproducibility bundle commonly needs:

1. source identity/checksums or an access-controlled source manifest;
2. import contract and canonical transformation metadata;
3. pre-review QC evidence;
4. review criteria and exclusion ledgers;
5. denominator flow;
6. reviewed AOI/event/model definitions used by the analysis;
7. the analysis-ready derivative;
8. held-out validation evidence when model validity is part of the claim;
9. exact software identity and parameters;
10. provenance/fingerprints;
11. final tables/figures or scripts that regenerate them.

Do **not** publish private participant-level source data merely because the software can package it. Archive access and de-identification remain study-specific governance decisions.

## One complete example

Run:

```bash
python examples/09_worked_research_evidence_bundle.py \
  --output-dir worked-research-evidence-bundle-demo
```

Then open `artifact_index.csv`, `workflow_manifest.json`, and the generated `README.md` first. They explain how the bundle is organized and which files are source, QC, review, analysis, or reporting evidence. Continue with the [Research evidence bundle](research-evidence-bundle.md) for manuscript/archive guidance.

The bundle is deterministic synthetic/demo material and is **not empirical validation evidence**.
