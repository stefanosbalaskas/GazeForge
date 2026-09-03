"""Adapter for the manually annotated Gaze-in-the-Wild event benchmark."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.io import loadmat

from .exceptions import SchemaError
from .schema import GazeFrame

GAZE_IN_WILD_LABELS = {
    0: "unlabelled",
    1: "fixation",
    2: "pursuit",
    3: "saccade",
    4: "blink",
    5: "vor",
}

_LABEL_RE = re.compile(r"^(?P<recording>.+)_Lbr_(?P<labeller>\d+)$")


def _field(obj: Any, name: str) -> Any:
    if isinstance(obj, Mapping):
        if name in obj:
            return obj[name]
    if hasattr(obj, name):
        return getattr(obj, name)
    if isinstance(obj, np.ndarray) and obj.dtype.names and name in obj.dtype.names:
        value = obj[name]
        while isinstance(value, np.ndarray) and value.size == 1:
            value = value.reshape(-1)[0]
        return value
    raise SchemaError(f"Gaze-in-the-Wild MATLAB struct is missing field {name!r}.")


def _load_struct(path: Path, key: str) -> Any:
    raw = loadmat(path, squeeze_me=True, struct_as_record=False)
    if key not in raw:
        raise SchemaError(f"{path.name} does not contain MATLAB variable {key!r}.")
    return raw[key]


def _numeric_vector(value: Any, *, name: str) -> np.ndarray:
    try:
        out = np.asarray(value, dtype=float).reshape(-1)
    except (TypeError, ValueError) as exc:
        raise SchemaError(f"Gaze-in-the-Wild field {name!r} must be numeric.") from exc
    if not len(out):
        raise SchemaError(f"Gaze-in-the-Wild field {name!r} cannot be empty.")
    return out


def _label_file_metadata(path: Path) -> tuple[str, int | None]:
    match = _LABEL_RE.match(path.stem)
    if match is None:
        return path.stem, None
    return match.group("recording"), int(match.group("labeller"))


def _infer_rate_from_seconds(times_s: np.ndarray) -> float:
    if np.any(~np.isfinite(times_s)):
        raise SchemaError("Gaze-in-the-Wild timestamps must be finite.")
    if len(times_s) < 2:
        raise SchemaError("At least two timestamps are required to infer sampling rate.")
    diffs = np.diff(times_s)
    if np.any(diffs <= 0):
        raise SchemaError("Gaze-in-the-Wild timestamps must be strictly increasing.")
    median_dt_s = float(np.median(diffs))
    rate = 1.0 / median_dt_s
    if not np.isfinite(rate) or rate <= 0:
        raise SchemaError("Could not infer a valid Gaze-in-the-Wild sampling rate.")
    return rate


def _por_xy(por: Any, n_samples: int) -> tuple[np.ndarray, np.ndarray]:
    try:
        values = np.asarray(por, dtype=float)
    except (TypeError, ValueError) as exc:
        raise SchemaError("Gaze-in-the-Wild ETG.POR must be numeric.") from exc
    values = np.squeeze(values)
    if values.ndim != 2:
        raise SchemaError("Gaze-in-the-Wild ETG.POR must be a two-dimensional array.")
    if values.shape == (2, n_samples):
        return values[0].copy(), values[1].copy()
    if values.shape == (n_samples, 2):
        return values[:, 0].copy(), values[:, 1].copy()
    raise SchemaError(
        "Gaze-in-the-Wild ETG.POR shape must be 2×N or N×2 and match LabelData."
    )


def load_gaze_in_wild_mat(
    label_path: str | Path,
    *,
    process_path: str | Path | None = None,
    participant_id: str | None = None,
    trial_id: str | None = None,
    confidence_threshold: float = 0.30,
) -> GazeFrame:
    """Load one manually annotated Gaze-in-the-Wild recording.

    Sampling rate is inferred from ``LabelData.T`` rather than hard-coded. The published hardware
    rate (120 Hz) is retained as provenance because secondary processed benchmark descriptions have
    reported a different cadence. Point-of-regard coordinates are retained but marked unverified;
    unit-sensitive cross-dataset modelling must not proceed until their basis is independently
    audited.
    """
    label_file = Path(label_path)
    if not label_file.exists():
        raise FileNotFoundError(label_file)
    threshold = float(confidence_threshold)
    if not np.isfinite(threshold) or not 0.0 <= threshold <= 1.0:
        raise ValueError("confidence_threshold must be finite and in [0, 1].")

    label_data = _load_struct(label_file, "LabelData")
    recording, filename_labeller = _label_file_metadata(label_file)
    labels_raw = _numeric_vector(_field(label_data, "Labels"), name="Labels")
    times_s = _numeric_vector(_field(label_data, "T"), name="T")
    if len(labels_raw) != len(times_s):
        raise SchemaError("Gaze-in-the-Wild LabelData Labels and T lengths differ.")

    labeller_value: int | None = filename_labeller
    try:
        label_struct_labeller = int(np.asarray(_field(label_data, "LbrIdx")).reshape(-1)[0])
    except SchemaError:
        label_struct_labeller = None
    if filename_labeller is not None and label_struct_labeller is not None:
        if filename_labeller != label_struct_labeller:
            raise SchemaError(
                "Gaze-in-the-Wild labeller index disagrees between filename and LabelData.LbrIdx."
            )
    if label_struct_labeller is not None:
        labeller_value = label_struct_labeller

    sampling_rate_hz = _infer_rate_from_seconds(times_s)
    n_samples = len(times_s)
    x = np.full(n_samples, np.nan, dtype=float)
    y = np.full(n_samples, np.nan, dtype=float)
    confidence = np.full(n_samples, np.nan, dtype=float)
    valid = np.zeros(n_samples, dtype=bool)
    process_file: Path | None = None

    if process_path is not None:
        process_file = Path(process_path)
        if not process_file.exists():
            raise FileNotFoundError(process_file)
        process_data = _load_struct(process_file, "ProcessData")
        etg = _field(process_data, "ETG")
        x, y = _por_xy(_field(etg, "POR"), n_samples)
        confidence = _numeric_vector(_field(etg, "Confidence"), name="ETG.Confidence")
        if len(confidence) != n_samples:
            raise SchemaError(
                "Gaze-in-the-Wild ETG.Confidence length does not match LabelData."
            )
        valid = np.isfinite(confidence) & (confidence >= threshold)
        x[~valid] = np.nan
        y[~valid] = np.nan

    event_codes = np.rint(labels_raw).astype(int)
    event_labels = [
        GAZE_IN_WILD_LABELS.get(int(code), f"unknown_{int(code)}") for code in event_codes
    ]
    participant = participant_id if participant_id is not None else "__unresolved__"
    trial = trial_id if trial_id is not None else recording

    frame = pd.DataFrame(
        {
            "participant_id": str(participant),
            "trial_id": str(trial),
            "timestamp_ms": times_s * 1000.0,
            "x_px": x,
            "y_px": y,
            "validity": valid,
            "confidence": confidence,
            "event_code": event_codes,
            "event_label": event_labels,
            "annotator": None if labeller_value is None else f"labeller_{labeller_value}",
            "dataset_id": "Gaze-in-the-Wild",
            "source_file": label_file.name,
            "source_sampling_rate_hz": sampling_rate_hz,
        }
    )
    return GazeFrame(
        data=frame,
        sampling_rate_hz=sampling_rate_hz,
        screen_size_px=None,
        metadata={
            "source_dataset": "Gaze-in-the-Wild",
            "source_file": label_file.name,
            "source_process_file": None if process_file is None else process_file.name,
            "labeller_id": labeller_value,
            "label_code_map": dict(GAZE_IN_WILD_LABELS),
            "confidence_threshold": threshold,
            "participant_identity_resolved": participant_id is not None,
            "coordinate_source_unit": "dataset-native POR; unit not independently verified",
            "coordinate_unit_verified": False,
            "sampling_rate_source": "inferred_from_LabelData.T",
            "published_hardware_sampling_rate_hz": 120.0,
            "published_hardware": "Pupil Labs binocular eye-tracking glasses",
            "sampling_rate_provenance_note": (
                "The primary paper reports 120 Hz acquisition; secondary processed benchmark "
                "metadata has reported another cadence. Analysis uses file timestamps."
            ),
        },
    )


def load_gaze_in_wild_directory(
    label_root: str | Path,
    *,
    process_root: str | Path | None = None,
    participant_parser: Callable[[Path], str | None] | None = None,
    labeller: int | None = None,
    recursive: bool = True,
    confidence_threshold: float = 0.30,
) -> GazeFrame:
    """Load a directory of Gaze-in-the-Wild annotation files without guessing identities."""
    label_dir = Path(label_root)
    if not label_dir.exists():
        raise FileNotFoundError(label_dir)
    process_dir = None if process_root is None else Path(process_root)
    if process_dir is not None and not process_dir.exists():
        raise FileNotFoundError(process_dir)
    pattern = "*_Lbr_*.mat" if labeller is None else f"*_Lbr_{int(labeller)}.mat"
    paths = sorted(label_dir.rglob(pattern) if recursive else label_dir.glob(pattern))
    if not paths:
        raise FileNotFoundError(f"No Gaze-in-the-Wild label files were found under {label_dir}.")
    selected_labellers = {
        value for _, value in map(_label_file_metadata, paths) if value is not None
    }
    if labeller is None and len(selected_labellers) > 1:
        raise SchemaError(
            "Multiple Gaze-in-the-Wild labellers were found; select one labeller explicitly "
            "before building a modelling table."
        )

    frames: list[GazeFrame] = []
    for path in paths:
        recording, _ = _label_file_metadata(path)
        participant = participant_parser(path) if participant_parser is not None else None
        process_path: Path | None = None
        if process_dir is not None:
            relative = path.relative_to(label_dir)
            process_path = process_dir / relative.parent / f"{recording}.mat"
        frames.append(
            load_gaze_in_wild_mat(
                path,
                process_path=process_path,
                participant_id=participant,
                trial_id=recording,
                confidence_threshold=confidence_threshold,
            )
        )

    rates = np.asarray([frame.sampling_rate_hz for frame in frames], dtype=float)
    median_rate = float(np.median(rates))
    if not np.allclose(rates, median_rate, rtol=0.01, atol=0.1):
        raise SchemaError(
            "Gaze-in-the-Wild files do not share a consistent inferred sampling rate: "
            f"{sorted(round(float(value), 6) for value in rates)}"
        )
    combined = pd.concat([frame.data for frame in frames], ignore_index=True)
    resolved = not combined["participant_id"].astype(str).eq("__unresolved__").any()
    return GazeFrame(
        data=combined,
        sampling_rate_hz=median_rate,
        screen_size_px=None,
        metadata={
            "source_dataset": "Gaze-in-the-Wild",
            "n_source_files": len(frames),
            "participant_identity_resolved": resolved,
            "coordinate_source_unit": "dataset-native POR; unit not independently verified",
            "coordinate_unit_verified": False,
            "sampling_rate_source": "median_of_file_timestamp_inference",
            "published_hardware_sampling_rate_hz": 120.0,
            "human_annotator_count_published": 5,
            "selected_labeller": (
                labeller if labeller is not None else next(iter(selected_labellers), None)
            ),
            "confidence_threshold": float(confidence_threshold),
        },
    )
