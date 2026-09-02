"""Cross-dataset eye-event benchmark preparation and validation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, recall_score

from .benchmarks import benchmark_fingerprint
from .calibration import evaluate_event_calibration
from .exceptions import SchemaError
from .resampling import resample_labeled_gaze
from .schema import GazeFrame
from .validation import (
    ValidationResult,
    dataset_holdout_context_event_validate,
    dataset_holdout_event_validate,
)


@dataclass(slots=True)
class CrossDatasetEventPrepared:
    """Harmonised lower-rate data plus dataset-level preparation reports."""

    data: pd.DataFrame
    dataset_reports: dict[str, dict[str, Any]]
    design: dict[str, Any]


@dataclass(slots=True)
class CrossDatasetEventValidation:
    """Leave-one-dataset-out results for the two learned GazeForge baselines."""

    random_forest: ValidationResult
    context_mlp: ValidationResult
    summary: pd.DataFrame
    design: dict[str, Any]
    report_fingerprint_sha256: str


def _dataset_identity(name: str, gaze: GazeFrame) -> str:
    data_ids = []
    if "dataset_id" in gaze.data.columns:
        data_ids = sorted(gaze.data["dataset_id"].dropna().astype(str).unique())
    if len(data_ids) > 1:
        raise SchemaError(f"Dataset {name!r} contains multiple dataset_id values: {data_ids}")
    source = str(gaze.metadata.get("source_dataset") or (data_ids[0] if data_ids else name))
    if data_ids and data_ids[0] != source:
        raise SchemaError(
            f"Dataset identity conflict for {name!r}: metadata={source!r}, data={data_ids[0]!r}."
        )
    return source


def _require_resolved_participants(name: str, gaze: GazeFrame) -> None:
    if "participant_id" not in gaze.data.columns:
        raise SchemaError(f"Dataset {name!r} has no participant_id column.")
    values = gaze.data["participant_id"].astype(str).str.strip()
    unresolved = values.isin({"", "__unresolved__", "unknown", "none", "nan"})
    metadata_flag = gaze.metadata.get("participant_identity_resolved")
    if unresolved.any() or metadata_flag is False:
        raise SchemaError(
            f"Dataset {name!r} does not have fully resolved participant identities; "
            "cross-dataset validation is blocked."
        )


def _coordinate_evidence(gaze: GazeFrame) -> tuple[str, bool, str]:
    unit = str(gaze.metadata.get("coordinate_source_unit", "unverified"))
    verified = gaze.metadata.get("coordinate_unit_verified") is True
    basis = "dataset metadata"
    source = str(gaze.metadata.get("source_dataset", ""))
    if not verified and source == "Lund2013":
        unit = "pixels"
        verified = True
        basis = "Lund2013 adapter/source convention"
    return unit, verified, basis


def _require_verified_coordinates(name: str, gaze: GazeFrame) -> None:
    _, verified, _ = _coordinate_evidence(gaze)
    if not verified:
        raise SchemaError(
            f"Dataset {name!r} does not have a verified coordinate unit; "
            "unit-sensitive cross-dataset kinematic modelling is blocked."
        )


def _normalise_label(value: Any) -> str:
    return str(value).strip().lower().replace("smooth_pursuit", "pursuit")


def prepare_cross_dataset_event_benchmark(
    datasets: Mapping[str, GazeFrame],
    *,
    target_sampling_rate_hz: float = 60.0,
    common_labels: Sequence[str] = ("fixation", "saccade", "pursuit"),
    min_label_purity: float = 0.75,
    ambiguous_label: str = "ambiguous",
    require_resolved_participants: bool = True,
    require_verified_coordinates: bool = True,
    require_all_common_labels: bool = True,
) -> CrossDatasetEventPrepared:
    """Prepare multiple human-reference corpora for matched lower-rate validation.

    Each source is independently resampled to the requested rate using the benchmark resampling
    guardrails. Participant and trial identifiers are namespaced by dataset after source identities
    have been checked, preventing accidental collisions across independently collected corpora.
    """
    if len(datasets) < 2:
        raise ValueError("At least two datasets are required for cross-dataset validation.")
    target_rate = float(target_sampling_rate_hz)
    if not np.isfinite(target_rate) or target_rate <= 0:
        raise ValueError("target_sampling_rate_hz must be finite and positive.")
    labels = tuple(dict.fromkeys(_normalise_label(label) for label in common_labels))
    if len(labels) < 2:
        raise ValueError("common_labels must contain at least two distinct labels.")

    output_parts: list[pd.DataFrame] = []
    reports: dict[str, dict[str, Any]] = {}
    dataset_ids_seen: set[str] = set()

    for name, gaze in datasets.items():
        if not isinstance(gaze, GazeFrame):
            raise TypeError(f"Dataset {name!r} must be a GazeFrame.")
        dataset_id = _dataset_identity(str(name), gaze)
        if dataset_id in dataset_ids_seen:
            raise SchemaError(f"Duplicate dataset identity in cross-dataset input: {dataset_id!r}")
        dataset_ids_seen.add(dataset_id)
        if require_resolved_participants:
            _require_resolved_participants(dataset_id, gaze)
        if require_verified_coordinates:
            _require_verified_coordinates(dataset_id, gaze)
        if "event_label" not in gaze.data.columns:
            raise SchemaError(f"Dataset {dataset_id!r} has no event_label column.")

        coordinate_unit, coordinate_verified, coordinate_basis = _coordinate_evidence(gaze)
        source = gaze.data.copy()
        source["event_label"] = source["event_label"].map(_normalise_label)
        source["dataset_id"] = dataset_id
        source["coordinate_unit"] = coordinate_unit
        source["coordinate_unit_verified"] = coordinate_verified

        if target_rate < float(gaze.sampling_rate_hz):
            sampled_result = resample_labeled_gaze(
                source,
                target_sampling_rate_hz=target_rate,
                source_sampling_rate_hz=float(gaze.sampling_rate_hz),
                label_col="event_label",
                min_label_purity=float(min_label_purity),
                ambiguous_label=ambiguous_label,
                carry_cols=(
                    "annotator",
                    "stimulus_type",
                    "dataset_id",
                    "source_file",
                    "coordinate_unit",
                    "coordinate_unit_verified",
                    "screen_width_px",
                    "screen_height_px",
                    "screen_width_physical",
                    "screen_height_physical",
                    "view_distance_physical",
                ),
            )
            sampled = sampled_result.data
            resampling_report = sampled_result.report
            sampling_origin = "resampled"
        elif np.isclose(target_rate, float(gaze.sampling_rate_hz), rtol=0.0, atol=1e-9):
            sampled = source.copy()
            sampled["benchmark_label_ambiguous"] = False
            sampled["benchmark_label_purity"] = 1.0
            sampled["source_sampling_rate_hz"] = float(gaze.sampling_rate_hz)
            sampled["target_sampling_rate_hz"] = target_rate
            resampling_report = {
                "method": "native_no_resampling",
                "source_sampling_rate_hz": float(gaze.sampling_rate_hz),
                "target_sampling_rate_hz": target_rate,
                "source_rows": int(len(source)),
                "target_rows": int(len(sampled)),
                "ambiguous_rows": 0,
                "ambiguous_fraction": 0.0,
            }
            sampling_origin = "native"
        else:
            raise ValueError(
                f"Dataset {dataset_id!r} is sampled at {gaze.sampling_rate_hz:g} Hz, below the "
                f"requested target {target_rate:g} Hz; benchmark preparation will not upsample."
            )

        before_filter = len(sampled)
        sampled["event_label"] = sampled["event_label"].map(_normalise_label)
        sampled = sampled.loc[sampled["event_label"].isin(labels)].copy()
        available_labels = sorted(sampled["event_label"].unique())
        missing_labels = sorted(set(labels) - set(available_labels))
        if require_all_common_labels and missing_labels:
            raise SchemaError(
                f"Dataset {dataset_id!r} is missing required common labels after harmonisation: "
                f"{missing_labels}"
            )
        if sampled.empty:
            raise SchemaError(f"Dataset {dataset_id!r} has no rows after label harmonisation.")

        sampled["source_participant_id"] = sampled["participant_id"].astype(str)
        sampled["source_trial_id"] = sampled["trial_id"].astype(str)
        sampled["participant_id"] = dataset_id + "::" + sampled["source_participant_id"]
        sampled["trial_id"] = dataset_id + "::" + sampled["source_trial_id"]
        sampled["dataset_id"] = dataset_id
        output_parts.append(sampled)

        reports[dataset_id] = {
            "source_sampling_rate_hz": float(gaze.sampling_rate_hz),
            "target_sampling_rate_hz": target_rate,
            "sampling_origin_at_analysis": sampling_origin,
            "coordinate_source_unit": coordinate_unit,
            "coordinate_unit_verified": coordinate_verified,
            "coordinate_verification_basis": coordinate_basis,
            "participant_identity_resolved": not sampled["source_participant_id"].isin(
                {"__unresolved__", "unknown"}
            ).any(),
            "rows_before_common_label_filter": int(before_filter),
            "rows_after_common_label_filter": int(len(sampled)),
            "common_labels_present": available_labels,
            "resampling": resampling_report,
        }

    combined = pd.concat(output_parts, ignore_index=True)
    design = {
        "design": "harmonised_cross_dataset_event_benchmark",
        "dataset_ids": sorted(reports),
        "target_sampling_rate_hz": target_rate,
        "common_labels": list(labels),
        "min_label_purity": float(min_label_purity),
        "ambiguous_label": ambiguous_label,
        "require_resolved_participants": bool(require_resolved_participants),
        "require_verified_coordinates": bool(require_verified_coordinates),
        "require_all_common_labels": bool(require_all_common_labels),
        "participant_namespace_policy": "dataset_id::source_participant_id",
        "trial_namespace_policy": "dataset_id::source_trial_id",
    }
    return CrossDatasetEventPrepared(data=combined, dataset_reports=reports, design=design)


def _validation_summary(
    model_name: str,
    result: ValidationResult,
    *,
    label_col: str,
    calibration_bins: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for held_out, part in result.predictions.groupby("held_out_dataset", sort=True):
        truth = part[label_col].astype(str).to_numpy()
        pred = part["predicted_event"].astype(str).to_numpy()
        row: dict[str, Any] = {
            "model": model_name,
            "held_out_dataset": str(held_out),
            "n_test_rows": int(len(part)),
            "accuracy": float(accuracy_score(truth, pred)),
            "balanced_accuracy": float(
                recall_score(
                    truth,
                    pred,
                    labels=sorted(set(truth)),
                    average="macro",
                    zero_division=0,
                )
            ),
            "macro_f1": float(f1_score(truth, pred, average="macro", zero_division=0)),
            "multiclass_brier_score": np.nan,
            "expected_calibration_error": np.nan,
        }
        if any(column.startswith("p_event_") for column in part.columns):
            calibration = evaluate_event_calibration(
                part,
                true_label_col=label_col,
                n_bins=int(calibration_bins),
            )
            row["multiclass_brier_score"] = float(calibration["multiclass_brier_score"])
            row["expected_calibration_error"] = float(
                calibration["expected_calibration_error"]
            )
        rows.append(row)
    return rows


def run_cross_dataset_event_validation(
    prepared: CrossDatasetEventPrepared,
    *,
    label_col: str = "event_label",
    min_confidence: float = 0.0,
    random_state: int = 42,
    n_estimators: int = 200,
    context_radius_ms: float = 50.0,
    rolling_window_ms: float = 80.0,
    hidden_layer_sizes: tuple[int, ...] = (64, 32),
    temporal_solver: str = "adam",
    temporal_max_iter: int = 200,
    calibration_bins: int = 10,
) -> CrossDatasetEventValidation:
    """Run RF and temporal-context MLP in a leave-one-dataset-out design."""
    if not isinstance(prepared, CrossDatasetEventPrepared):
        raise TypeError("prepared must be a CrossDatasetEventPrepared instance.")
    data = prepared.data.copy()
    if data["dataset_id"].nunique() < 2:
        raise ValueError("At least two datasets are required for validation.")
    if calibration_bins < 2:
        raise ValueError("calibration_bins must be at least 2.")
    target_rate = float(prepared.design["target_sampling_rate_hz"])

    rf = dataset_holdout_event_validate(
        data,
        dataset_col="dataset_id",
        participant_col="participant_id",
        label_col=label_col,
        sampling_rate_hz=target_rate,
        min_confidence=min_confidence,
        random_state=random_state,
        n_estimators=n_estimators,
        require_disjoint_participants=True,
    )
    context = dataset_holdout_context_event_validate(
        data,
        dataset_col="dataset_id",
        participant_col="participant_id",
        label_col=label_col,
        sampling_rate_hz=target_rate,
        min_confidence=min_confidence,
        random_state=random_state,
        context_radius_ms=context_radius_ms,
        rolling_window_ms=rolling_window_ms,
        hidden_layer_sizes=hidden_layer_sizes,
        solver=temporal_solver,
        max_iter=temporal_max_iter,
        require_disjoint_participants=True,
    )
    summary = pd.DataFrame(
        _validation_summary(
            "RandomForest",
            rf,
            label_col=label_col,
            calibration_bins=calibration_bins,
        )
        + _validation_summary(
            "ContextMLP",
            context,
            label_col=label_col,
            calibration_bins=calibration_bins,
        )
    ).sort_values(["model", "held_out_dataset"], kind="stable").reset_index(drop=True)
    design = {
        **prepared.design,
        "validation_design": "leave_one_dataset_out",
        "models": ["RandomForest", "ContextMLP"],
        "random_state": int(random_state),
        "context_radius_ms": float(context_radius_ms),
        "rolling_window_ms": float(rolling_window_ms),
        "calibration_bins": int(calibration_bins),
    }
    fingerprint_payload = {
        "design": design,
        "dataset_reports": prepared.dataset_reports,
        "summary": summary.to_dict(orient="records"),
    }
    return CrossDatasetEventValidation(
        random_forest=rf,
        context_mlp=context,
        summary=summary,
        design=design,
        report_fingerprint_sha256=benchmark_fingerprint(fingerprint_payload),
    )
