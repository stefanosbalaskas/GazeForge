"""GazeForge: auditable AI for eye-tracking analysis."""

from importlib.metadata import PackageNotFoundError, version

from .adapters import adapt_gazepoint_samples, adapt_processed_table
from .aoi import (
    AOI,
    CallableAOIProvider,
    HuggingFaceZeroShotAOIProvider,
    aois_to_frame,
    apply_aoi_review,
    detect_semantic_aois,
    map_fixations_to_aois,
)
from .audit import build_audit_report
from .benchmark_catalog import (
    gaze_in_wild_manual_event_card,
    hollywood2_manual_event_card,
    visus_dynamic_aoi_card,
)
from .benchmarks import (
    BenchmarkDatasetCard,
    benchmark_fingerprint,
    build_benchmark_report,
    freeze_benchmark_report,
)
from .calibration import (
    evaluate_event_calibration,
    expected_calibration_error,
    multiclass_brier_score,
    selective_accuracy_curve,
    top_label_calibration_table,
)
from .comparison import EventModelComparison, compare_event_models_grouped
from .cross_dataset import (
    CrossDatasetEventPrepared,
    CrossDatasetEventValidation,
    prepare_cross_dataset_event_benchmark,
    run_cross_dataset_event_validation,
)
from .dashboard import (
    BenchmarkDashboard,
    build_benchmark_dashboard,
    discover_frozen_benchmark_reports,
    discover_lund2013_suite_manifests,
    load_frozen_benchmark_report,
    render_benchmark_dashboard_markdown,
    validate_frozen_benchmark_report,
)
from .dynamic_aoi import (
    CallableDynamicAOIProvider,
    DynamicAOIKeyframe,
    detect_dynamic_aois,
    dynamic_aois_from_frame,
    dynamic_aois_to_frame,
    interpolate_dynamic_aoi,
    map_fixations_to_dynamic_aois,
)
from .dynamic_evaluation import (
    DynamicAOIEvaluation,
    build_dynamic_aoi_benchmark_report,
    dynamic_aoi_snapshot,
    dynamic_fixation_assignment_agreement,
    evaluate_dynamic_aoi_tracks,
)
from .evaluation import (
    aoi_boundary_sensitivity,
    aoi_iou,
    evaluate_aoi_detection,
    fixation_assignment_agreement,
    match_aois,
    pairwise_aoi_iou,
    sample_label_agreement,
)
from .event_evaluation import (
    EventLevelEvaluation,
    evaluate_event_intervals,
    evaluate_sample_event_predictions,
    match_event_intervals,
    samples_to_event_intervals,
    temporal_event_iou,
)
from .events import (
    EventModel,
    ai_classify_events,
    evaluate_event_predictions,
    ivt_classify_events,
    ivt_classify_events_angular,
    train_event_classifier,
)
from .exceptions import BenchmarkIntegrityError
from .gaze_in_wild import (
    GAZE_IN_WILD_LABELS,
    load_gaze_in_wild_directory,
    load_gaze_in_wild_mat,
)
from .geometry import angular_kinematic_features, pixels_to_visual_angle_deg
from .hollywood2 import (
    HOLLYWOOD2_ANNOTATOR_COLUMNS,
    HOLLYWOOD2_EVENT_LABELS,
    load_hollywood2_arff,
    load_hollywood2_directory,
)
from .lund2013 import LUND2013_LABELS, load_lund2013_directory, load_lund2013_mat
from .lund_benchmark import (
    Lund2013BenchmarkRun,
    Lund2013PreparedBenchmark,
    compare_lund2013_annotators,
    prepare_lund2013_benchmark,
    run_lund2013_event_benchmark,
)
from .lund_fetch import (
    LUND2013_ANNOTATORS,
    LUND2013_COMMIT,
    LUND2013_DATA_PATH,
    LUND2013_FAMILIES,
    LUND2013_REPOSITORY,
    Lund2013FetchResult,
    fetch_lund2013_dataset,
    validate_lund2013_source_manifest,
)
from .lund_sensitivity import Lund2013SensitivityRun, run_lund2013_sampling_sensitivity
from .lund_suite import (
    Lund2013BenchmarkSuiteRun,
    run_lund2013_benchmark_suite,
    validate_lund2013_suite_manifest,
)
from .model_cards import ModelCard
from .provenance import AuditTrail, ProvenanceRecord, fingerprint_frame
from .qc import ai_flag_anomalies, detect_calibration_drift, score_trial_quality
from .resampling import BenchmarkResamplingResult, resample_labeled_gaze
from .sampling_sensitivity import (
    SamplingSensitivityResult,
    evaluate_sampling_purity_sensitivity,
)
from .scanpath import (
    ScanpathEmbeddingModel,
    cluster_scanpaths_ai,
    embed_scanpaths,
    find_scanpath_motifs,
    fit_scanpath_embedder,
    scanpath_similarity,
    to_semantic_scanpaths,
)
from .schema import GazeFrame, canonicalize_gaze, infer_sampling_rate_hz
from .simulate import simulate_gaze
from .temporal import (
    TemporalContextModel,
    ai_classify_events_context,
    train_context_event_classifier,
)
from .validation import (
    ValidationResult,
    assert_no_group_leakage,
    dataset_holdout_context_event_validate,
    dataset_holdout_event_validate,
    grouped_context_event_cross_validate,
    grouped_event_cross_validate,
    grouped_holdout_indices,
)

