"""Optional, composable visual diagnostics for eye-tracking workflows.

Plotting is deliberately separated from scientific estimation. The functions in
this module do not delete rows, refit models, change classifications, or call
``show()``/``savefig()``. They render already-computed analytic structures and
return a Matplotlib ``Axes`` so callers retain control of composition and output.
"""

from __future__ import annotations

from collections.abc import Sequence
from itertools import cycle
from typing import Any

import pandas as pd

from .aoi import AOI
from .calibration import top_label_calibration_table
from .dynamic_aoi import DynamicAOIKeyframe, interpolate_dynamic_aoi
from .exceptions import OptionalDependencyError, SchemaError


_PLOT_INSTALL_GUIDANCE = (
    "Visual diagnostics require Matplotlib. For a repository checkout, install the "
    "plotting extra with `python -m pip install -e \".[plot]\"`; for a packaged "
    "release, use the plotting extra documented for that release."
)


def _pyplot():
    try:
        from matplotlib import pyplot as plt
    except ImportError as exc:  # pragma: no cover - exercised with import isolation
        raise OptionalDependencyError(_PLOT_INSTALL_GUIDANCE) from exc
    return plt


def _axis(ax: Any | None, *, figsize: tuple[float, float]) -> Any:
    if ax is not None:
        return ax
    plt = _pyplot()
    _, created = plt.subplots(figsize=figsize)
    return created


def _require_columns(data: pd.DataFrame, columns: Sequence[str], *, context: str) -> None:
    missing = [column for column in columns if column not in data.columns]
    if missing:
        raise SchemaError(f"{context} is missing columns: {missing}")


def plot_qc_timeline(
    data: pd.DataFrame,
    *,
    timestamp_col: str = "timestamp_ms",
    score_col: str = "qc_anomaly_score",
    flag_col: str = "qc_flag",
    ax: Any | None = None,
    title: str | None = "QC anomaly timeline",
) -> Any:
    """Plot anomaly score over time and mark flagged samples without changing data."""
    _require_columns(data, [timestamp_col, score_col], context="QC timeline input")
    axis = _axis(ax, figsize=(9.0, 3.8))
    timestamp = pd.to_numeric(data[timestamp_col], errors="coerce")
    score = pd.to_numeric(data[score_col], errors="coerce")
    valid = timestamp.notna() & score.notna()
    axis.plot(timestamp[valid], score[valid], label="anomaly score", linewidth=1.4)

    if flag_col in data.columns:
        flagged = data[flag_col].fillna(False).astype(bool) & valid
        if flagged.any():
            axis.scatter(
                timestamp[flagged],
                score[flagged],
                marker="x",
                s=42,
                linewidths=1.5,
                label="flagged sample",
            )

    axis.set_xlabel("Time (ms)")
    axis.set_ylabel("Anomaly score")
    if title:
        axis.set_title(title)
    axis.legend()
    return axis


def plot_event_probabilities(
    predictions: pd.DataFrame,
    *,
    timestamp_col: str = "timestamp_ms",
    probability_prefix: str = "p_event_",
    confidence_threshold: float | None = None,
    ax: Any | None = None,
    title: str | None = "Event probabilities",
) -> Any:
    """Plot class probabilities with line-style cues in addition to colour."""
    _require_columns(predictions, [timestamp_col], context="Event-probability input")
    probability_cols = [
        column for column in predictions.columns if column.startswith(probability_prefix)
    ]
    if not probability_cols:
        raise SchemaError(
            f"Event-probability input has no columns with prefix {probability_prefix!r}."
        )
    if confidence_threshold is not None and not 0.0 <= float(confidence_threshold) <= 1.0:
        raise ValueError("confidence_threshold must be in [0, 1].")

    axis = _axis(ax, figsize=(9.0, 4.2))
    timestamp = pd.to_numeric(predictions[timestamp_col], errors="coerce")
    styles = cycle(("-", "--", "-.", ":"))
    for column in probability_cols:
        values = pd.to_numeric(predictions[column], errors="coerce")
        valid = timestamp.notna() & values.notna()
        label = column[len(probability_prefix) :] or column
        axis.plot(
            timestamp[valid],
            values[valid],
            linestyle=next(styles),
            linewidth=1.5,
            label=label,
        )

    if confidence_threshold is not None:
        axis.axhline(
            float(confidence_threshold),
            linestyle=":",
            linewidth=1.2,
            label=f"threshold {float(confidence_threshold):.2f}",
        )
    axis.set_ylim(0.0, 1.0)
    axis.set_xlabel("Time (ms)")
    axis.set_ylabel("Probability")
    if title:
        axis.set_title(title)
    axis.legend(ncol=min(3, max(1, len(probability_cols))))
    return axis


