# Benchmarking and validation evidence

GazeForge separates **software smoke tests** from **scientific validation evidence**.
Passing synthetic tests proves that an analysis path executes as specified; it does not establish
accuracy on human eye-tracking data.

## AOI validation

`evaluate_aoi_detection()` compares AI AOI proposals with expert/reference AOIs using one-to-one
Hungarian matching and an explicit IoU threshold. It reports precision, recall, F1, mean matched
IoU, and semantic-label agreement.

`fixation_assignment_agreement()` compares the downstream fixation-to-AOI labels themselves. This
is important because small geometric differences do not necessarily alter substantive gaze
metrics, while some apparently similar boundaries can change assignment near AOI edges.

`aoi_boundary_sensitivity()` expands and contracts AOIs to quantify how robust fixation assignment
is to plausible boundary uncertainty.

## Frozen reports

`BenchmarkDatasetCard` records benchmark provenance, license, sampling rates, split unit, and the
intended validation scope. `build_benchmark_report()` creates a deterministic report fingerprint,
and `freeze_benchmark_report()` refuses to overwrite a previous report unless explicitly told to.

A report generated from synthetic data should use a scope such as `synthetic-smoke-only`. It must
not be presented as empirical validation of event classification or semantic AOI accuracy.

## Planned evidence hierarchy

1. Synthetic implementation smoke tests.
2. Internal manually annotated eye-tracking recordings with participant-held-out evaluation.
3. Public benchmark datasets with frozen splits and dataset-held-out testing.
4. Dedicated 60 Hz validation for GP3-class recordings.
5. Cross-domain AOI validation across static ads, interfaces, and other stimulus families.
