"""Adapter for the manually annotated Lund2013 eye-movement benchmark files."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.io import loadmat

from .exceptions import SchemaError
from .schema import GazeFrame

LUND2013_LABELS = {
    0: "unlabelled",
    1: "fixation",
    2: "saccade",
    3: "pso",
    4: "pursuit",
    5: "blink",
    6: "undefined",
}


def _mat_field(etdata: np.ndarray, name: str) -> Any:
    names = etdata.dtype.names or ()
    if name not in names:
        raise SchemaError(f"Lund2013 ETdata is missing field {name!r}.")
    return etdata[name][0, 0]


def _numeric_flat(value: Any) -> np.ndarray:
    try:
        return np.asarray(value, dtype=float).reshape(-1)
    except (TypeError, ValueError) as exc:
        raise SchemaError("Lund2013 metadata contains a non-numeric field.") from exc


def _infer_file_metadata(path: Path) -> dict[str, str | None]:
    stem = path.stem
    annotator_match = re.search(r"_labelled_([A-Za-z0-9]+)$", stem)
    annotator = annotator_match.group(1) if annotator_match else None
    base = stem[: annotator_match.start()] if annotator_match else stem
    participant = base.split("_", maxsplit=1)[0] if "_" in base else base
    if "_img_" in f"_{base}_":
        stimulus_type = "image"
    elif "_video_" in f"_{base}_":
        stimulus_type = "video"
    elif re.search(r"_trial\d+", base):
        stimulus_type = "moving_dot"
    else:
        stimulus_type = "unknown"
    return {
        "participant_id": participant or None,
        "trial_id": base or None,
        "annotator": annotator,
        "stimulus_type": stimulus_type,
    }


def load_lund2013_mat(
    path: str | Path,
    *,
    participant_id: str | None = None,
    trial_id: str | None = None,
    annotator: str | None = None,
    stimulus_type: str | None = None,
    zero_pair_is_missing: bool = True,
) -> GazeFrame:
    """Load one annotated Lund2013 MATLAB file into GazeForge's canonical gaze schema.

    The public benchmark stores x/y coordinates in columns 4/5 of MATLAB's one-based `pos`
    matrix and human event codes in column 6. Codes follow the original benchmark convention:
    fixation=1, saccade=2, PSO=3, pursuit=4, blink=5, undefined=6; code 0 is retained as
    `unlabelled` rather than silently discarded.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(file_path)

    raw = loadmat(file_path)
    if "ETdata" not in raw:
        raise SchemaError("Lund2013 MATLAB file does not contain ETdata.")
    etdata = raw["ETdata"]
    if not isinstance(etdata, np.ndarray) or etdata.size != 1:
        raise SchemaError("Lund2013 ETdata must be a scalar MATLAB struct.")

    pos = np.asarray(_mat_field(etdata, "pos"), dtype=float)
    if pos.ndim != 2 or pos.shape[1] < 6:
        raise SchemaError("Lund2013 ETdata.pos must have at least six columns.")
    sampling_values = _numeric_flat(_mat_field(etdata, "sampFreq"))
    if not len(sampling_values) or sampling_values[0] <= 0:
        raise SchemaError("Lund2013 sampFreq must contain a positive sampling rate.")
    sampling_rate_hz = float(sampling_values[0])

    inferred = _infer_file_metadata(file_path)
    participant = participant_id or inferred["participant_id"] or "unknown"
    trial = trial_id or inferred["trial_id"] or file_path.stem
    coder = annotator or inferred["annotator"]
    stimulus = stimulus_type or inferred["stimulus_type"] or "unknown"

    x = pos[:, 3].astype(float, copy=True)
    y = pos[:, 4].astype(float, copy=True)
    if zero_pair_is_missing:
        missing = (x == 0) & (y == 0)
        x[missing] = np.nan
        y[missing] = np.nan
    codes = np.rint(pos[:, 5]).astype(int)
    labels = [LUND2013_LABELS.get(int(code), f"unknown_{int(code)}") for code in codes]
    timestamps = np.arange(len(pos), dtype=float) * (1000.0 / sampling_rate_hz)

    frame = pd.DataFrame(
        {
            "participant_id": str(participant),
            "trial_id": str(trial),
            "timestamp_ms": timestamps,
            "x_px": x,
            "y_px": y,
            "event_code": codes,
            "event_label": labels,
            "annotator": coder,
            "stimulus_type": stimulus,
            "dataset_id": "Lund2013",
            "source_file": file_path.name,
        }
    )

    screen_values = _numeric_flat(_mat_field(etdata, "screenRes"))
    screen_size_px: tuple[int, int] | None = None
    if len(screen_values) >= 2 and np.all(screen_values[:2] > 0):
        screen_size_px = (int(round(screen_values[0])), int(round(screen_values[1])))

    screen_dimensions = (
        _numeric_flat(_mat_field(etdata, "screenDim"))
        if "screenDim" in (etdata.dtype.names or ())
        else np.array([], dtype=float)
    )
    view_distance = (
        _numeric_flat(_mat_field(etdata, "viewDist"))
        if "viewDist" in (etdata.dtype.names or ())
        else np.array([], dtype=float)
    )
    geometry_available = (
        screen_size_px is not None
        and len(screen_dimensions) >= 2
        and np.all(screen_dimensions[:2] > 0)
        and len(view_distance) >= 1
        and view_distance[0] > 0
    )
    if geometry_available:
        frame["screen_width_px"] = float(screen_size_px[0])
        frame["screen_height_px"] = float(screen_size_px[1])
        frame["screen_width_physical"] = float(screen_dimensions[0])
        frame["screen_height_physical"] = float(screen_dimensions[1])
        frame["view_distance_physical"] = float(view_distance[0])

    metadata: dict[str, Any] = {
        "source_dataset": "Lund2013",
        "source_file": file_path.name,
        "annotator": coder,
        "stimulus_type": stimulus,
        "label_code_map": dict(LUND2013_LABELS),
        "zero_pair_is_missing": bool(zero_pair_is_missing),
        "visual_angle_geometry_available": bool(geometry_available),
        "physical_geometry_units": "source-consistent; screenDim and viewDist use the same unit",
    }
    for source_name, target_name in (
        ("viewDist", "view_distance"),
        ("screenDim", "screen_dimensions"),
        ("screenRes", "screen_resolution"),
    ):
        if source_name in (etdata.dtype.names or ()):
            values = _numeric_flat(_mat_field(etdata, source_name))
            metadata[target_name] = values.tolist()

    return GazeFrame(
        data=frame,
        sampling_rate_hz=sampling_rate_hz,
        screen_size_px=screen_size_px,
        metadata=metadata,
    )