def plot_event_calibration(
    predictions: pd.DataFrame,
    *,
    true_label_col: str = "event_label",
    probability_prefix: str = "p_event_",
    n_bins: int = 10,
    ax: Any | None = None,
    title: str | None = "Top-label calibration",
) -> Any:
    """Plot observed top-label calibration against the ideal diagonal."""
    table = top_label_calibration_table(
        predictions,
        true_label_col=true_label_col,
        probability_prefix=probability_prefix,
        n_bins=n_bins,
    )
    nonempty = table.loc[table["n"] > 0].copy()
    axis = _axis(ax, figsize=(5.4, 5.0))
    axis.plot([0.0, 1.0], [0.0, 1.0], linestyle="--", linewidth=1.2, label="ideal")
    axis.plot(
        nonempty["mean_confidence"],
        nonempty["accuracy"],
        marker="o",
        linewidth=1.5,
        label="observed",
    )
    for row in nonempty.itertuples(index=False):
        axis.annotate(
            f"n={int(row.n)}",
            (float(row.mean_confidence), float(row.accuracy)),
            xytext=(4, 4),
            textcoords="offset points",
            fontsize="x-small",
        )
    axis.set_xlim(0.0, 1.0)
    axis.set_ylim(0.0, 1.0)
    axis.set_aspect("equal", adjustable="box")
    axis.set_xlabel("Mean confidence")
    axis.set_ylabel("Empirical accuracy")
    if title:
        axis.set_title(title)
    axis.legend()
    return axis


def plot_aoi_overlay(
    aois: Sequence[AOI],
    *,
    fixations: pd.DataFrame | None = None,
    image: Any | None = None,
    x_col: str = "x_px",
    y_col: str = "y_px",
    ax: Any | None = None,
    invert_y: bool = True,
    title: str | None = "AOI overlay",
) -> Any:
    """Overlay labelled AOI rectangles and optional fixation locations."""
    axis = _axis(ax, figsize=(8.0, 5.0))
    if image is not None:
        axis.imshow(image)

    try:
        from matplotlib.patches import Rectangle
    except ImportError as exc:  # pragma: no cover - guarded by normal optional install
        raise OptionalDependencyError(_PLOT_INSTALL_GUIDANCE) from exc

    colors = cycle(_pyplot().rcParams["axes.prop_cycle"].by_key()["color"])
    styles = cycle(("solid", "dashed", "dashdot", "dotted"))
    for aoi in aois:
        rectangle = Rectangle(
            (aoi.xmin, aoi.ymin),
            aoi.xmax - aoi.xmin,
            aoi.ymax - aoi.ymin,
            fill=False,
            linewidth=2.0,
            edgecolor=next(colors),
            linestyle=next(styles),
        )
        axis.add_patch(rectangle)
        axis.text(
            aoi.xmin,
            aoi.ymin,
            f"{aoi.label} ({aoi.aoi_id})",
            va="bottom",
            fontsize="small",
            bbox={"boxstyle": "round,pad=0.2", "facecolor": "white", "alpha": 0.75},
        )

    if fixations is not None:
        _require_columns(fixations, [x_col, y_col], context="AOI fixation input")
        x = pd.to_numeric(fixations[x_col], errors="coerce")
        y = pd.to_numeric(fixations[y_col], errors="coerce")
        valid = x.notna() & y.notna()
        axis.scatter(x[valid], y[valid], marker="o", s=28, label="fixation")
        if valid.any():
            axis.legend()

    axis.set_xlabel("x (px)")
    axis.set_ylabel("y (px)")
    if image is None and invert_y:
        axis.invert_yaxis()
    if title:
        axis.set_title(title)
    return axis


