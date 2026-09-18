---
description: Worked first-study blueprint showing how to move an eye-tracking research question through acquisition, GazeForge processing, review, analysis-ready artifacts, and manuscript/archive evidence.
search:
  boost: 1.5
---

# First study blueprint

<div class="gf-doc-kind" role="note" aria-label="Documentation type">
<strong>Worked how-to</strong> · Follow one realistic eye-tracking study from research question to reviewable analysis and reporting artifacts.
</div>

<nav class="gf-help" aria-label="Documentation help">
<a href="gazeforge-tour.md">Tour</a>
<a href="documentation-map.md">Task map</a>
<a href="troubleshooting.md">Troubleshooting</a>
<a href="runnable-examples.md">Examples</a>
<a href="https://github.com/stefanosbalaskas/GazeForge/issues">Ask / report</a>
</nav>

This blueprint answers a common question: **“I understand what GazeForge does, but how do I turn my own study into a defensible workflow?”**

The example is a static digital-ad/interface study with four researcher-defined regions: `brand`, `claim`, `disclosure`, and `product`. The scientific question is deliberately modest:

> How is visual attention distributed across the predeclared regions, and how do the observed fixation/AOI sequences differ across experimental conditions?

The example does **not** treat gaze as a direct measure of trust, persuasion, emotion, memory, preference, or diagnosis.

## The study in one view

<div class="gf-flow" aria-label="Worked first-study flow">
<div><strong>01</strong><span>Plan</span><small>Define constructs, conditions, AOIs, exclusions, and reporting rules before analysis.</small></div>
<div><strong>02</strong><span>Acquire</span><small>Record tracker, software, geometry, nominal rate, participant/trial IDs, and stimulus identity.</small></div>
<div><strong>03</strong><span>Import</span><small>Preserve source files and make time/coordinate transformations explicit.</small></div>
<div><strong>04</strong><span>Review QC</span><small>Keep anomaly evidence separate from retained/excluded decisions.</small></div>
<div><strong>05</strong><span>Derive</span><small>Create events, fixation centroids, AOI assignments, and semantic scanpaths.</small></div>
<div><strong>06</strong><span>Analyze</span><small>Build the table whose rows and denominators match the study question.</small></div>
<div><strong>07</strong><span>Report</span><small>Freeze provenance, figures, tables, versions, and scientific boundaries.</small></div>
</div>

## 1 · Write the analysis contract before touching the export

Record at least:

| Item | Example |
| --- | --- |
| Study unit | participant viewing one assigned advertisement/interface |
| Experimental condition | e.g. disclosure A vs disclosure B |
| Primary AOIs | `brand`, `claim`, `disclosure`, `product` |
| Main gaze outcomes | dwell time, fixation count, first-fixation latency, AOI transitions |
| Event source | predeclared transparent baseline or separately validated learned model |
| QC policy | review missing/off-screen/anomalous trials using prespecified criteria |
| Participant exclusion | only via explicit reviewed participant-level criterion |
| Primary denominator | retained participant × trial observations |
| Exploratory work | clearly labelled and never silently substituted for the primary analysis |

If an exclusion or AOI rule is invented only after seeing the final statistical result, label it exploratory rather than rewriting the analysis history.

## 2 · Preserve acquisition/source identity

Keep the original tracker export unchanged. Record:

- tracker model and acquisition software;
- nominal/native sampling rate;
- observed timestamp cadence separately;
- monitor/stimulus dimensions;
- participant identifier source;
- trial/stimulus identifier source;
- timestamp column and unit;
- coordinate columns and coordinate basis;
- stimulus filename/version; and
- acquisition anomalies known during data collection.

Use the [Worked tracker import + QC](worked-tracker-import.md) example when your export is Gazepoint-shaped, and the [Real-data import clinic](data-import-clinic.md) for other known source contracts.

## 3 · Import without hiding transformations

A defensible import should leave you with at least these retained artifacts:

```text
study/
├── source/
│   └── tracker_export.csv
├── import/
│   ├── canonical_gaze.csv
│   ├── import_preflight.csv
│   └── import_contract.json
└── provenance/
    └── import_provenance.json
```

The import contract should make seconds→milliseconds, normalized→pixel conversion, geometry, identity mapping, duplicate keys, missing gaze, and cadence explicit.

**Boundary:** a successful adapter run demonstrates transformation compatibility. It does not establish tracker validity, calibration validity, or native-rate event validity.

## 4 · Add QC, then review decisions separately

First produce non-destructive QC evidence:

```text
qc/
├── pre_review_qc_samples.csv
└── trial_quality.csv
```

Then create the review/exclusion layer:

```text
review/
├── decision_criteria.csv
├── sample_review_ledger.csv
├── trial_review_ledger.csv
├── participant_review_ledger.csv
├── exclusion_flow.csv
└── primary_analysis_rows.csv
```

Run the worked pattern:

```bash
python examples/08_worked_qc_review_ledger.py \
  --output-dir worked-qc-review-ledger-demo
```

A sample may be **flagged and retained**. A trial may be excluded for a reviewed prespecified reason. A participant should not disappear because a downstream script silently filtered all of their rows.

## 5 · Freeze AOIs before outcome interpretation

For the worked static study, define the intended semantic regions before inspecting condition effects:

