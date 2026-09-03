# Changelog

All notable changes to GazeForge will be documented here.

The project follows semantic versioning once stable releases begin. Alpha versions may change APIs
while validation evidence is being established.

## Unreleased

### Added

- Canonical vendor-neutral gaze schema and sampling-rate inference.
- Gazepoint and explicit processed-table adapters.
- Auditable Isolation-Forest QC flags and trial-quality summaries.
- Probabilistic event-model API with sampling-rate compatibility guardrails.
- Boundary-safe temporal-context MLP event classifier with probabilistic abstention metadata.
- I-VT baseline event classifier.
- Geometry-normalized angular I-VT baseline with explicit degrees/second thresholds.
- Semantic AOI provider API, optional OWL-ViT provider, human review, and fixation mapping.
- Dynamic AOI keyframes, provider protocol, gap-limited interpolation, and temporal fixation mapping.
- Dynamic AOI track evaluation with explicit timestamp grids, Hungarian IoU matching, and
  fixation-assignment agreement.
- Semantic scanpaths, motifs, TF-IDF/SVD embeddings, similarity, and clustering.
- Participant/group-held-out and leave-one-dataset-out validation.
- Matched-fold comparison of I-VT, Random Forest, and temporal-context event models.
- Descriptive matched-fold model differences with raw and direction-normalized deltas,
  win/tie/loss counts, identical-fold guardrails, and no naive cross-validation p-values or CIs.
- Post-hoc out-of-fold stratified event performance with sample, calibration, and temporal-event
  metrics, explicit fold/group counts, and no model refitting by stratum.
- Lund2013 stimulus-family performance for image, moving-dot, and video recordings, embedded in
  the same RA/MN participant-held-out benchmark reports and suite artifacts.
- Event-level temporal IoU matching, event precision/recall/F1, and onset/offset/duration error
  metrics integrated into matched-fold and cross-dataset validation.
- Sampling-rate × label-purity sensitivity surfaces with complete ambiguity/retention ledgers,
  non-evaluable-setting provenance, and matched sample/event model metrics.
- Lund2013 sampling-rate × label-purity sensitivity runner and frozen-report CLI.
- Explicit pinned Lund2013 fetch/cache command with Git-blob SHA/size verification and a
  fingerprinted local source manifest; raw benchmark files remain external.
- Run-time Lund source-manifest and local-file revalidation bound into agreement, primary benchmark,
  and sampling-sensitivity provenance when a GazeForge source manifest is present.
- One-command Lund2013 validation-suite orchestration that freezes native/60 Hz human agreement,
  RA primary modelling, MN annotator sensitivity, and RA sampling×purity sensitivity before writing
  a deterministic suite-completion manifest.
- Post-freeze Lund2013 suite verification that checks the completion manifest, exact five-report
  inventory, pinned source identity, safe child paths, and every referenced report fingerprint.
- Verified Lund suite status in the public benchmark dashboard while preserving child reports as
  separate empirical evidence rows.
- Native Lund2013 MATLAB benchmark ingestion with original expert event-code mapping.
- Label-purity-aware lower-rate benchmark resampling with explicit ambiguous boundary samples.
- MN-vs-RA sample-label agreement and a fingerprinted Lund2013 60 Hz benchmark runner/CLI.
- AOI IoU/matching, semantic-label agreement, fixation-assignment agreement, and boundary
  sensitivity metrics.
- Multiclass Brier score, ECE/reliability bins, and confidence-versus-coverage diagnostics.
- Data fingerprints, audit trails, model cards, benchmark dataset cards, and frozen report
  fingerprints.
- Benchmark evidence-strength taxonomy with native/resampled and human/algorithmic guardrails.
- External benchmark catalog entries for VISUS dynamic AOIs, Hollywood2 manual events, and
  Gaze-in-the-Wild hand-labelled naturalistic events.
- Hollywood2EM ARFF ingestion with explicit student/expert labels and unresolved-identity and
  coordinate-evidence guardrails.
- Cross-dataset Lund2013/Hollywood2 preparation and leave-one-dataset-out RF/ContextMLP validation
  with coordinate, participant-identity, resampling, and label-harmonisation guardrails.
- Gaze-in-the-Wild MATLAB ingestion with file-timestamp sampling-rate inference, confidence-based
  track loss, explicit participant identity, and single-labeller modelling-table guardrails.
- MkDocs Material website with getting-started, validation-status, benchmark, and API navigation.
- Conditional GitHub Pages deployment workflow that strict-builds even before Pages is enabled.
- Redesigned repository README as a scientific project front page.
- Synthetic gaze generation, tests, CI matrix, and documentation infrastructure.