def plot_scanpath(
    fixations: pd.DataFrame,
    *,
    x_col: str = "x_px",
    y_col: str = "y_px",
    label_col: str | None = "aoi_label",
    ax: Any | None = None,
    invert_y: bool = True,
    annotate_order: bool = True,
    title: str | None = "Scanpath",
) -> Any:
    """Plot a fixation sequence with connected markers and optional semantic labels."""
    _require_columns(fixations, [x_col, y_col], context="Scanpath input")
    if label_col is not None and label_col not in fixations.columns:
        raise SchemaError(f"Scanpath input is missing label column: {label_col!r}")
    axis = _axis(ax, figsize=(7.0, 5.0))
    x = pd.to_numeric(fixations[x_col], errors="coerce")
    y = pd.to_numeric(fixations[y_col], errors="coerce")
    valid = x.notna() & y.notna()
    xv = x[valid].to_numpy(dtype=float)
    yv = y[valid].to_numpy(dtype=float)
    axis.plot(xv, yv, marker="o", linewidth=1.4, label="fixation sequence")

    if annotate_order:
        labels = None
        if label_col is not None:
            labels = fixations.loc[valid, label_col].astype(str).to_numpy()
        for index, (x_value, y_value) in enumerate(zip(xv, yv, strict=True), start=1):
            suffix = "" if labels is None else f" · {labels[index - 1]}"
            axis.annotate(
                f"{index}{suffix}",
                (x_value, y_value),
                xytext=(5, 5),
                textcoords="offset points",
                fontsize="x-small",
            )

    axis.set_xlabel("x (px)")
    axis.set_ylabel("y (px)")
    if invert_y:
        axis.invert_yaxis()
    if title:
        axis.set_title(title)
    axis.legend()
    return axis


def plot_dynamic_aoi_snapshot(
    keyframes: Sequence[DynamicAOIKeyframe],
    timestamp_ms: float,
    *,
    fixations: pd.DataFrame | None = None,
    image: Any | None = None,
    x_col: str = "x_px",
    y_col: str = "y_px",
    max_interpolation_gap_ms: float = 100.0,
    ax: Any | None = None,
    invert_y: bool = True,
    title: str | None = None,
) -> Any:
    """Plot dynamic AOI geometry at one timestamp using bounded interpolation only."""
    tracks: dict[str, list[DynamicAOIKeyframe]] = {}
    for frame in keyframes:
        tracks.setdefault(frame.aoi_id, []).append(frame)

    visible: list[AOI] = []
    for track in tracks.values():
        geometry = interpolate_dynamic_aoi(
            track,
            float(timestamp_ms),
            max_gap_ms=float(max_interpolation_gap_ms),
        )
        if geometry is None:
            continue
        visible.append(
            AOI(
                aoi_id=geometry.aoi_id,
                label=geometry.label,
                xmin=geometry.xmin,
                ymin=geometry.ymin,
                xmax=geometry.xmax,
                ymax=geometry.ymax,
                confidence=geometry.confidence,
                source=geometry.source,
                model_name=geometry.model_name,
                model_version=geometry.model_version,
            )
        )

    snapshot_title = title if title is not None else f"Dynamic AOIs at {float(timestamp_ms):g} ms"
    return plot_aoi_overlay(
        visible,
        fixations=fixations,
        image=image,
        x_col=x_col,
        y_col=y_col,
        ax=ax,
        invert_y=invert_y,
        title=snapshot_title,
    )


__all__ = [
    "plot_aoi_overlay",
    "plot_dynamic_aoi_snapshot",
    "plot_event_calibration",
    "plot_event_probabilities",
    "plot_qc_timeline",
    "plot_scanpath",
]