| AOI | Research role | Example geometry source |
| --- | --- | --- |
| `brand` | brand identifier | researcher-reviewed rectangle/polygon |
| `claim` | focal textual claim | researcher-reviewed region |
| `disclosure` | disclosure/source information | researcher-reviewed region |
| `product` | product visual | researcher-reviewed region |

If AI proposes AOIs, retain model identity, confidence, proposal geometry, and the human accept/reject/relabel/edit decision. The reviewed AOI set—not the raw proposal—is the analysis input.

For a moving stimulus, switch to the [Worked dynamic-AOI study](worked-dynamic-aoi-study.md) and preserve the **no extrapolation** boundary outside reviewed temporal support.

## 6 · Derive events and scanpaths with visible assumptions

A transparent event route is useful as an inspectable baseline:

```python
from gazeforge import ivt_classify_events, samples_to_event_intervals

event_samples = ivt_classify_events(
    qc_samples,
    sampling_rate_hz=60,
    velocity_threshold_px_s=1000.0,
)
intervals = samples_to_event_intervals(
    event_samples,
    label_col="predicted_event",
    sampling_rate_hz=60,
)
```

The numeric threshold above is a worked-example setting, **not a universal physiological cutoff**.

Then map reviewed fixation centroids to reviewed AOIs and derive semantic scanpaths. Preserve the intermediate assignment table so a surprising sequence can be traced back to coordinates, fixation timing, and AOI geometry.

## 7 · Build the analysis table for the actual question

For a participant × trial analysis, a compact analysis-ready table might contain:

| Column | Meaning |
| --- | --- |
| `participant_id` | independent participant identity |
| `trial_id` | retained study trial |
| `condition` | randomized/assigned experimental condition |
| `aoi_label` | reviewed semantic AOI |
| `fixation_count` | number of retained fixation assignments |
| `dwell_ms` | total retained fixation duration in the AOI |
| `first_fixation_latency_ms` | latency to first retained fixation in the AOI |
| `transition_from` / `transition_to` | semantic sequence relation |
| `qc_status` | retained/review status carried forward |
| `source_fingerprint` | link back to the frozen source/import evidence |

The statistical model comes **after** this table is scientifically interpretable. GazeForge does not turn a repeated-measures design into independent rows merely because that is convenient for a model.

## 8 · Reconcile denominators before modelling

Before fitting a model, be able to answer:

- How many participants were acquired?
- How many were reviewed?
- How many were excluded, and by which criterion?
- How many trials were available and retained?
- How many sample rows were in the canonical table?
- How many rows were removed only because their reviewed trial/participant was excluded?
- How many AOI assignments were unassigned or outside geometry/support?
- Which analyses are primary versus exploratory?

If those numbers do not reconcile, stop before modelling.

## 9 · Freeze a manuscript/archive bundle

A strong final bundle separates source, decisions, derived data, and report-facing material:

```text
study-freeze/
├── source-manifest.json
├── import-contract.json
├── analysis-plan.json
├── decision-criteria.csv
├── exclusion-flow.csv
├── reviewed-aoi-definitions.csv
├── analysis-ready-table.csv
├── model-specification.txt
├── figures/
├── tables/
├── provenance.json
├── workflow-manifest.json
└── software-identity.txt
```

Record the exact GazeForge version or full commit SHA, Python version, key parameters, source fingerprints, and the native/derived status of any validation evidence used to justify the workflow.

Use the [Research evidence bundle](research-evidence-bundle.md) to see this separation implemented as one runnable archive, the [Artifact & output dictionary](artifact-dictionary.md) to interpret each file, then [Publication readiness](publication-readiness.md), [Validation reporting cookbook](validation-reporting-cookbook.md), and [Reproducible reporting](reproducible-reporting.md) before manuscript submission.

## Run the archive-facing worked example

The evidence-bundle example composes import, QC, reviewed decisions, a separate primary-analysis derivative, transparent events, AOIs, scanpaths, provenance, an artifact index, and a reviewer-facing README:

```bash
python examples/09_worked_research_evidence_bundle.py \
  --output-dir worked-research-evidence-bundle
```

Read [Research evidence bundle](research-evidence-bundle.md) for the exact archive logic.

The bundled static-study demonstration remains useful when the scientific focus is the static AOI workflow itself:

```bash
python examples/04_worked_advertising_study.py \
  --output-dir worked-advertising-demo
```

It writes study-shaped source, canonical/QC, event, AOI, fixation-assignment, scanpath, analysis-plan, provenance, and workflow-manifest artifacts using deterministic **synthetic/demo data**.

Read [Worked advertising/interface study](worked-advertising-study.md) for the exact output inventory and interpretation boundaries.

## What this blueprint does not establish

This worked route does not establish:

- consumer or behavioral effects;
- that an AOI is a valid measure of a psychological construct;
- that a QC threshold is universally valid;
- that an event detector is valid for every tracker or sampling rate;
- native Gazepoint/GP3 event validity from derived or synthetic evidence;
- causal effects from observational comparisons; or
- that gaze alone measures trust, persuasion, memory, preference, emotion, or diagnosis.

It shows how to make the **research workflow auditable** so those scientific questions can be evaluated with the appropriate study design and evidence.
