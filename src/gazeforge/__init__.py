"""GazeForge: auditable AI for eye-tracking analysis."""

from importlib.metadata import PackageNotFoundError, version

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
from .events import (
    EventModel,
    ai_classify_events,
    evaluate_event_predictions,
    ivt_classify_events,
    train_event_classifier,
)
from .model_cards import ModelCard
from .provenance import AuditTrail, ProvenanceRecord, fingerprint_frame
from .qc import ai_flag_anomalies, detect_calibration_drift, score_trial_quality
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

try:
    __version__ = version("gazeforge")
except PackageNotFoundError:
    __version__ = "0+unknown"

__all__ = [
    "AOI",
    "AuditTrail",
    "CallableAOIProvider",
    "EventModel",
    "GazeFrame",
    "HuggingFaceZeroShotAOIProvider",
    "ModelCard",
    "ProvenanceRecord",
    "ScanpathEmbeddingModel",
    "ai_classify_events",
    "ai_flag_anomalies",
    "aois_to_frame",
    "apply_aoi_review",
    "build_audit_report",
    "canonicalize_gaze",
    "cluster_scanpaths_ai",
    "detect_calibration_drift",
    "detect_semantic_aois",
    "embed_scanpaths",
    "evaluate_event_predictions",
    "find_scanpath_motifs",
    "fingerprint_frame",
    "fit_scanpath_embedder",
    "infer_sampling_rate_hz",
    "ivt_classify_events",
    "map_fixations_to_aois",
    "scanpath_similarity",
    "score_trial_quality",
    "simulate_gaze",
    "to_semantic_scanpaths",
    "train_event_classifier",
]
