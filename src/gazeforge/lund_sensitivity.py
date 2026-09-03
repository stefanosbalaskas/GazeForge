"""Lund2013 sampling-rate and annotation-boundary sensitivity workflow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .benchmarks import BenchmarkDatasetCard, build_benchmark_report
from .exceptions import SchemaError
from .lund2013 import load_lund2013_directory
from .sampling_sensitivity import (
    SamplingSensitivityResult,
    evaluate_sampling_purity_sensitivity,
)


@dataclass(slots=True)
class Lund2013SensitivityRun:
    """Sensitivity surface, dataset evidence card, and deterministic benchmark report."""

    sensitivity: SamplingSensitivityResult
    dataset_card: BenchmarkDatasetCard
    report: dict[str, Any]


def _json_safe_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    clean = frame.astype(object).where(pd.notna(frame), None)
    return clean.to_dict(orient="records")


def run_lund2013_sampling_sensitivity(
    root: str | Path,
    *,
    annotator: str = "RA",
    target_sampling_rates_hz: tuple[float, ...] = (120.0, 90.0, 60.0, 30.0),
    min_label_purities: tuple[float, ...] = (0.60, 0.75, 0.90),
    n_splits: int = 5,
    ivt_velocity_threshold_deg_s: float = 45.0,
    random_state: int = 42,
    n_estimators: int = 200,
    context_radius_ms: float = 50.0,
    rolling_window_ms: float = 80.0,
    hidden_layer_sizes: tuple[int, ...] = (64, 32),
    temporal_solver: str = "adam",
    temporal_max_iter: int = 200,
    calibration_bins: int = 10,
    event_min_iou: float = 0.50,
    max_interpolation_gap_ms: float | None = None,
) -> Lund2013SensitivityRun:
    """Evaluate Lund2013 across lower sampling rates and label-purity thresholds.

    The workflow uses one expert annotation stream at a time, records ambiguity before exclusions,
    and applies the same default label policy as the primary Lund benchmark. The angular I-VT
    baseline remains fixed at the supplied degrees/second threshold across the sensitivity surface.
    """
    gaze = load_lund2013_directory(root, annotator=annotator)
    source = gaze.data.copy()
    source_rate = float(gaze.sampling_rate_hz)
    n_participants = int(source["participant_id"].nunique())
    folds = min(int(n_splits), n_participants)
    if folds < 2:
        raise SchemaError("At least two participant folds are required for Lund sensitivity.")

    sensitivity = evaluate_sampling_purity_sensitivity(
        source,
        target_sampling_rates_hz=target_sampling_rates_hz,
        min_label_purities=min_label_purities,
        source_sampling_rate_hz=source_rate,
        n_splits=folds,
        ivt_velocity_threshold_px_s=None,
        ivt_velocity_threshold_deg_s=ivt_velocity_threshold_deg_s,
        random_state=random_state,
        n_estimators=n_estimators,
        context_radius_ms=context_radius_ms,
        rolling_window_ms=rolling_window_ms,
        hidden_layer_sizes=hidden_layer_sizes,
        temporal_solver=temporal_solver,
        temporal_max_iter=temporal_max_iter,
        calibration_bins=calibration_bins,
        event_min_iou=event_min_iou,
        max_interpolation_gap_ms=max_interpolation_gap_ms,
    )

    analysis_rates = [
        float(value) for value in sensitivity.design["target_sampling_rates_hz"]
    ]
    card = BenchmarkDatasetCard(
        name="Lund2013-sampling-sensitivity",
        version="Andersson-et-al-2017-public-repository",
        source="richardandersson/EyeMovementDetectorEvaluation",
        license="GPL-3.0 repository license; raw benchmark is not bundled by GazeForge",
        task="sampling-rate and annotation-boundary sensitivity for eye-movement classification",
        sampling_rates_hz=[source_rate, *analysis_rates],
        participant_count=n_participants,
        stimulus_count=int(source["trial_id"].nunique()),
        split_unit="participant_id",
        validation_scope="external-empirical-sensitivity-analysis",
        annotation_origin="expert-manual",
        sampling_origin="resampled",
        reference_strength="derived-human-reference",
        human_annotator_count=1,
        reference_description=(
            f"Expert {annotator} sample labels are independently transferred to each lower-rate "
            "condition using explicit majority-window purity rules."
        ),
        notes=[
            "Every sensitivity condition is derived from the native high-rate human annotations.",
            "Ambiguity prevalence is recorded before excluded labels are removed from modelling.",
            "The angular I-VT threshold is held constant across target sampling rates.",
            "This analysis does not convert derived 60 Hz evidence into native 60 Hz evidence.",
        ],
    )
    metrics = {
        "settings": _json_safe_records(sensitivity.settings),
        "model_metrics": _json_safe_records(sensitivity.model_metrics),
        "sensitivity_fingerprint_sha256": sensitivity.report_fingerprint_sha256,
        "source_label_counts": (
            source["event_label"].fillna("MISSING").astype(str).value_counts().sort_index().to_dict()
        ),
    }
    protocol = {
        "dataset": "Lund2013",
        "annotator": annotator,
        "source_sampling_rate_hz": source_rate,
        "participant_count": n_participants,
        "trial_count": int(source["trial_id"].nunique()),
        "comparison_folds": folds,
        "ivt_velocity_threshold_deg_s": float(ivt_velocity_threshold_deg_s),
        "sensitivity_design": sensitivity.design,
    }
    report = build_benchmark_report(
        benchmark=card,
        metrics=metrics,
        model={"models": ["I-VT", "RandomForest", "ContextMLP"]},
        protocol=protocol,
    )
    return Lund2013SensitivityRun(
        sensitivity=sensitivity,
        dataset_card=card,
        report=report,
    )
