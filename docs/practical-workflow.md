# Practical end-to-end research workflow

This guide shows how to compose GazeForge into one inspectable research workflow rather than treating the package as a collection of isolated API calls. It follows a realistic sequence:

```text
source gaze
   ↓
canonical schema
   ↓
non-destructive QC → trial-quality review
   ↓
transparent I-VT sample labels → event intervals
   ↓
fixation centroids
   ↓
researcher-defined/reviewed AOIs
   ↓
AOI assignments → semantic scanpaths
   ↓
provenance + fingerprints + optional figures
   ↓
reviewable analysis bundle
```

!!! warning "The bundled run is demonstration data, not validation evidence"
    The runnable example uses deterministic synthetic gaze and records the exact classification `synthetic_demo_not_empirical_evidence`. It is **not empirical validation** and does not establish native-device, native 60 Hz, Gazepoint, or GP3 validity. For the current empirical boundaries, use the generated [Evidence status](evidence-status.md).

## Run the complete example

From a repository checkout with the development dependencies installed:

```bash
python -m pip install -e ".[dev]"
python examples/end_to_end_research_workflow.py \
  --output-dir end-to-end-research-demo
```

The plotting layer is optional. To exercise only the analysis/export path:

```bash
python examples/end_to_end_research_workflow.py \
  --output-dir end-to-end-research-demo \
  --no-figures
```

For a packaged installation, install the plotting extra documented for that release when you want the optional figures.

## What the example writes

The output directory is intended to be reviewable rather than opaque.

| Artifact | Purpose |
| --- | --- |
| `01_source_gaze.csv` | untouched source table used by the demonstration |
| `02_canonical_gaze.csv` | vendor-neutral GazeForge schema |
| `03_qc_samples.csv` | original rows plus anomaly score/flag fields |
| `04_trial_quality.csv` | trial-level missingness, bounds, gap, anomaly, and quality summaries |
| `05_event_samples.csv` | sample-level transparent I-VT labels |
| `06_event_intervals.csv` | contiguous half-open eye-event intervals |
| `07_fixation_centroids.csv` | one coordinate row per retained fixation interval |
| `08_aoi_definitions.csv` | explicit AOI geometry and provenance |
| `09_fixation_aoi_assignments.csv` | fixation rows plus semantic AOI assignment |
| `10_semantic_scanpaths.csv` | participant/trial semantic attention sequences |
| `provenance.json` | operation-level fingerprints and parameters |
| `workflow_manifest.json` | bundle identity, evidence boundary, fingerprints, and output inventory |
| `figures/*.png` | optional QC, AOI, and scanpath diagnostics |

The example checks that its original source DataFrame is byte-equivalent at the pandas table level after the workflow. The manifest records `source_unchanged: true` only after that check succeeds.

## 1. Start from a minimum defensible input

The canonical GazeForge table requires five columns:

```text
participant_id
trial_id
timestamp_ms
x_px
y_px
```

Optional fields such as pupil size and tracker validity can remain alongside them.

If your table already uses those canonical names:

```python
from gazeforge import canonicalize_gaze

canonical = canonicalize_gaze(
    samples,
    sampling_rate_hz=60,
    screen_size_px=(1920, 1080),
)
```

Canonicalisation standardises the schema and validates declared metadata. It does **not** manufacture participant/trial identity, infer undocumented tracker semantics, repair invalid measurements, or convert an analysis-rate assumption into evidence about the native acquisition device.

### Generic processed tables

For an eye-tracking table produced by another package or a custom preprocessing pipeline, use `adapt_processed_table()` and state the mapping explicitly:

```python
from gazeforge import adapt_processed_table

canonical = adapt_processed_table(
    processed,
    participant_col="subject",
    trial_col="stimulus_id",
    timestamp_col="time_s",
    x_col="gaze_x",
    y_col="gaze_y",
    pupil_col="pupil_mm",
    timestamp_scale_to_ms=1000.0,
    coordinate_scale=(1.0, 1.0),
    sampling_rate_hz=60,
    screen_size_px=(1920, 1080),
    source_name="my_processed_export",
)
```

The important point is that `timestamp_scale_to_ms`, `coordinate_scale`, `sampling_rate_hz`, and `screen_size_px` are research metadata, not convenience decoration. Record how you obtained them.

### Gazepoint exports

For Gazepoint-style exports, use the dedicated adapter rather than guessing normalized-coordinate or time conventions:

