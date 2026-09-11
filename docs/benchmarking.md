# Benchmarking and validation evidence

GazeForge separates **software smoke tests**, **known-truth simulation**, and **empirical scientific
validation**.

Passing ordinary synthetic smoke tests proves that an analysis path executes as specified; it does
not establish accuracy. Known-truth simulation is stronger for method validation because the
latent target is exactly known, but it still establishes recovery only under the simulator's
frozen generative assumptions. Empirical validity on devices, participants, or external datasets
requires separate human/device data and the relevant leakage-aware design.

## AOI validation

`evaluate_aoi_detection()` compares AI AOI proposals with expert/reference AOIs using one-to-one
Hungarian matching and an explicit IoU threshold. It reports precision, recall, F1, mean matched
IoU, and semantic-label agreement.

`fixation_assignment_agreement()` compares the downstream fixation-to-AOI labels themselves. This
is important because small geometric differences do not necessarily alter substantive gaze
metrics, while some apparently similar boundaries can change assignment near AOI edges.

`aoi_boundary_sensitivity()` expands and contracts AOIs to quantify how robust fixation assignment
is to plausible boundary uncertainty.

## Synthetic evidence classes

GazeForge keeps two synthetic roles separate:

1. `simulate_gaze()` supports examples, smoke tests, and pipeline checks. Reports using this role
   should retain `synthetic-smoke-only` semantics.
2. `simulate_known_truth_gaze()` creates a separately fingerprinted latent truth, artifact ledger,
   corrupted observed signal, and event truth. Its `synthetic-known-truth` reference strength can
   support recovery-error claims under the frozen simulator assumptions, but never an empirical
   human/device validity claim.

See [Known-truth synthetic benchmarks](synthetic-known-truth-benchmarks.md) for the complete
contract and recovery-certificate boundary.

## Frozen reports

`BenchmarkDatasetCard` records benchmark provenance, license, sampling rates, split unit, and the
intended validation scope. `build_benchmark_report()` creates a deterministic report fingerprint,
and `freeze_benchmark_report()` refuses to overwrite a previous report unless explicitly told to.

Synthetic recovery certificates intentionally use their own schema rather than the public Frozen
empirical-evidence report schema. A passing synthetic certificate must not be presented as
empirical validation of event classification, semantic AOI accuracy, GP3 validity, or
subject-independent generalisation.

## Evidence hierarchy

1. Synthetic implementation smoke tests.
2. Synthetic known-truth recovery validation across controlled error surfaces.
3. Internal manually annotated eye-tracking recordings with participant-held-out evaluation.
4. Public benchmark datasets with frozen splits and dataset-held-out testing.
5. Dedicated native-rate validation for GP3-class recordings.
6. Cross-domain AOI validation across static ads, interfaces, and other stimulus families.
