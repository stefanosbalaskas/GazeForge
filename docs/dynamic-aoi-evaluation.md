# Dynamic AOI evaluation

GazeForge evaluates moving AOIs on an **explicit timestamp grid**. The grid is supplied by the
benchmark protocol (for example, video frame timestamps) rather than inferred from a model's own
predictions. This prevents a tracker from improving apparent coverage merely by choosing when to
emit keyframes.

## Geometry and semantic agreement

`evaluate_dynamic_aoi_tracks()` resolves each predicted and reference AOI track at every evaluation
timestamp using the same guarded interpolation used by fixation mapping. Geometry is never
extrapolated beyond the observed keyframe range, and interpolation across gaps larger than the
configured maximum is refused.

At each timestamp, AOIs are matched one-to-one with global Hungarian assignment. The evaluator
reports:

- true positives, false positives, and false negatives across the full time grid;
- precision, recall, and F1;
- mean IoU across accepted matches;
- semantic-label accuracy among accepted matches;
- predicted and reference track-timepoint coverage;
- empty evaluation timestamps; and
- timestamp-level match records for auditability.

`require_label_match=True` makes semantic identity part of the matching criterion rather than a
secondary diagnostic.

## Fixation-assignment agreement

`dynamic_fixation_assignment_agreement()` maps the same fixation rows through two dynamic AOI
references and reports exact assignment agreement, Cohen's kappa, and assignment rates. This is
useful for human-human AOI reliability before model-human performance is interpreted.

## Benchmark reports

`build_dynamic_aoi_benchmark_report()` combines the evaluation with a `BenchmarkDatasetCard` and
produces the same deterministic SHA-256 report fingerprint used by event benchmarks. Timestamp
summaries are retained by default; full individual match rows can be included when required.

## VISUS candidate protocol

VISUS is a strong candidate because published descriptions report native 60 Hz gaze, 11 dynamic
video stimuli, and two human AOI annotators using rectangular keyframes. The historical dataset
endpoint is not treated as a stable dependency. GazeForge therefore records a candidate protocol
but does not redistribute the raw benchmark or claim completed empirical validation until a current
authoritative local copy and its reuse terms are verified.