try:
    __version__ = version("gazeforge")
except PackageNotFoundError:
    __version__ = "0+unknown"

__all__ = [
    "AOI",
    "ValidationResult",
    "AuditTrail",
    "BenchmarkDashboard",
    "BenchmarkDatasetCard",
    "BenchmarkIntegrityError",
    "BenchmarkResamplingResult",
    "CallableAOIProvider",
    "CallableDynamicAOIProvider",
    "CrossDatasetEventPrepared",
    "CrossDatasetEventValidation",
    "DynamicAOIEvaluation",
    "DynamicAOIKeyframe",
    "EventLevelEvaluation",
    "EventModel",
    "EventModelComparison",
    "GAZE_IN_WILD_LABELS",
    "GazeFrame",
    "HuggingFaceZeroShotAOIProvider",
    "HOLLYWOOD2_ANNOTATOR_COLUMNS",
    "HOLLYWOOD2_EVENT_LABELS",
    "LUND2013_ANNOTATORS",
    "LUND2013_COMMIT",
    "LUND2013_DATA_PATH",
    "LUND2013_FAMILIES",
    "LUND2013_LABELS",
    "LUND2013_REPOSITORY",
    "Lund2013BenchmarkRun",
    "Lund2013BenchmarkSuiteRun",
    "Lund2013FetchResult",
    "Lund2013PreparedBenchmark",
    "Lund2013SensitivityRun",
    "ModelCard",
    "ProvenanceRecord",
    "SamplingSensitivityResult",
    "ScanpathEmbeddingModel",
    "TemporalContextModel",
    "adapt_gazepoint_samples",
    "adapt_processed_table",
    "aoi_boundary_sensitivity",
    "aoi_iou",
    "ai_classify_events",
    "angular_kinematic_features",
    "ai_classify_events_context",
    "ai_flag_anomalies",
    "aois_to_frame",
    "apply_aoi_review",
    "assert_no_group_leakage",
    "benchmark_fingerprint",
    "build_audit_report",
    "build_benchmark_dashboard",
    "build_dynamic_aoi_benchmark_report",
    "build_benchmark_report",
    "canonicalize_gaze",
    "cluster_scanpaths_ai",
    "compare_event_models_grouped",
    "compare_lund2013_annotators",
    "detect_calibration_drift",
    "detect_dynamic_aois",
    "dataset_holdout_context_event_validate",
    "dataset_holdout_event_validate",
    "detect_semantic_aois",
    "discover_frozen_benchmark_reports",
    "discover_lund2013_suite_manifests",
    "dynamic_aoi_snapshot",
    "dynamic_aois_from_frame",
    "dynamic_aois_to_frame",
    "dynamic_fixation_assignment_agreement",
    "embed_scanpaths",
    "evaluate_aoi_detection",
    "evaluate_dynamic_aoi_tracks",
    "evaluate_event_intervals",
    "evaluate_event_calibration",
    "evaluate_sample_event_predictions",
    "evaluate_event_predictions",
    "evaluate_sampling_purity_sensitivity",
    "expected_calibration_error",
    "fetch_lund2013_dataset",
    "fixation_assignment_agreement",
    "freeze_benchmark_report",
    "find_scanpath_motifs",
    "fingerprint_frame",
    "fit_scanpath_embedder",
    "gaze_in_wild_manual_event_card",
    "grouped_context_event_cross_validate",
    "grouped_event_cross_validate",
    "grouped_holdout_indices",
    "hollywood2_manual_event_card",
    "infer_sampling_rate_hz",
    "interpolate_dynamic_aoi",
    "ivt_classify_events",
    "ivt_classify_events_angular",
    "load_frozen_benchmark_report",
    "load_gaze_in_wild_directory",
    "load_gaze_in_wild_mat",
    "load_hollywood2_arff",
    "load_hollywood2_directory",
    "load_lund2013_directory",
    "load_lund2013_mat",
    "map_fixations_to_aois",
    "map_fixations_to_dynamic_aois",
    "multiclass_brier_score",
    "match_event_intervals",
    "match_aois",
    "pairwise_aoi_iou",
    "pixels_to_visual_angle_deg",
    "prepare_cross_dataset_event_benchmark",
    "prepare_lund2013_benchmark",
    "render_benchmark_dashboard_markdown",
    "resample_labeled_gaze",
    "run_lund2013_benchmark_suite",
    "run_lund2013_event_benchmark",
    "run_lund2013_sampling_sensitivity",
    "run_cross_dataset_event_validation",
    "samples_to_event_intervals",
    "sample_label_agreement",
    "scanpath_similarity",
    "score_trial_quality",
    "selective_accuracy_curve",
    "simulate_gaze",
    "temporal_event_iou",
    "to_semantic_scanpaths",
    "top_label_calibration_table",
    "train_context_event_classifier",
    "train_event_classifier",
    "validate_frozen_benchmark_report",
    "validate_lund2013_source_manifest",
    "validate_lund2013_suite_manifest",
    "visus_dynamic_aoi_card",
]
