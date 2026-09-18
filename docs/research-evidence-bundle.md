---
description: Archive-facing guide for assembling source, QC, review, analysis, provenance, and reporting artifacts into one reviewable GazeForge research evidence bundle.
search:
  boost: 1.5
---

# Research evidence bundle

<div class="gf-doc-kind" role="note" aria-label="Documentation type">
<strong>Worked archive guide</strong> · Build one reviewable directory that separates source records, QC evidence, human decisions, analysis derivatives, and reporting metadata.
</div>

<nav class="gf-help" aria-label="Documentation help">
<a href="gazeforge-tour.md">Tour</a>
<a href="documentation-map.md">Task map</a>
<a href="troubleshooting.md">Troubleshooting</a>
<a href="runnable-examples.md">Examples</a>
<a href="https://github.com/stefanosbalaskas/GazeForge/issues">Ask / report</a>
</nav>


<nav class="gf-study-path" aria-label="Research workflow path">
<a href="documentation-map.md"><strong>1</strong><span>Task</span></a>
<a href="method-chooser.md"><strong>2</strong><span>Method</span></a>
<a href="artifact-dictionary.md"><strong>3</strong><span>Artifacts</span></a>
<a href="research-evidence-bundle.md" aria-current="step"><strong>4</strong><span>Evidence bundle</span></a>
<a href="reporting-interpretation-clinic.md"><strong>5</strong><span>Report</span></a>
<a href="publication-readiness.md"><strong>6</strong><span>Submit</span></a>
</nav>

A reproducible analysis is easier to review when the archive itself shows **which files are inputs, which are quality evidence, which encode researcher decisions, which are analysis derivatives, and which exist only to document/report the workflow**.

This guide accompanies `examples/09_worked_research_evidence_bundle.py`. It deliberately composes existing public APIs instead of inventing a second scientific pipeline.

!!! warning "Archive completeness is not scientific validation"
    A complete, deterministic bundle can demonstrate software reproducibility and decision traceability. It does **not** establish tracker validity, native-device validity, native-60-Hz validity, Gazepoint/GP3 validity, event-model validity, AOI construct validity, calibration validity, measurement validity, or a substantive psychological effect.

## Run the example

```bash
python examples/09_worked_research_evidence_bundle.py \
  --output-dir worked-research-evidence-bundle
```

The demo uses a deterministic tracker-shaped synthetic source and writes:

```text
worked-research-evidence-bundle/
├── README.md
├── source_contract.json
├── 01_source_tracker_export.csv
├── 02_canonical_gaze.csv
├── 03_pre_review_qc_samples.csv
├── 04_decision_criteria.csv
├── 05_trial_quality.csv
├── 06_trial_review_ledger.csv
├── 07_primary_analysis_rows.csv
├── 08_event_samples.csv
├── 09_event_intervals.csv
├── 10_fixation_centroids.csv
├── 11_aoi_definitions.csv
├── 12_fixation_aoi_assignments.csv
├── 13_semantic_scanpaths.csv
├── artifact_index.csv
├── analysis_plan.json
├── provenance.json
└── workflow_manifest.json
```

## The five archive layers

| Layer | Typical files | What it answers | What it must not be promoted into |
| --- | --- | --- | --- |
| **1 · Source** | `source_contract.json`, `01_source_tracker_export.csv` | What was supplied? What do columns/units mean? | proof of device validity |
| **2 · QC** | `02_canonical_gaze.csv`, `03_pre_review_qc_samples.csv`, `05_trial_quality.csv` | What quality evidence was observed before decisions? | automatic invalidity/exclusion labels |
| **3 · Review** | `04_decision_criteria.csv`, `06_trial_review_ledger.csv` | Which rule triggered and what decision was recorded? | proof that the rule is universally valid |
| **4 · Analysis** | `07_primary_analysis_rows.csv` through `13_semantic_scanpaths.csv` | What exact derivative fed the downstream analysis? | unsupported causal/psychological inference |
| **5 · Provenance/reporting** | `artifact_index.csv`, `analysis_plan.json`, `provenance.json`, `workflow_manifest.json`, `README.md` | Can another researcher identify, inspect, and reconstruct the workflow? | external empirical validation |

## Why the primary-analysis table is separate

The worked bundle never edits the pre-review QC table in place. Reviewed trial decisions create a new `07_primary_analysis_rows.csv`.

