"""Reproducible Lund2013 empirical event-classification benchmark workflows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .benchmarks import BenchmarkDatasetCard, build_benchmark_report
from .comparison import EventModelComparison, compare_event_models_grouped
from .evaluation import sample_label_agreement
from .exceptions import SchemaError
from .lund2013 import load_lund2013_directory
from .resampling import BenchmarkResamplingResult, resample_labeled_gaze

_DEFAULT_EXCLUDED_LABELS = ("ambiguous", "unlabelled", "undefined")


@dataclass(slots=True)
class Lund2013PreparedBenchmark:
    """Prepared Lund2013 rows plus explicit inclusion/exclusion provenance."""

    data: pd.DataFrame
    dataset_card: BenchmarkDatasetCard
    preparation_report: dict[str, Any]


@dataclass(slots=True)
class Lund2013BenchmarkRun:
    """Prepared data, matched-fold comparison, and deterministic benchmark report."""

    prepared: Lund2013PreparedBenchmark
    comparison: EventModelComparison
    report: dict[str, Any]


def _json_safe_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    clean = frame.astype(object).where(pd.notna(frame), None)
    return clean.to_dict(orient="records")


def prepare_lund2013_benchmark(
    root: str | Path,
    *,
    annotator: str = "RA",
    target_sampling_rate_hz: float | None = 60.0,
    min_label_purity: float = 0.75,
    max_interpolation_gap_ms: float | None = None,
    excluded_labels: tuple[str, ...] = _DEFAULT_EXCLUDED_LABELS,
) -> Lund2013PreparedBenchmark:
    """Load Lund2013 and prepare an explicit native- or lower-rate benchmark table.

    The raw benchmark is never modified. When a lower sampling rate is requested, labels are
    transferred with :func:`resample_labeled_gaze`; ambiguous target windows remain auditable and
    are excluded only after their prevalence has been recorded in the preparation report.
    """
    gaze = load_lund2013_directory(root, annotator=annotator)
    source = gaze.data.copy()
    source_rate = float(gaze.sampling_rate_hz)

    resampling: BenchmarkResamplingResult | None = None
    if target_sampling_rate_hz is None or np.isclose(target_sampling_rate_hz, source_rate):
        prepared = source.copy()
        analysis_rate = source_rate
    else:
        resampling = resample_labeled_gaze(
            source,
            target_sampling_rate_hz=float(target_sampling_rate_hz),
            min_label_purity=float(min_label_purity),
            max_interpolation_gap_ms=max_interpolation_gap_ms,
            source_sampling_rate_hz=source_rate,
        )
        prepared = resampling.data.copy()
        analysis_rate = float(target_sampling_rate_hz)

    if "event_label" not in prepared:
        raise SchemaError("Prepared Lund2013 benchmark is missing event_label.")
    labels_before = prepared["event_label"].fillna("MISSING").astype(str)
    excluded = {str(label) for label in excluded_labels}
    retained_mask = ~labels_before.isin(excluded)
    retained = prepared.loc[retained_mask].copy().reset_index(drop=True)
    if retained.empty:
        raise SchemaError("Lund2013 preparation excluded every benchmark row.")
    if retained["event_label"].nunique() < 2:
        raise SchemaError("Lund2013 preparation retained fewer than two event classes.")
    if retained["participant_id"].nunique() < 2:
        raise SchemaError("Lund2013 benchmark requires at least two participants.")

    preparation_report: dict[str, Any] = {
        "dataset": "Lund2013",
        "annotator": annotator,
        "source_sampling_rate_hz": source_rate,
        "analysis_sampling_rate_hz": analysis_rate,
        "source_rows": int(len(source)),
        "prepared_rows_before_exclusions": int(len(prepared)),
        "analysis_rows": int(len(retained)),
        "excluded_rows": int((~retained_mask).sum()),
        "excluded_labels": sorted(excluded),
        "label_counts_before_exclusions": labels_before.value_counts().sort_index().to_dict(),
        "label_counts_analysis": (
            retained["event_label"].astype(str).value_counts().sort_index().to_dict()
        ),
        "participant_count": int(retained["participant_id"].nunique()),
        "trial_count": int(retained["trial_id"].nunique()),
        "resampling": None if resampling is None else resampling.report,
    }
    card = BenchmarkDatasetCard(
        name="Lund2013",
        version="Andersson-et-al-2017-public-repository",
        source="richardandersson/EyeMovementDetectorEvaluation",
        license="GPL-3.0 repository license; raw benchmark is not bundled by GazeForge",
        task="sample-level eye-movement event classification",
        sampling_rates_hz=[source_rate, analysis_rate]
        if not np.isclose(source_rate, analysis_rate)
        else [source_rate],
        participant_count=int(retained["participant_id"].nunique()),
        stimulus_count=int(retained["trial_id"].nunique()),
        split_unit="participant_id",
        validation_scope="external-empirical-benchmark",
        annotation_origin="expert-manual",
        sampling_origin=(
            "native" if np.isclose(source_rate, analysis_rate) else "resampled"
        ),
        reference_strength=(
            "expert-human-reference"
            if np.isclose(source_rate, analysis_rate)
            else "derived-human-reference"
        ),
        human_annotator_count=1,
        reference_description=(
            f"Sample-level eye-movement labels supplied by expert annotator {annotator}; "
            "the public corpus contains paired MN/RA annotations for agreement analysis."
        ),
        notes=[
            f"Human labels from annotator {annotator}.",
            "Ambiguous lower-rate boundary windows are excluded only after prevalence is recorded.",
            "Raw source files remain external to GazeForge.",
        ],
    )
    return Lund2013PreparedBenchmark(
        data=retained,
        dataset_card=card,
        preparation_report=preparation_report,
    )


def compare_lund2013_annotators(
    root: str | Path,
    *,
    left_annotator: str = "MN",
    right_annotator: str = "RA",
    target_sampling_rate_hz: float | None = None,
    min_label_purity: float = 0.75,
) -> dict[str, Any]:
    """Measure the human-human sample-label agreement ceiling for Lund2013."""
    left = load_lund2013_directory(root, annotator=left_annotator)
    right = load_lund2013_directory(root, annotator=right_annotator)
    left_data = left.data
    right_data = right.data
    target = target_sampling_rate_hz
    if target is not None and not np.isclose(target, left.sampling_rate_hz):
        left_data = resample_labeled_gaze(
            left_data,
            target_sampling_rate_hz=float(target),
            min_label_purity=min_label_purity,
            source_sampling_rate_hz=left.sampling_rate_hz,
        ).data
        right_data = resample_labeled_gaze(
            right_data,
            target_sampling_rate_hz=float(target),
            min_label_purity=min_label_purity,
            source_sampling_rate_hz=right.sampling_rate_hz,
        ).data

    overall = sample_label_agreement(left_data, right_data)
    by_stimulus: dict[str, dict[str, Any]] = {}
    if "stimulus_type" in left_data.columns and "stimulus_type" in right_data.columns:
        shared = sorted(
            set(left_data["stimulus_type"].astype(str))
            & set(right_data["stimulus_type"].astype(str))
        )
        for stimulus in shared:
            left_part = left_data.loc[left_data["stimulus_type"].astype(str) == stimulus]
            right_part = right_data.loc[right_data["stimulus_type"].astype(str) == stimulus]
            if not left_part.empty and not right_part.empty:
                by_stimulus[stimulus] = sample_label_agreement(left_part, right_part)
    return {
        "dataset": "Lund2013",
        "left_annotator": left_annotator,
        "right_annotator": right_annotator,
        "sampling_rate_hz": float(target or left.sampling_rate_hz),
        "overall": overall,
        "by_stimulus_type": by_stimulus,
    }


def run_lund2013_event_benchmark(
    root: str | Path,
    *,
    annotator: str = "RA",
    target_sampling_rate_hz: float = 60.0,
    min_label_purity: float = 0.75,
    n_splits: int = 5,
    ivt_velocity_threshold_deg_s: float = 45.0,
    random_state: int = 42,
    n_estimators: int = 200,
    context_radius_ms: float = 50.0,
    hidden_layer_sizes: tuple[int, ...] = (64, 32),
    temporal_solver: str = "adam",
    temporal_max_iter: int = 200,
) -> Lund2013BenchmarkRun:
    """Run matched participant-held-out I-VT/RF/ContextMLP validation on Lund2013."""
    prepared = prepare_lund2013_benchmark(
        root,
        annotator=annotator,
        target_sampling_rate_hz=target_sampling_rate_hz,
        min_label_purity=min_label_purity,
    )
    n_groups = prepared.data["participant_id"].nunique()
    folds = min(int(n_splits), int(n_groups))
    if folds < 2:
        raise SchemaError("At least two participant folds are required for Lund2013 validation.")
    comparison = compare_event_models_grouped(
        prepared.data,
        n_splits=folds,
        sampling_rate_hz=float(prepared.preparation_report["analysis_sampling_rate_hz"]),
        ivt_velocity_threshold_px_s=None,
        ivt_velocity_threshold_deg_s=ivt_velocity_threshold_deg_s,
        random_state=random_state,
        n_estimators=n_estimators,
        context_radius_ms=context_radius_ms,
        hidden_layer_sizes=hidden_layer_sizes,
        temporal_solver=temporal_solver,
        temporal_max_iter=temporal_max_iter,
    )
    metrics = {
        "summary": _json_safe_records(comparison.summary),
        "fold_metrics": _json_safe_records(comparison.fold_metrics),
        "analysis_label_counts": prepared.preparation_report["label_counts_analysis"],
    }
    protocol = {
        "preparation": prepared.preparation_report,
        "comparison_design": comparison.design,
    }
    report = build_benchmark_report(
        benchmark=prepared.dataset_card,
        metrics=metrics,
        model={"models": comparison.design["models"]},
        protocol=protocol,
    )
    return Lund2013BenchmarkRun(
        prepared=prepared,
        comparison=comparison,
        report=report,
    )
