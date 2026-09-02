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
from .dynamic_aoi import (
    CallableDynamicAOIProvider,
    DynamicAOIKeyframe,
    detect_dynamic_aois,
    dynamic_aois_to_frame,
    interpolate_dynamic_aoi,
    map_fixations_to_dynamic_aois,
)
from .evaluation import (
    aoi_boundary_sensitivity,
    aoi_iou,
    evaluate_aoi_detection,
    fixation_assignment_agreement,
    sample_label_agreement,
    match_aois,
    pairwise_aoi_iou,
)
from .events import (
    EventModel,
    ai_classify_events,
    evaluate_event_predictions,
    ivt_classify_events,
    ivt_classify_events_angular,
    train_event_classifier,
)
from .geometry import angular_kinematic_features, pixels_to_visual_angle_deg
from .lund2013 import LUND2013_LABELS, load_lund2013_directory, load_lund2013_mat
from .lund_benchmark import (
    Lund2013BenchmarkRun,
    Lund2013PreparedBenchmark,
    compare_lund2013_annotators,
    prepare_lund2013_benchmark,
    run_lund2013_event_benchmark,
)
from .model_cards import ModelCard
from .provenance import AuditTrail, ProvenanceRecord, fingerprint_frame
from .qc import ai_flag_anomalies, detect_calibration_drift, score_trial_quality
from .resampling import BenchmarkResamplingResult, resample_labeled_gaze
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
    "BenchmarkDatasetCard",
    "BenchmarkResamplingResult",
    "CallableAOIProvider",
    "CallableDynamicAOIProvider",
    "DynamicAOIKeyframe",
    "EventModel",
    "EventModelComparison",
    "GazeFrame",
    "HuggingFaceZeroShotAOIProvider",
    "LUND2013_LABELS",
    "Lund2013BenchmarkRun",
    "Lund2013PreparedBenchmark",
    "ModelCard",
    "ProvenanceRecord",
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
    "dynamic_aois_to_frame",
    "embed_scanpaths",
    "evaluate_aoi_detection",
    "evaluate_event_calibration",
    "evaluate_event_predictions",
    "expected_calibration_error",
    "fixation_assignment_agreement",
    "freeze_benchmark_report",
    "find_scanpath_motifs",
    "fingerprint_frame",
    "fit_scanpath_embedder",
    "grouped_context_event_cross_validate",
    "grouped_event_cross_validate",
    "grouped_holdout_indices",
    "infer_sampling_rate_hz",
    "interpolate_dynamic_aoi",
    "ivt_classify_events",
    "ivt_classify_events_angular",
    "load_lund2013_directory",
    "load_lund2013_mat",
    "map_fixations_to_aois",
    "map_fixations_to_dynamic_aois",
    "multiclass_brier_score",
    "match_aois",
    "pairwise_aoi_iou",
    "pixels_to_visual_angle_deg",
    "prepare_lund2013_benchmark",
    "resample_labeled_gaze",
    "run_lund2013_event_benchmark",
    "sample_label_agreement",
    "scanpath_similarity",
    "score_trial_quality",
    "selective_accuracy_curve",
    "simulate_gaze",
    "to_semantic_scanpaths",
    "top_label_calibration_table",
    "train_context_event_classifier",
    "train_event_classifier",
]