```python
from gazeforge import adapt_gazepoint_samples

canonical = adapt_gazepoint_samples(
    gazepoint_export,
    screen_size_px=(1920, 1080),
    participant_col="USER_FILE",
    trial_col="MEDIA_ID",
    timestamp_col="TIME",
    x_col="BPOGX",
    y_col="BPOGY",
    time_unit="seconds",
    coordinates="normalized",
    sampling_rate_hz=60,
)
```

!!! important "Declare acquisition facts; do not infer validation from an adapter"
    An adapter converts documented column semantics into the canonical schema. Successfully adapting a Gazepoint/GP3 export does not establish event-classification accuracy, native-device validity, or benchmark equivalence.

## 2. Add QC without deleting samples

GazeForge's QC layer is intentionally non-destructive:

```python
from gazeforge import AuditTrail, ai_flag_anomalies, score_trial_quality

trail = AuditTrail()
flagged = ai_flag_anomalies(
    canonical.data,
    sampling_rate_hz=canonical.sampling_rate_hz,
    random_state=42,
    trail=trail,
)
quality = score_trial_quality(
    flagged,
    screen_size_px=canonical.screen_size_px,
)
```

`ai_flag_anomalies()` adds scores and flags to copied data. It does not remove rows. `score_trial_quality()` then gives trial-level summaries that can support a prespecified review/exclusion rule.

A defensible sequence is:

```text
QC evidence → researcher review → documented rule → exclusion decision
```

not:

```text
AI flag → automatic deletion
```

Archive the pre-exclusion table and the decision rule. If thresholds are exploratory, label them as such rather than presenting them as preregistered.

## 3. Use an inspectable event baseline before a learned alternative

The runnable example uses the transparent pixel-velocity I-VT baseline:

```python
from gazeforge import ivt_classify_events, samples_to_event_intervals

event_samples = ivt_classify_events(
    flagged,
    sampling_rate_hz=canonical.sampling_rate_hz,
    velocity_threshold_px_s=1000.0,
)

event_intervals = samples_to_event_intervals(
    event_samples,
    label_col="predicted_event",
    sampling_rate_hz=canonical.sampling_rate_hz,
)
```

The threshold is explicit and inspectable. That makes I-VT a useful baseline for understanding the pipeline, but it is not a claim that the threshold is optimal for every tracker, geometry, task, or participant population.

For confirmatory use, choose the event method and threshold from appropriate prior evidence or validate them against suitable human/reference labels. Learned models should be compared on matched held-out data, not substituted merely because they are more complex.

## 4. Convert event intervals to fixation-level rows deliberately

AOI and scanpath analyses usually require fixation-level coordinates rather than every raw gaze sample. The example computes one centroid per fixation interval while preserving:

- participant identity;
- trial identity;
- event index;
- start/end time;
- duration;
- sample count;
- centroid x/y coordinates.

This is an analysis transformation, so it receives its own provenance record. It should not overwrite the sample-level table.

For a different scientific design, you may prefer another fixation summary or an external fixation table. Preserve the lineage from source samples to the fixation representation you actually analyse.

## 5. Treat AOIs as research objects with provenance

The example uses three non-overlapping, explicitly researcher-defined rectangles:

```python
from gazeforge import AOI, aois_to_frame, map_fixations_to_aois

aois = [
    AOI("header", "header", 0, 0, 1920, 260, source="researcher_defined"),
    AOI(
        "left_panel",
        "left panel",
        0,
        260,
        820,
        1080,
        source="researcher_defined",
    ),
    AOI(
        "main_content",
        "main content",
        820,
        260,
        1920,
        1080,
        source="researcher_defined",
    ),
]

aoi_table = aois_to_frame(aois)
assignments = map_fixations_to_aois(
    fixation_centroids,
    aois,
    overlap_rule="first",
)
```

For a real study, AOI provenance should state whether geometry was:

- researcher-defined;
- manually annotated;
- imported from a stimulus specification;
- proposed by a computer-vision model and human-reviewed;
- dynamically tracked through video.

AI-generated AOIs are proposals until reviewed. If bounds or labels are changed, preserve the review/correction record rather than silently replacing the original proposal.

## 6. Build semantic scanpaths without diagnosing latent states

Once fixations have semantic AOI labels:

```python
from gazeforge import to_semantic_scanpaths

scanpaths = to_semantic_scanpaths(assignments)
```

A semantic scanpath can support questions such as:

- which visible regions were inspected;
- in what order regions were visited;
- how many transitions occurred;
- whether sequences differ under a prespecified experimental contrast.

It does not, by itself, identify emotion, preference, comprehension, persuasion, deception, personality, or another latent psychological state. Those interpretations require independent constructs, outcomes, design logic, and evidence.

