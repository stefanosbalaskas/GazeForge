"""Validation metrics for semantic AOIs and fixation assignments."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from sklearn.metrics import cohen_kappa_score

from .aoi import AOI, map_fixations_to_aois
from .exceptions import SchemaError


def aoi_iou(left: AOI, right: AOI) -> float:
    """Return intersection-over-union for two rectangular AOIs."""
    x1 = max(left.xmin, right.xmin)
    y1 = max(left.ymin, right.ymin)
    x2 = min(left.xmax, right.xmax)
    y2 = min(left.ymax, right.ymax)
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    left_area = (left.xmax - left.xmin) * (left.ymax - left.ymin)
    right_area = (right.xmax - right.xmin) * (right.ymax - right.ymin)
    union = left_area + right_area - intersection
    return 0.0 if union <= 0 else float(intersection / union)


def pairwise_aoi_iou(
    predicted: Sequence[AOI],
    reference: Sequence[AOI],
) -> pd.DataFrame:
    """Return all predicted-reference AOI IoU values in long format."""
    rows: list[dict[str, Any]] = []
    for pred in predicted:
        for ref in reference:
            rows.append(
                {
                    "predicted_aoi_id": pred.aoi_id,
                    "reference_aoi_id": ref.aoi_id,
                    "predicted_label": pred.label,
                    "reference_label": ref.label,
                    "label_match": pred.label == ref.label,
                    "iou": aoi_iou(pred, ref),
                }
            )
    return pd.DataFrame(rows)


def match_aois(
    predicted: Sequence[AOI],
    reference: Sequence[AOI],
    *,
    min_iou: float = 0.50,
    require_label_match: bool = False,
) -> pd.DataFrame:
    """One-to-one match predicted AOIs to references using maximum total IoU.

    Hungarian assignment is applied globally. Matches below ``min_iou`` are reported as
    unmatched, which prevents weak overlaps from inflating detection performance.
    """
    if not 0.0 <= min_iou <= 1.0:
        raise ValueError("min_iou must be in [0, 1].")

    predicted = list(predicted)
    reference = list(reference)
    if not predicted and not reference:
        return pd.DataFrame(
            columns=[
                "predicted_aoi_id",
                "reference_aoi_id",
                "predicted_label",
                "reference_label",
                "label_match",
                "iou",
                "status",
            ]
        )

    matched_pred: set[int] = set()
    matched_ref: set[int] = set()
    rows: list[dict[str, Any]] = []

    if predicted and reference:
        ious = np.zeros((len(predicted), len(reference)), dtype=float)
        for i, pred in enumerate(predicted):
            for j, ref in enumerate(reference):
                value = aoi_iou(pred, ref)
                if require_label_match and pred.label != ref.label:
                    value = 0.0
                ious[i, j] = value

        pred_idx, ref_idx = linear_sum_assignment(1.0 - ious)
        for i, j in zip(pred_idx, ref_idx, strict=True):
            value = float(ious[i, j])
            if value < min_iou:
                continue
            pred = predicted[i]
            ref = reference[j]
            matched_pred.add(int(i))
            matched_ref.add(int(j))
            rows.append(
                {
                    "predicted_aoi_id": pred.aoi_id,
                    "reference_aoi_id": ref.aoi_id,
                    "predicted_label": pred.label,
                    "reference_label": ref.label,
                    "label_match": pred.label == ref.label,
                    "iou": value,
                    "status": "matched",
                }
            )

    for i, pred in enumerate(predicted):
        if i not in matched_pred:
            rows.append(
                {
                    "predicted_aoi_id": pred.aoi_id,
                    "reference_aoi_id": None,
                    "predicted_label": pred.label,
                    "reference_label": None,
                    "label_match": False,
                    "iou": 0.0,
                    "status": "false_positive",
                }
            )

    for j, ref in enumerate(reference):
        if j not in matched_ref:
            rows.append(
                {
                    "predicted_aoi_id": None,
                    "reference_aoi_id": ref.aoi_id,
                    "predicted_label": None,
                    "reference_label": ref.label,
                    "label_match": False,
                    "iou": 0.0,
                    "status": "false_negative",
                }
            )

    return pd.DataFrame(rows)


def evaluate_aoi_detection(
    predicted: Sequence[AOI],
    reference: Sequence[AOI],
    *,
    min_iou: float = 0.50,
    require_label_match: bool = False,
) -> dict[str, Any]:
    """Compute geometric and semantic agreement against expert/reference AOIs."""
    matches = match_aois(
        predicted,
        reference,
        min_iou=min_iou,
        require_label_match=require_label_match,
    )
    status = matches["status"] if "status" in matches else pd.Series(dtype=str)
    tp = int((status == "matched").sum())
    fp = int((status == "false_positive").sum())
    fn = int((status == "false_negative").sum())
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    matched = matches[matches["status"] == "matched"] if not matches.empty else matches
    mean_iou = float(matched["iou"].mean()) if not matched.empty else 0.0
    semantic_accuracy = (
        float(matched["label_match"].mean()) if not matched.empty else 0.0
    )
    return {
        "n_predicted": int(len(predicted)),
        "n_reference": int(len(reference)),
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "mean_matched_iou": mean_iou,
        "semantic_label_accuracy_matched": semantic_accuracy,
        "min_iou": float(min_iou),
        "require_label_match": bool(require_label_match),
        "matches": matches.to_dict(orient="records"),
    }


def fixation_assignment_agreement(
    predicted: pd.DataFrame,
    reference: pd.DataFrame,
    *,
    key_cols: tuple[str, ...] = ("participant_id", "trial_id", "fixation_index"),
    label_col: str = "aoi_label",
    unassigned_label: str = "UNASSIGNED",
) -> dict[str, Any]:
    """Compare AI-derived and reference fixation-to-AOI assignments on aligned fixations."""
    required = [*key_cols, label_col]
    for name, frame in (("predicted", predicted), ("reference", reference)):
        missing = [col for col in required if col not in frame.columns]
        if missing:
            raise SchemaError(f"{name} assignments are missing columns: {missing}")
        if frame.duplicated(list(key_cols)).any():
            raise SchemaError(f"{name} assignments contain duplicate fixation keys.")

    joined = predicted[required].merge(
        reference[required],
        on=list(key_cols),
        how="inner",
        suffixes=("_predicted", "_reference"),
        validate="one_to_one",
    )
    if joined.empty:
        raise SchemaError("No aligned fixation keys were available for assignment agreement.")

    predicted_labels = joined[f"{label_col}_predicted"].fillna(unassigned_label).astype(str)
    reference_labels = joined[f"{label_col}_reference"].fillna(unassigned_label).astype(str)
    exact = predicted_labels == reference_labels
    predicted_assigned = predicted_labels != unassigned_label
    reference_assigned = reference_labels != unassigned_label

    return {
        "n_aligned_fixations": int(len(joined)),
        "exact_agreement": float(exact.mean()),
        "cohen_kappa": float(cohen_kappa_score(reference_labels, predicted_labels)),
        "predicted_assignment_rate": float(predicted_assigned.mean()),
        "reference_assignment_rate": float(reference_assigned.mean()),
        "assignment_rate_difference": float(predicted_assigned.mean() - reference_assigned.mean()),
    }


def aoi_boundary_sensitivity(
    fixations: pd.DataFrame,
    aois: Sequence[AOI],
    *,
    perturbations_px: Sequence[float] = (-10.0, -5.0, 5.0, 10.0),
    x_col: str = "x_px",
    y_col: str = "y_px",
    label_col: str = "aoi_label",
) -> pd.DataFrame:
    """Quantify fixation-assignment stability under AOI boundary perturbations.

    Positive perturbations expand every boundary. Negative values contract boundaries while
    retaining only AOIs that still have positive width and height.
    """
    baseline = map_fixations_to_aois(fixations, aois, x_col=x_col, y_col=y_col)
    baseline_labels = baseline[label_col].fillna("UNASSIGNED").astype(str)
    rows: list[dict[str, Any]] = []

    for delta in perturbations_px:
        shifted: list[AOI] = []
        for aoi in aois:
            xmin = aoi.xmin - float(delta)
            ymin = aoi.ymin - float(delta)
            xmax = aoi.xmax + float(delta)
            ymax = aoi.ymax + float(delta)
            if xmax <= xmin or ymax <= ymin:
                continue
            shifted.append(
                AOI(
                    aoi_id=aoi.aoi_id,
                    label=aoi.label,
                    xmin=xmin,
                    ymin=ymin,
                    xmax=xmax,
                    ymax=ymax,
                    confidence=aoi.confidence,
                    source=aoi.source,
                    model_name=aoi.model_name,
                    model_version=aoi.model_version,
                )
            )
        remapped = map_fixations_to_aois(fixations, shifted, x_col=x_col, y_col=y_col)
        labels = remapped[label_col].fillna("UNASSIGNED").astype(str)
        rows.append(
            {
                "boundary_delta_px": float(delta),
                "n_retained_aois": int(len(shifted)),
                "assignment_stability": float((labels == baseline_labels).mean()),
                "assignment_rate": float((labels != "UNASSIGNED").mean()),
            }
        )
    return pd.DataFrame(rows)


def sample_label_agreement(
    left: pd.DataFrame,
    right: pd.DataFrame,
    *,
    key_cols: tuple[str, ...] = ("participant_id", "trial_id", "timestamp_ms"),
    label_col: str = "event_label",
    missing_label: str = "MISSING",
) -> dict[str, Any]:
    """Compare aligned sample-level event labels from two annotators or methods."""
    required = [*key_cols, label_col]
    for name, frame in (("left", left), ("right", right)):
        missing = [col for col in required if col not in frame.columns]
        if missing:
            raise SchemaError(f"{name} labels are missing columns: {missing}")
        if frame.duplicated(list(key_cols)).any():
            raise SchemaError(f"{name} labels contain duplicate alignment keys.")

    joined = left[required].merge(
        right[required],
        on=list(key_cols),
        how="inner",
        suffixes=("_left", "_right"),
        validate="one_to_one",
    )
    if joined.empty:
        raise SchemaError("No aligned samples were available for label agreement.")
    left_labels = joined[f"{label_col}_left"].fillna(missing_label).astype(str)
    right_labels = joined[f"{label_col}_right"].fillna(missing_label).astype(str)
    labels = sorted(set(left_labels) | set(right_labels))
    confusion = pd.crosstab(
        pd.Categorical(left_labels, categories=labels),
        pd.Categorical(right_labels, categories=labels),
        dropna=False,
    )
    confusion.index.name = "left_label"
    confusion.columns.name = "right_label"
    return {
        "n_aligned_samples": int(len(joined)),
        "exact_agreement": float((left_labels == right_labels).mean()),
        "cohen_kappa": float(cohen_kappa_score(left_labels, right_labels)),
        "labels": labels,
        "confusion_matrix": confusion.to_dict(),
    }
