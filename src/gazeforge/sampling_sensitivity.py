"""Sampling-rate and annotation-boundary sensitivity for labelled gaze benchmarks."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .benchmarks import benchmark_fingerprint
from .comparison import compare_event_models_grouped
from .exceptions import SchemaError
from .resampling import resample_labeled_gaze
from .schema import infer_sampling_rate_hz

_DEFAULT_EXCLUDED_LABELS = ("ambiguous", "unlabelled", "undefined")


@dataclass(slots=True)
class SamplingSensitivityResult:
    """Complete settings ledger and model metrics for a resampling sensitivity surface."""

    settings: pd.DataFrame
    model_metrics: pd.DataFrame
    design: dict[str, Any]
    report_fingerprint_sha256: str


def _normalise_unique(
    values: Sequence[float],
    *,
    name: str,
    descending: bool,
) -> tuple[float, ...]:
    if len(values) == 0:
        raise ValueError(f"{name} cannot be empty.")
    cleaned: list[float] = []
    for value in values:
        numeric = float(value)
        if not np.isfinite(numeric):
            raise ValueError(f"{name} values must be finite.")
        cleaned.append(numeric)
    return tuple(sorted(set(cleaned), reverse=descending))


def _setting_key(target_rate_hz: float, purity: float) -> str:
    return f"rate={target_rate_hz:g}|purity={purity:.6g}"


def evaluate_sampling_purity_sensitivity(
    data: pd.DataFrame,
    *,
    target_sampling_rates_hz: Sequence[float] = (120.0, 90.0, 60.0, 30.0),
    min_label_purities: Sequence[float] = (0.60, 0.75, 0.90),
    source_sampling_rate_hz: float | None = None,
    label_col: str = "event_label",
    group_col: str = "participant_id",
    resampling_group_cols: tuple[str, ...] = ("participant_id", "trial_id"),
    ambiguous_label: str = "ambiguous",
    excluded_labels: tuple[str, ...] = _DEFAULT_EXCLUDED_LABELS,
    n_splits: int = 5,
    ivt_velocity_threshold_px_s: float | None = 1000.0,
    ivt_velocity_threshold_deg_s: float | None = None,
    min_confidence: float = 0.0,
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
) -> SamplingSensitivityResult:
    """Evaluate model sensitivity to target sampling rate and boundary-label purity.

    Every rate/purity condition is retained in ``settings``. Ambiguous and other excluded labels
    are removed only after their prevalence has been recorded, matching the primary Lund benchmark
    policy. Conditions that no longer contain enough groups or labels for the requested validation
    design are recorded as ``not_evaluable`` instead of being silently dropped.
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError("data must be a pandas DataFrame.")
    required = [label_col, group_col, *resampling_group_cols]
    missing = [column for column in dict.fromkeys(required) if column not in data.columns]
    if missing:
        raise SchemaError(f"Sampling sensitivity is missing required columns: {missing}")
    if n_splits < 2:
        raise ValueError("n_splits must be at least 2.")

    source_rate = (
        float(source_sampling_rate_hz)
        if source_sampling_rate_hz is not None
        else infer_sampling_rate_hz(data, group_cols=resampling_group_cols)
    )
    if not np.isfinite(source_rate) or source_rate <= 0:
        raise ValueError("source_sampling_rate_hz must be finite and positive.")

    target_rates = _normalise_unique(
        target_sampling_rates_hz,
        name="target_sampling_rates_hz",
        descending=True,
    )
    purities = _normalise_unique(
        min_label_purities,
        name="min_label_purities",
        descending=False,
    )
    invalid_rates = [rate for rate in target_rates if rate <= 0 or rate >= source_rate]
    if invalid_rates:
        raise ValueError(
            "Every target sampling rate must be positive and lower than the source rate; "
            f"invalid values: {invalid_rates}"
        )
    invalid_purities = [purity for purity in purities if not 0.0 < purity <= 1.0]
    if invalid_purities:
        raise ValueError(
            "Every min_label_purity must be in (0, 1]; "
            f"invalid values: {invalid_purities}"
        )
    excluded = {str(label) for label in excluded_labels}
    excluded.add(str(ambiguous_label))

    setting_rows: list[dict[str, Any]] = []
    model_rows: list[dict[str, Any]] = []
    source_rows = int(len(data))

    for target_rate in target_rates:
        for purity in purities:
            setting_key = _setting_key(target_rate, purity)
            resampled = resample_labeled_gaze(
                data,
                target_sampling_rate_hz=target_rate,
                label_col=label_col,
                group_cols=resampling_group_cols,
                min_label_purity=purity,
                ambiguous_label=ambiguous_label,
                max_interpolation_gap_ms=max_interpolation_gap_ms,
                source_sampling_rate_hz=source_rate,
            )
            sampled = resampled.data
            labels = sampled[label_col].fillna("MISSING").astype(str)
            retained_mask = ~labels.isin(excluded)
            retained = sampled.loc[retained_mask].copy()
            n_target_rows = int(len(sampled))
            n_retained_rows = int(len(retained))
            n_groups = int(retained[group_col].astype(str).nunique()) if n_retained_rows else 0
            n_labels = int(retained[label_col].astype(str).nunique()) if n_retained_rows else 0

            status = "ok"
            reason = ""
            if n_retained_rows == 0:
                status = "not_evaluable"
                reason = "no_rows_after_label_exclusions"
            elif n_groups < n_splits:
                status = "not_evaluable"
                reason = "insufficient_groups_for_requested_splits"
            elif n_labels < 2:
                status = "not_evaluable"
                reason = "fewer_than_two_event_labels_after_filtering"

            setting_rows.append(
                {
                    "setting_key": setting_key,
                    "source_sampling_rate_hz": source_rate,
                    "target_sampling_rate_hz": target_rate,
                    "min_label_purity": purity,
                    "source_rows": source_rows,
                    "target_rows": n_target_rows,
                    "ambiguous_rows": int(resampled.report["ambiguous_rows"]),
                    "ambiguous_fraction": float(resampled.report["ambiguous_fraction"]),
                    "mean_label_purity": float(resampled.report["mean_label_purity"]),
                    "excluded_rows_after_resampling": int((~retained_mask).sum()),
                    "retained_rows": n_retained_rows,
                    "retained_fraction_of_target": (
                        float(n_retained_rows / n_target_rows) if n_target_rows else 0.0
                    ),
                    "retained_group_count": n_groups,
                    "retained_label_count": n_labels,
                    "comparison_status": status,
                    "comparison_reason": reason,
                }
            )
            if status != "ok":
                continue

            comparison = compare_event_models_grouped(
                retained,
                label_col=label_col,
                group_col=group_col,
                n_splits=n_splits,
                sampling_rate_hz=target_rate,
                ivt_velocity_threshold_px_s=ivt_velocity_threshold_px_s,
                ivt_velocity_threshold_deg_s=ivt_velocity_threshold_deg_s,
                min_confidence=min_confidence,
                random_state=random_state,
                n_estimators=n_estimators,
                context_radius_ms=context_radius_ms,
                rolling_window_ms=rolling_window_ms,
                hidden_layer_sizes=hidden_layer_sizes,
                temporal_solver=temporal_solver,
                temporal_max_iter=temporal_max_iter,
                calibration_bins=calibration_bins,
                include_event_level_metrics=True,
                event_group_cols=resampling_group_cols,
                event_min_iou=event_min_iou,
                event_excluded_labels=tuple(sorted(excluded)),
            )
            for row in comparison.summary.to_dict(orient="records"):
                model_rows.append(
                    {
                        "setting_key": setting_key,
                        "source_sampling_rate_hz": source_rate,
                        "target_sampling_rate_hz": target_rate,
                        "min_label_purity": purity,
                        "ambiguous_fraction": float(resampled.report["ambiguous_fraction"]),
                        "retained_fraction_of_target": (
                            float(n_retained_rows / n_target_rows) if n_target_rows else 0.0
                        ),
                        **row,
                    }
                )

    settings = pd.DataFrame(setting_rows).sort_values(
        ["target_sampling_rate_hz", "min_label_purity"],
        ascending=[False, True],
        kind="stable",
    ).reset_index(drop=True)
    model_metrics = pd.DataFrame(model_rows)
    if not model_metrics.empty:
        model_metrics = model_metrics.sort_values(
            ["target_sampling_rate_hz", "min_label_purity", "model"],
            ascending=[False, True, True],
            kind="stable",
        ).reset_index(drop=True)

    design = {
        "design": "sampling_rate_by_label_purity_sensitivity",
        "source_sampling_rate_hz": source_rate,
        "target_sampling_rates_hz": list(target_rates),
        "min_label_purities": list(purities),
        "label_col": label_col,
        "group_col": group_col,
        "resampling_group_cols": list(resampling_group_cols),
        "ambiguous_label": ambiguous_label,
        "excluded_labels": sorted(excluded),
        "excluded_rows_used_for_modelling": False,
        "n_splits": int(n_splits),
        "event_min_iou": float(event_min_iou),
        "random_state": int(random_state),
        "max_interpolation_gap_ms": max_interpolation_gap_ms,
    }
    fingerprint_body = {
        "design": design,
        "settings": settings.to_dict(orient="records"),
        "model_metrics": model_metrics.to_dict(orient="records"),
    }
    return SamplingSensitivityResult(
        settings=settings,
        model_metrics=model_metrics,
        design=design,
        report_fingerprint_sha256=benchmark_fingerprint(fingerprint_body),
    )
