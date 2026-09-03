# VISUS model-human validation

GazeForge provides a source-audit-aware orchestration layer for evaluating a dynamic-AOI detector or tracker against one explicitly selected human-reference stream from an audited VISUS snapshot.

This workflow is **validation infrastructure**, not a frozen VISUS result. A real empirical claim still requires an independently obtained source copy that passes the VISUS source audit, real model predictions, reviewed timestamp grids, and scientific review of the resulting fingerprinted report.

## Why the source audit is mandatory

`run_visus_dynamic_aoi_model_validation()` accepts only a verified `VisusSourceAuditRun`. Before evaluating predictions it revalidates the source-audit report fingerprint, specification fingerprint, and exact source-manifest fingerprint.

The runner also requires:

- an explicit AOI reference-stream identifier that is manifested for every audited stimulus;
- complete prediction, reference, and timestamp-grid coverage of every audited stimulus;
- an explicit model name and model version;
- an explicit description of where the evaluation timestamp grid came from;
- a fixed numeric interpolation-gap policy;
- an explicit IoU threshold and semantic-label matching policy.

Prediction timestamps never define the evaluation grid. The caller supplies a strictly increasing grid for every stimulus, and the report fingerprints each grid separately.

## Dynamic geometry and semantic evaluation

For every audited stimulus, the runner uses the existing dynamic-AOI evaluation stack to resolve model and human tracks on the same timestamp grid. Geometry outside observed keyframe ranges is not extrapolated. Gaps wider than `max_interpolation_gap_ms` are not interpolated.

The resulting report contains per-stimulus and pooled:

- true-positive, false-positive, and false-negative AOI detections;
- precision, recall, and F1;
- mean IoU for accepted matches;
- semantic-label accuracy among accepted matches;
- evaluated and empty timestamp counts.

Full timestamp-level matches can be included when needed for auditability, but are optional because video benchmarks can produce large artifacts.

## Optional fixation-assignment validation

If fixation tables are supplied for every stimulus, the runner maps the same fixations through model and human AOIs and reports overall and per-stimulus fixation-to-AOI assignment agreement.

The current fixation mapping interface uses `x_px`/`y_px`, so this path is enabled only when the source audit verifies pixel coordinates. Geometry-only dynamic-AOI evaluation can still operate with another explicitly verified common coordinate system.

## Annotation provenance

The selected AOI stream is treated as **one human reference**. The published VISUS workflow involved two contributors to a curated annotation process; that fact is not converted into two independent annotation streams. Accordingly, this model-human report always records `human_human_agreement_claimed=false`.

Human-human agreement is a separate empirical question and remains blocked unless the audited source itself proves that independently recoverable annotation streams exist.

## Example

```python
from gazeforge.visus_validation import run_visus_dynamic_aoi_model_validation

run = run_visus_dynamic_aoi_model_validation(
    audit,
    predicted_by_stimulus=model_tracks,
    reference_by_stimulus=human_tracks,
    timestamps_by_stimulus=video_frame_times,
    reference_stream_id="published_curated",
    model_name="my-tracker",
    model_version="1.0.0",
    timestamp_grid_basis="decoded timestamps from the audited video files",
    max_interpolation_gap_ms=80.0,
    min_iou=0.50,
    require_label_match=True,
)
```

`run.report` is deterministic and carries the VISUS source-audit, source-specification, and exact-manifest fingerprints. Use the ordinary benchmark freezing/review workflow only after the real audited source and prediction artifacts have been inspected.