## 7. Inspect figures and intermediate tables

The example can write three optional diagnostics:

1. a sample-level QC anomaly timeline;
2. researcher-defined AOIs over fixation centroids;
3. the semantic scanpath for one participant/trial.

These plots are diagnostics of already-computed structures. They do not alter rows, refit models, or constitute empirical validation evidence.

The most useful review habit is to inspect tables and plots together. A visually plausible scanpath is not a substitute for checking timestamps, event intervals, AOI provenance, missingness, or assignment rules.

## 8. Preserve provenance and fingerprints

The example uses `AuditTrail` and `fingerprint_frame()` to record the major transformations. The manifest also fingerprints every exported table.

That provides a practical answer to questions such as:

- Which table entered each operation?
- Which parameters were used?
- Did the source table change?
- Which exact output tables belong to this run?
- Can a collaborator detect accidental output drift?

A fingerprint is an integrity aid, not proof that the scientific design is valid. It cannot replace source authority, suitable reference labels, held-out validation, preregistration, or substantive theory.

## 9. Replace the demo with a real experiment

For real data, replace only the synthetic input step and then review every assumption that follows.

1. Export or load the tracker table without deleting source columns prematurely.
2. Preserve participant, trial/stimulus, session, and condition identifiers required by the design.
3. Adapt the source using `canonicalize_gaze()`, `adapt_processed_table()`, or `adapt_gazepoint_samples()` with explicit units.
4. Record tracker model, acquisition sampling rate, display geometry, timestamp convention, and any upstream processing.
5. Review QC summaries and apply a prespecified/documented exclusion procedure; retain the pre-exclusion evidence.
6. Select an event method whose assumptions match the acquisition geometry and validation evidence available for the study.
7. Define or review AOIs before confirmatory outcome testing where feasible, and archive AOI geometry/provenance.
8. Create fixation/AOI/scanpath outputs without losing participant/trial identity.
9. Archive the exact GazeForge version or commit SHA, environment, parameters, source identity, and bundle fingerprints.
10. Check [Evidence status](evidence-status.md) before using any benchmark or native-device statement in a manuscript.

### Example: replace the synthetic source

The only top-level source change can be as small as:

```python
import pandas as pd
from gazeforge import adapt_processed_table

raw = pd.read_csv("my_tracker_export.csv")
gaze = adapt_processed_table(
    raw,
    participant_col="participant",
    trial_col="trial",
    timestamp_col="timestamp_s",
    x_col="x_px",
    y_col="y_px",
    timestamp_scale_to_ms=1000.0,
    sampling_rate_hz=60,
    screen_size_px=(1920, 1080),
    source_name="study_export_v1",
)
```

Do not mechanically reuse `60`, the example AOIs, or the I-VT threshold unless they are correct for your recording and research design.

## 10. Archive a manuscript-ready analysis bundle

At minimum, archive or report:

- source-data identity and access/version information;
- exact GazeForge release or commit SHA;
- Python/environment lock or package inventory;
- tracker, native acquisition rate, display geometry, and timestamp/coordinate units;
- canonicalisation/adapter mapping;
- QC variables, review rule, and exclusions;
- event method, parameters, and validation basis;
- AOI definitions, provenance, and human-review decisions;
- fixation/AOI/scanpath analysis tables actually used downstream;
- statistical-analysis code separated from measurement preprocessing where practical;
- provenance records and output fingerprints;
- evidence-status boundary for any benchmark or device-specific claim.

Continue with [Reproducible reporting](reproducible-reporting.md) for the manuscript-facing checklist and [Citation & attribution](citation-attribution.md) for release-versus-development citation guidance.

## Common mistakes this workflow is designed to prevent

| Mistake | Better practice |
| --- | --- |
| deleting AI-flagged rows automatically | preserve flags, review, document the exclusion rule |
| treating canonicalisation as validation | separate schema conversion from empirical validity |
| using a learned event model without a transparent comparator | inspect a rule-based baseline and validate on matched held-out data |
| losing participant/trial identity during aggregation | carry identifiers through every derived table |
| allowing AI AOIs to become ground truth silently | retain proposal/model/review provenance |
| treating a semantic sequence as a cognitive diagnosis | interpret observable order/transition features at the supported level |
| citing a synthetic demo as performance evidence | label it `synthetic_demo_not_empirical_evidence` |
| treating derived/resampled evidence as native-device validity | preserve acquisition-versus-analysis-rate distinctions |
| archiving only the final statistics table | archive intermediate tables, parameters, provenance, and fingerprints |
