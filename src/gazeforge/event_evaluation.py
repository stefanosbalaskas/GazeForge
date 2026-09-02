"""Event-level eye-movement segmentation and temporal matching metrics."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment

from .exceptions import SchemaError

_DEFAULT_EXCLUDED_LABELS = ("ambiguous", "unlabelled", "undefined")


@dataclass(slots=True)
class EventLevelEvaluation:
    """Event intervals, one-to-one matches, and aggregate/per-class metrics."""

    reference_events: pd.DataFrame
    predicted_events: pd.DataFrame
    matches: pd.DataFrame
    per_class: pd.DataFrame
    summary: dict[str, Any]
    design: dict[str, Any]


def _normalise_label(value: Any) -> str:
    if value is None or pd.isna(value):
        return "unlabelled"
    return str(value).strip().lower()


def _validate_rate(sampling_rate_hz: float) -> tuple[float, float]:
    rate = float(sampling_rate_hz)
    if not np.isfinite(rate) or rate <= 0:
        raise ValueError("sampling_rate_hz must be finite and positive.")
    return rate, 1000.0 / rate


def samples_to_event_intervals(
    data: pd.DataFrame,
    *,
    label_col: str = "event_label",
    timestamp_col: str = "timestamp_ms",
    group_cols: Sequence[str] = ("participant_id", "trial_id"),
    sampling_rate_hz: float,
    excluded_labels: Sequence[str] = _DEFAULT_EXCLUDED_LABELS,
    max_gap_factor: float = 1.5,
) -> pd.DataFrame:
    """Convert sample labels to contiguous half-open event intervals.

    Segmentation occurs before excluded labels are removed, so an ambiguous/undefined run remains a
    hard separator between two otherwise identical event labels. A timestamp gap larger than
    ``max_gap_factor`` nominal sample periods also starts a new event.
    """
    if not group_cols:
        raise ValueError("group_cols must contain at least one grouping column.")
    required = [*group_cols, timestamp_col, label_col]
    missing = [column for column in required if column not in data.columns]
    if missing:
        raise SchemaError(f"Event segmentation requires columns: {missing}")
    if data[list(group_cols)].isna().any().any():
        raise SchemaError("Event segmentation group identifiers cannot be missing.")
    _, sample_period_ms = _validate_rate(sampling_rate_hz)
    gap_factor = float(max_gap_factor)
    if not np.isfinite(gap_factor) or gap_factor < 1.0:
        raise ValueError("max_gap_factor must be finite and at least 1.0.")
    excluded = {_normalise_label(label) for label in excluded_labels}

    rows: list[dict[str, Any]] = []
    for group_key, part in data.groupby(list(group_cols), sort=False, dropna=False):
        keys = group_key if isinstance(group_key, tuple) else (group_key,)
        timestamps = pd.to_numeric(part[timestamp_col], errors="coerce").to_numpy(dtype=float)
        if not np.all(np.isfinite(timestamps)):
            raise SchemaError("Event segmentation timestamps must be finite.")
        if len(timestamps) > 1 and np.any(np.diff(timestamps) <= 0):
            raise SchemaError(
                "Event segmentation requires strictly increasing timestamps within every group."
            )
        labels = part[label_col].map(_normalise_label).to_numpy(dtype=object)
        if not len(labels):
            continue

        event_index = 0
        run_start = 0
        for position in range(1, len(part) + 1):
            at_end = position == len(part)
            if not at_end:
                label_changed = labels[position] != labels[position - 1]
                gap_ms = timestamps[position] - timestamps[position - 1]
                gap_break = gap_ms > gap_factor * sample_period_ms
            else:
                label_changed = True
                gap_break = False
            if not (label_changed or gap_break):
                continue

            run_end = position - 1
            label = str(labels[run_start])
            if label not in excluded:
                event_index += 1
                row = {column: value for column, value in zip(group_cols, keys, strict=True)}
                start_ms = float(timestamps[run_start])
                end_ms = float(timestamps[run_end] + sample_period_ms)
                row.update(
                    {
                        "event_index": event_index,
                        "event_label": label,
                        "start_ms": start_ms,
                        "end_ms": end_ms,
                        "duration_ms": end_ms - start_ms,
                        "n_samples": int(run_end - run_start + 1),
                    }
                )
                rows.append(row)
            run_start = position

    columns = [
        *group_cols,
        "event_index",
        "event_label",
        "start_ms",
        "end_ms",
        "duration_ms",
        "n_samples",
    ]
    return pd.DataFrame(rows, columns=columns)


def temporal_event_iou(
    predicted_start_ms: float,
    predicted_end_ms: float,
    reference_start_ms: float,
    reference_end_ms: float,
) -> float:
    """Return temporal intersection-over-union for two half-open event intervals."""
    values = np.asarray(
        [predicted_start_ms, predicted_end_ms, reference_start_ms, reference_end_ms],
        dtype=float,
    )
    if not np.all(np.isfinite(values)):
        raise ValueError("Event interval bounds must be finite.")
    p_start, p_end, r_start, r_end = values
    if p_end <= p_start or r_end <= r_start:
        raise ValueError("Event interval end must be greater than start.")
    overlap = max(0.0, min(p_end, r_end) - max(p_start, r_start))
    union = (p_end - p_start) + (r_end - r_start) - overlap
    return 0.0 if union <= 0 else float(overlap / union)


def _validate_event_frame(
    frame: pd.DataFrame,
    *,
    name: str,
    group_cols: Sequence[str],
    label_col: str,
) -> None:
    required = [*group_cols, "event_index", label_col, "start_ms", "end_ms", "duration_ms"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise SchemaError(f"{name} event intervals are missing columns: {missing}")
    if frame[list(group_cols)].isna().any().any():
        raise SchemaError(f"{name} event interval group identifiers cannot be missing.")
    if frame.duplicated([*group_cols, "event_index"]).any():
        raise SchemaError(f"{name} event intervals contain duplicate event keys.")
    if len(frame):
        start = pd.to_numeric(frame["start_ms"], errors="coerce").to_numpy(dtype=float)
        end = pd.to_numeric(frame["end_ms"], errors="coerce").to_numpy(dtype=float)
        if not np.all(np.isfinite(start)) or not np.all(np.isfinite(end)):
            raise SchemaError(f"{name} event interval bounds must be finite.")
        if np.any(end <= start):
            raise SchemaError(f"{name} event intervals must have end_ms > start_ms.")
        for _, part in frame.groupby(list(group_cols), sort=False, dropna=False):
            ordered = part.sort_values("start_ms", kind="stable")
            starts = ordered["start_ms"].to_numpy(dtype=float)
            ends = ordered["end_ms"].to_numpy(dtype=float)
            if len(starts) > 1 and np.any(starts[1:] < ends[:-1] - 1e-9):
                raise SchemaError(f"{name} event intervals cannot overlap within a group.")


def match_event_intervals(
    predicted: pd.DataFrame,
    reference: pd.DataFrame,
    *,
    group_cols: Sequence[str] = ("participant_id", "trial_id"),
    label_col: str = "event_label",
    min_iou: float = 0.50,
    require_label_match: bool = True,
) -> pd.DataFrame:
    """One-to-one match predicted events to references within each participant/trial group."""
    if not 0.0 <= float(min_iou) <= 1.0:
        raise ValueError("min_iou must be in [0, 1].")
    _validate_event_frame(predicted, name="predicted", group_cols=group_cols, label_col=label_col)
    _validate_event_frame(reference, name="reference", group_cols=group_cols, label_col=label_col)

    match_rows: list[dict[str, Any]] = []
    pred_groups = {
        key if isinstance(key, tuple) else (key,): part
        for key, part in predicted.groupby(list(group_cols), sort=False, dropna=False)
    }
    ref_groups = {
        key if isinstance(key, tuple) else (key,): part
        for key, part in reference.groupby(list(group_cols), sort=False, dropna=False)
    }
    group_keys = list(dict.fromkeys([*ref_groups.keys(), *pred_groups.keys()]))

    for key in group_keys:
        pred = pred_groups.get(key, predicted.iloc[0:0]).reset_index(drop=True)
        ref = ref_groups.get(key, reference.iloc[0:0]).reset_index(drop=True)
        matched_pred: set[int] = set()
        matched_ref: set[int] = set()
        if len(pred) and len(ref):
            ious = np.zeros((len(pred), len(ref)), dtype=float)
            for i, p_row in pred.iterrows():
                for j, r_row in ref.iterrows():
                    if require_label_match and str(p_row[label_col]) != str(r_row[label_col]):
                        continue
                    ious[i, j] = temporal_event_iou(
                        p_row["start_ms"],
                        p_row["end_ms"],
                        r_row["start_ms"],
                        r_row["end_ms"],
                    )
            pred_idx, ref_idx = linear_sum_assignment(1.0 - ious)
            for i, j in zip(pred_idx, ref_idx, strict=True):
                iou = float(ious[i, j])
                if iou <= 0.0 or iou < float(min_iou):
                    continue
                p_row = pred.iloc[int(i)]
                r_row = ref.iloc[int(j)]
                matched_pred.add(int(i))
                matched_ref.add(int(j))
                row = {column: value for column, value in zip(group_cols, key, strict=True)}
                onset_error = float(p_row["start_ms"] - r_row["start_ms"])
                offset_error = float(p_row["end_ms"] - r_row["end_ms"])
                duration_error = float(p_row["duration_ms"] - r_row["duration_ms"])
                row.update(
                    {
                        "predicted_event_index": int(p_row["event_index"]),
                        "reference_event_index": int(r_row["event_index"]),
                        "predicted_label": str(p_row[label_col]),
                        "reference_label": str(r_row[label_col]),
                        "label_match": str(p_row[label_col]) == str(r_row[label_col]),
                        "iou": iou,
                        "onset_error_ms": onset_error,
                        "offset_error_ms": offset_error,
                        "duration_error_ms": duration_error,
                        "status": "matched",
                    }
                )
                match_rows.append(row)

        for i, p_row in pred.iterrows():
            if int(i) in matched_pred:
                continue
            row = {column: value for column, value in zip(group_cols, key, strict=True)}
            row.update(
                {
                    "predicted_event_index": int(p_row["event_index"]),
                    "reference_event_index": None,
                    "predicted_label": str(p_row[label_col]),
                    "reference_label": None,
                    "label_match": False,
                    "iou": 0.0,
                    "onset_error_ms": np.nan,
                    "offset_error_ms": np.nan,
                    "duration_error_ms": np.nan,
                    "status": "false_positive",
                }
            )
            match_rows.append(row)
        for j, r_row in ref.iterrows():
            if int(j) in matched_ref:
                continue
            row = {column: value for column, value in zip(group_cols, key, strict=True)}
            row.update(
                {
                    "predicted_event_index": None,
                    "reference_event_index": int(r_row["event_index"]),
                    "predicted_label": None,
                    "reference_label": str(r_row[label_col]),
                    "label_match": False,
                    "iou": 0.0,
                    "onset_error_ms": np.nan,
                    "offset_error_ms": np.nan,
                    "duration_error_ms": np.nan,
                    "status": "false_negative",
                }
            )
            match_rows.append(row)

    columns = [
        *group_cols,
        "predicted_event_index",
        "reference_event_index",
        "predicted_label",
        "reference_label",
        "label_match",
        "iou",
        "onset_error_ms",
        "offset_error_ms",
        "duration_error_ms",
        "status",
    ]
    return pd.DataFrame(match_rows, columns=columns)


def _precision_recall_f1(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    f1 = 2.0 * precision * recall / (precision + recall) if precision + recall else 0.0
    return float(precision), float(recall), float(f1)


def _matched_error_metrics(matches: pd.DataFrame) -> dict[str, float]:
    matched = matches.loc[matches["status"] == "matched"] if len(matches) else matches
    if matched.empty:
        return {
            "mean_matched_iou": 0.0,
            "mean_abs_onset_error_ms": np.nan,
            "mean_abs_offset_error_ms": np.nan,
            "mean_abs_duration_error_ms": np.nan,
        }
    return {
        "mean_matched_iou": float(matched["iou"].mean()),
        "mean_abs_onset_error_ms": float(matched["onset_error_ms"].abs().mean()),
        "mean_abs_offset_error_ms": float(matched["offset_error_ms"].abs().mean()),
        "mean_abs_duration_error_ms": float(matched["duration_error_ms"].abs().mean()),
    }


def evaluate_event_intervals(
    predicted: pd.DataFrame,
    reference: pd.DataFrame,
    *,
    group_cols: Sequence[str] = ("participant_id", "trial_id"),
    label_col: str = "event_label",
    min_iou: float = 0.50,
    require_label_match: bool = True,
) -> EventLevelEvaluation:
    """Evaluate event detection/classification with one-to-one temporal matching."""
    matches = match_event_intervals(
        predicted,
        reference,
        group_cols=group_cols,
        label_col=label_col,
        min_iou=min_iou,
        require_label_match=require_label_match,
    )
    status = matches["status"] if len(matches) else pd.Series(dtype=str)
    tp = int((status == "matched").sum())
    fp = int((status == "false_positive").sum())
    fn = int((status == "false_negative").sum())
    precision, recall, f1 = _precision_recall_f1(tp, fp, fn)
    summary = {
        "n_predicted_events": int(len(predicted)),
        "n_reference_events": int(len(reference)),
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        **_matched_error_metrics(matches),
    }

    labels = sorted(
        set(predicted[label_col].astype(str)).union(reference[label_col].astype(str))
    )
    class_rows: list[dict[str, Any]] = []
    for label in labels:
        matched_same = matches.loc[
            (matches["status"] == "matched")
            & (matches["predicted_label"] == label)
            & (matches["reference_label"] == label)
        ]
        matched_pred_wrong = matches.loc[
            (matches["status"] == "matched")
            & (matches["predicted_label"] == label)
            & (matches["reference_label"] != label)
        ]
        matched_ref_wrong = matches.loc[
            (matches["status"] == "matched")
            & (matches["reference_label"] == label)
            & (matches["predicted_label"] != label)
        ]
        class_fp = int(
            ((matches["status"] == "false_positive") & (matches["predicted_label"] == label)).sum()
            + len(matched_pred_wrong)
        )
        class_fn = int(
            ((matches["status"] == "false_negative") & (matches["reference_label"] == label)).sum()
            + len(matched_ref_wrong)
        )
        class_tp = int(len(matched_same))
        class_precision, class_recall, class_f1 = _precision_recall_f1(
            class_tp,
            class_fp,
            class_fn,
        )
        errors = _matched_error_metrics(matched_same)
        class_rows.append(
            {
                "event_label": label,
                "n_predicted_events": int((predicted[label_col].astype(str) == label).sum()),
                "n_reference_events": int((reference[label_col].astype(str) == label).sum()),
                "true_positive": class_tp,
                "false_positive": class_fp,
                "false_negative": class_fn,
                "precision": class_precision,
                "recall": class_recall,
                "f1": class_f1,
                **errors,
            }
        )

    design = {
        "matching": "one_to_one_hungarian_temporal_iou",
        "group_cols": list(group_cols),
        "min_iou": float(min_iou),
        "require_label_match": bool(require_label_match),
        "interval_convention": "half_open_[start,end)",
    }
    return EventLevelEvaluation(
        reference_events=reference.copy(),
        predicted_events=predicted.copy(),
        matches=matches,
        per_class=pd.DataFrame(class_rows),
        summary=summary,
        design=design,
    )


def evaluate_sample_event_predictions(
    data: pd.DataFrame,
    *,
    true_label_col: str = "event_label",
    predicted_label_col: str = "predicted_event",
    timestamp_col: str = "timestamp_ms",
    group_cols: Sequence[str] = ("participant_id", "trial_id"),
    sampling_rate_hz: float,
    excluded_labels: Sequence[str] = _DEFAULT_EXCLUDED_LABELS,
    max_gap_factor: float = 1.5,
    min_iou: float = 0.50,
    require_label_match: bool = True,
) -> EventLevelEvaluation:
    """Segment sample-level truth/predictions and evaluate them at event level."""
    for column in (true_label_col, predicted_label_col):
        if column not in data.columns:
            raise SchemaError(f"Missing event-evaluation label column: {column!r}")
    reference_input = data.rename(columns={true_label_col: "__event_reference_label"})
    predicted_input = data.rename(columns={predicted_label_col: "__event_predicted_label"})
    reference = samples_to_event_intervals(
        reference_input,
        label_col="__event_reference_label",
        timestamp_col=timestamp_col,
        group_cols=group_cols,
        sampling_rate_hz=sampling_rate_hz,
        excluded_labels=excluded_labels,
        max_gap_factor=max_gap_factor,
    )
    predicted = samples_to_event_intervals(
        predicted_input,
        label_col="__event_predicted_label",
        timestamp_col=timestamp_col,
        group_cols=group_cols,
        sampling_rate_hz=sampling_rate_hz,
        excluded_labels=excluded_labels,
        max_gap_factor=max_gap_factor,
    )
    result = evaluate_event_intervals(
        predicted,
        reference,
        group_cols=group_cols,
        label_col="event_label",
        min_iou=min_iou,
        require_label_match=require_label_match,
    )
    result.design.update(
        {
            "sampling_rate_hz": float(sampling_rate_hz),
            "excluded_labels": sorted({_normalise_label(value) for value in excluded_labels}),
            "max_gap_factor": float(max_gap_factor),
            "true_label_col": true_label_col,
            "predicted_label_col": predicted_label_col,
        }
    )
    return result