That separation makes three questions independently answerable:

1. **What did the QC system flag?**
2. **What did the reviewer decide?**
3. **What rows actually entered downstream analysis?**

**QC flags are not automatic exclusions.** A `qc_flag=True` sample can still be retained. Conversely, a reviewed trial can be excluded because a prespecified criterion was met even when not every sample in that trial is individually anomalous.

## Use the artifact index as the archive table of contents

`artifact_index.csv` records, for every major file:

- layer;
- unit of observation;
- whether the file should be treated as immutable/frozen;
- purpose;
- archive recommendation; and
- the evidence boundary that must travel with the file.

This is especially useful when a manuscript archive contains files from different stages that would otherwise look equally authoritative.

## Minimum source contract

For real data, replace the synthetic source contract with study-specific facts:

```yaml
tracker_model: <model>
source_file_identity: <name/checksum or controlled archive id>
participant_field: <field>
trial_or_stimulus_field: <field>
timestamp_field: <field>
timestamp_unit: ms | s | other
coordinate_fields: <x/y>
coordinate_basis: pixels | normalized | degrees | other
screen_or_stimulus_geometry: <width × height + unit>
native_or_nominal_rate_hz: <documented acquisition setting>
observed_timestamp_cadence_hz: <diagnostic from analysed stream>
analysis_rate_status: native | derived | mixed
```

**Observed timestamp cadence is not proof of the native hardware sampling rate.** Keep the two concepts separate in methods and archives.

## Minimum review record

A review/exclusion ledger should make these fields recoverable:

- unit reviewed: sample, trial, participant, stimulus, or another explicit unit;
- criterion/rule identifier;
- criterion status: prespecified, protocol amendment, exploratory, or sensitivity-only;
- reviewer and review timestamp where appropriate;
- decision;
- denominator before the decision;
- rationale; and
- link to the QC evidence that triggered review.

Do not overwrite a QC score with a binary “valid/invalid” field and lose the original evidence.

## What belongs in a manuscript archive?

Usually retain, subject to privacy/licensing restrictions:

- exact source identity or a non-sensitive checksum/manifest;
- the import/source contract;
- pre-review QC summaries and the reviewed decision ledger;
- the exact primary-analysis derivative or a reproducible recipe for rebuilding it;
- event/AOI/scanpath specifications used in the reported analysis;
- analysis plan / preregistration linkage;
- software version and full commit SHA for unreleased development code;
- provenance/fingerprints/manifests;
- final tables/figures and code that generated them; and
- one explicit evidence-boundary statement.

Do **not** redistribute participant data, restricted benchmark sources, unpublished stimuli, or licensed assets merely because the software can package them.

## Manuscript-facing reporting pattern

A methods section should make the archive logic visible in prose:

> Source files were preserved separately from canonical and QC-enriched derivatives. Automated QC flags were treated as review evidence rather than automatic exclusions. Reviewed trial decisions were recorded in a dedicated ledger and applied to a separate primary-analysis derivative. Event, AOI, and scanpath outputs were generated only after that reviewed analysis table was frozen. Software version, analysis parameters, provenance, and file fingerprints were retained in the archive.

Adapt that wording to the actual study; do not copy the demonstration thresholds or imply they are validated defaults.

## Connect this bundle to the rest of GazeForge

- [Method chooser](method-chooser.md) — choose a workflow that matches the scientific question and held-out/generalisation unit.
- [Artifact & output dictionary](artifact-dictionary.md) — understand common CSV/JSON outputs in more detail.
- [First study blueprint](first-study-blueprint.md) — plan from research question through acquisition and publication.
- [QC review & exclusion ledger](qc-review-exclusion-ledger.md) — separate automated QC from decisions.
- [Publication readiness](publication-readiness.md) — audit what must be reported before submission.
- [Reproducible reporting](reproducible-reporting.md) — translate the frozen workflow into methods and archive documentation.

## Evidence boundary

The worked evidence bundle is `synthetic_demo_not_empirical_evidence`. It is **not empirical validation evidence**. It is intentionally useful for learning archive structure while being scientifically weak as evidence. A clean archive can show **what happened in the software**; empirical validity still requires evidence appropriate to the tracker, task, labels, sampling condition, population, and scientific claim.
