# VISUS human-human dynamic-AOI agreement

GazeForge contains a deliberately **conditional** VISUS human-human agreement runner. It is not available merely because the published VISUS annotation workflow involved two human contributors.

The source audit must first establish that the local authoritative copy contains **separately recoverable independent AOI annotation streams** for every audited stimulus. Only then does `run_visus_dynamic_aoi_human_agreement()` execute.

## Why this gate matters

The published VISUS workflow describes a curated annotation process in which one contributor performed the main annotation and another added or refined annotations. Contributor count is therefore not automatically an annotator-reliability design. Treating that published description as two independent ground-truth streams would overstate the evidence.

A verified `VisusSourceAuditRun` must report:

```text
independent_annotation_streams_verified = true
human_human_agreement_ready = true
```

and both requested stream identifiers must be explicitly manifested for every audited stimulus.

## Agreement design

When the independence gate is satisfied, the runner requires complete stimulus coverage for:

- the left human AOI stream;
- the right human AOI stream;
- an explicit common timestamp grid for each stimulus;
- optional fixation tables, when fixation-to-AOI assignment agreement is requested.

The two stream identifiers must be distinct. Source-audit report, specification, and exact-manifest fingerprints are revalidated before any metric is computed.

### Bidirectional geometry and semantic metrics

Dynamic AOI matching is evaluated twice:

1. left stream treated as the predicted set and right stream as the reference set;
2. right stream treated as the predicted set and left stream as the reference set.

This produces directional precision, recall, F1, IoU, semantic-label agreement, and timestamp coverage without presenting either annotator as error-free ground truth. The input AOI tracks and timestamp grids receive deterministic per-stimulus fingerprints in the report.

Interpolation remains gap limited and temporal extrapolation is disabled.

### Fixation-assignment agreement

When identical fixation tables are supplied, GazeForge maps each fixation through both independent AOI streams and reports overall and per-stimulus exact agreement and Cohen's kappa. This path currently requires an audited pixel coordinate basis because fixation locations use `x_px` and `y_px`.

## Evidence interpretation

Human-human agreement describes **annotation variability**. It is not a model-performance score, an error-free ceiling, or proof that one stream is correct.

The implementation also does not prove that the historical VISUS distribution contains independent streams. That is an empirical source-audit question. Until an authoritative copy demonstrates stream independence, the relevant empirical roadmap task remains open and no VISUS human-human result should be frozen.

## Example

```python
from gazeforge.visus_agreement import run_visus_dynamic_aoi_human_agreement

agreement = run_visus_dynamic_aoi_human_agreement(
    audit,
    left_by_stimulus=annotator_a_tracks,
    right_by_stimulus=annotator_b_tracks,
    timestamps_by_stimulus=video_frame_times,
    left_stream_id="annotator_a",
    right_stream_id="annotator_b",
    timestamp_grid_basis="decoded timestamps from the audited video files",
    max_interpolation_gap_ms=80.0,
    min_iou=0.50,
    require_label_match=True,
)
```

If the source audit has not independently verified both streams, this call raises an integrity error rather than manufacturing a human-human agreement result.