def load_lund2013_directory(
    root: str | Path,
    *,
    annotator: str = "RA",
    recursive: bool = True,
) -> GazeFrame:
    """Load and concatenate Lund2013 files for one annotator from a benchmark directory."""
    root_path = Path(root)
    if not root_path.exists():
        raise FileNotFoundError(root_path)
    pattern = f"*_labelled_{annotator}.mat"
    paths = sorted(root_path.rglob(pattern) if recursive else root_path.glob(pattern))
    if not paths:
        raise FileNotFoundError(
            f"No Lund2013 files matching {pattern!r} were found under {root_path}."
        )

    frames = [load_lund2013_mat(path) for path in paths]
    rates = {round(frame.sampling_rate_hz, 9) for frame in frames}
    if len(rates) != 1:
        raise SchemaError(f"Lund2013 files contain inconsistent sampling rates: {sorted(rates)}")
    combined = pd.concat([frame.data for frame in frames], ignore_index=True)
    screen_sizes = {frame.screen_size_px for frame in frames if frame.screen_size_px is not None}
    screen_size_px = next(iter(screen_sizes)) if len(screen_sizes) == 1 else None
    return GazeFrame(
        data=combined,
        sampling_rate_hz=frames[0].sampling_rate_hz,
        screen_size_px=screen_size_px,
        metadata={
            "source_dataset": "Lund2013",
            "annotator": annotator,
            "n_source_files": len(paths),
            "source_files": [path.name for path in paths],
            "label_code_map": dict(LUND2013_LABELS),
        },
    )
