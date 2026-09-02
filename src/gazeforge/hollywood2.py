"""Adapter for the manually annotated Hollywood2 eye-movement benchmark."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.io import arff

from .exceptions import SchemaError
from .schema import GazeFrame, infer_sampling_rate_hz

HOLLYWOOD2_EVENT_LABELS = {
    0: "unlabelled",
    1: "fixation",
    2: "saccade",
    3: "pursuit",
    4: "noise",
}

_HOLLYWOOD2_STRING_LABELS = {
    "UNKNOWN": "unlabelled",
    "UNASSIGNED": "unlabelled",
    "FIX": "fixation",
    "FIXATION": "fixation",
    "SACCADE": "saccade",
    "SP": "pursuit",
    "PURSUIT": "pursuit",
    "SMOOTH_PURSUIT": "pursuit",
    "NOISE": "noise",
    "BLINK": "noise",
    "NOISE_CLUSTER": "noise",
}

HOLLYWOOD2_ANNOTATOR_COLUMNS = {
    "student": "handlabeller_1",
    "novice": "handlabeller_1",
    "final": "handlabeller_final",
    "expert": "handlabeller_final",
}

IdentityParser = Callable[[Path], tuple[str, str]]


def _decode_arff_value(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


def _load_arff_frame(path: Path) -> pd.DataFrame:
    try:
        records, _ = arff.loadarff(path)
    except (OSError, ValueError) as exc:
        raise SchemaError(f"Could not parse Hollywood2 ARFF file: {path}") from exc
    frame = pd.DataFrame(records)
    for column in frame.columns:
        if frame[column].dtype == object:
            frame[column] = frame[column].map(_decode_arff_value)
    return frame


def _map_hollywood2_label(value: Any) -> str:
    value = _decode_arff_value(value)
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "unlabelled"
    if isinstance(value, (int, np.integer)):
        return HOLLYWOOD2_EVENT_LABELS.get(int(value), f"unknown_{int(value)}")
    if isinstance(value, (float, np.floating)) and np.isfinite(value):
        rounded = int(round(float(value)))
        if np.isclose(value, rounded):
            return HOLLYWOOD2_EVENT_LABELS.get(rounded, f"unknown_{rounded}")
    text = str(value).strip()
    mapped = _HOLLYWOOD2_STRING_LABELS.get(text.upper())
    return mapped if mapped is not None else f"unknown_{text}"


def _resolve_label_column(frame: pd.DataFrame, annotator: str, label_col: str | None) -> str:
    if label_col is not None:
        column = label_col
    else:
        key = str(annotator).strip().lower()
        column = HOLLYWOOD2_ANNOTATOR_COLUMNS.get(key, annotator)
    if column not in frame.columns:
        raise SchemaError(
            f"Hollywood2 ARFF is missing annotation column {column!r}; "
            f"available columns are {list(frame.columns)}."
        )
    return str(column)


def load_hollywood2_arff(
    path: str | Path,
    *,
    annotator: str = "final",
    label_col: str | None = None,
    participant_id: str | None = None,
    trial_id: str | None = None,
    split: str | None = None,
    expected_sampling_rate_hz: float | None = 500.0,
    sampling_rate_tolerance: float = 0.05,
    confidence_threshold: float = 0.5,
    zero_pair_is_missing: bool = True,
    coordinate_unit: str = "unverified",
) -> GazeFrame:
    """Load one Hollywood2EM hand-labelled ARFF recording.

    The published/TUM evaluation convention stores ``time`` in microseconds and uses ``x``, ``y``,
    and ``confidence`` for the gaze samples. ``handlabeller_1`` contains the first/student coding
    pass and ``handlabeller_final`` contains the expert-corrected labels. Participant identity is
    deliberately **not** guessed from filenames; callers should supply it when participant-held-out
    validation is intended.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(file_path)
    if not 0.0 <= confidence_threshold <= 1.0:
        raise ValueError("confidence_threshold must be in [0, 1].")
    if sampling_rate_tolerance < 0:
        raise ValueError("sampling_rate_tolerance must be non-negative.")
    coordinate_unit = str(coordinate_unit).strip().lower()
    if coordinate_unit not in {"unverified", "pixels"}:
        raise ValueError("coordinate_unit must be 'unverified' or 'pixels'.")
    coordinate_unit_verified = coordinate_unit == "pixels"

    source = _load_arff_frame(file_path)
    required = ["time", "x", "y", "confidence"]
    missing = [column for column in required if column not in source.columns]
    if missing:
        raise SchemaError(f"Hollywood2 ARFF is missing gaze columns: {missing}")
    annotation_column = _resolve_label_column(source, annotator, label_col)

    time_us = pd.to_numeric(source["time"], errors="coerce")
    x = pd.to_numeric(source["x"], errors="coerce")
    y = pd.to_numeric(source["y"], errors="coerce")
    confidence = pd.to_numeric(source["confidence"], errors="coerce")
    if time_us.isna().any():
        raise SchemaError("Hollywood2 time contains missing or non-numeric values.")

    trackloss = (x == 0) & (y == 0)
    valid = confidence.gt(float(confidence_threshold)) & ~trackloss & x.notna() & y.notna()
    if zero_pair_is_missing:
        x = x.mask(trackloss)
        y = y.mask(trackloss)

    participant = str(participant_id) if participant_id is not None else "__unresolved__"
    trial = str(trial_id) if trial_id is not None else file_path.stem
    raw_labels = source[annotation_column].map(_decode_arff_value)
    event_labels = raw_labels.map(_map_hollywood2_label)

    frame = pd.DataFrame(
        {
            "participant_id": participant,
            "trial_id": trial,
            "timestamp_ms": time_us.to_numpy(dtype=float) / 1000.0,
            "x_px": x.to_numpy(dtype=float),
            "y_px": y.to_numpy(dtype=float),
            "validity": valid.to_numpy(dtype=bool),
            "confidence": confidence.to_numpy(dtype=float),
            "event_raw_label": raw_labels.astype(str).to_numpy(),
            "event_label": event_labels.to_numpy(),
            "annotator": annotation_column,
            "split": split,
            "dataset_id": "Hollywood2EM",
            "source_file": file_path.name,
            "coordinate_unit": coordinate_unit,
            "coordinate_unit_verified": coordinate_unit_verified,
        }
    )
    sampling_rate_hz = infer_sampling_rate_hz(frame)
    if expected_sampling_rate_hz is not None:
        expected = float(expected_sampling_rate_hz)
        if not np.isfinite(expected) or expected <= 0:
            raise ValueError("expected_sampling_rate_hz must be finite and positive.")
        relative_error = abs(sampling_rate_hz - expected) / expected
        if relative_error > float(sampling_rate_tolerance):
            raise SchemaError(
                "Hollywood2 sampling rate is incompatible with the expected rate: "
                f"inferred={sampling_rate_hz:.6g} Hz, expected={expected:.6g} Hz, "
                f"tolerance={sampling_rate_tolerance:.3g}."
            )

    return GazeFrame(
        data=frame,
        sampling_rate_hz=float(sampling_rate_hz),
        metadata={
            "source_dataset": "Hollywood2EM",
            "source_file": file_path.name,
            "annotation_column": annotation_column,
            "participant_identity_resolved": participant_id is not None,
            "trial_identity_explicit": trial_id is not None,
            "split": split,
            "time_source_unit": "microseconds",
            "coordinate_source_unit": coordinate_unit,
            "coordinate_unit_verified": coordinate_unit_verified,
            "canonical_coordinate_alias_only": not coordinate_unit_verified,
            "zero_pair_is_missing": bool(zero_pair_is_missing),
            "confidence_threshold": float(confidence_threshold),
            "reference_annotation_origin": "human-assisted",
            "reference_strength": "expert-human-reference"
            if annotation_column == "handlabeller_final"
            else "human-reference",
        },
    )


def load_hollywood2_directory(
    root: str | Path,
    *,
    annotator: str = "final",
    identity_parser: IdentityParser | None = None,
    expected_sampling_rate_hz: float | None = 500.0,
    sampling_rate_tolerance: float = 0.05,
    coordinate_unit: str = "unverified",
) -> GazeFrame:
    """Load a Hollywood2EM ground-truth tree without guessing participant identities.

    ``identity_parser`` receives each ARFF path relative to the selected ground-truth directory and
    must return ``(participant_id, trial_id)``. Without it, every row receives the sentinel
    ``__unresolved__`` participant ID; this intentionally prevents accidental participant-held-out
    validation until the repository-specific identity mapping has been supplied and audited.
    """
    root_path = Path(root)
    if not root_path.exists():
        raise FileNotFoundError(root_path)
    data_root = root_path / "ground_truth" if (root_path / "ground_truth").is_dir() else root_path
    paths = sorted(data_root.rglob("*.arff"))
    if not paths:
        raise FileNotFoundError(f"No Hollywood2 ARFF files were found under {data_root}.")

    frames: list[GazeFrame] = []
    for path in paths:
        relative = path.relative_to(data_root)
        participant_id: str | None = None
        trial_id: str | None = str(relative.with_suffix(""))
        if identity_parser is not None:
            participant_id, trial_id = identity_parser(relative)
            if not str(participant_id).strip() or not str(trial_id).strip():
                raise SchemaError("Hollywood2 identity_parser returned an empty identity.")
        split = (
            relative.parts[0]
            if relative.parts and relative.parts[0] in {"train", "test"}
            else None
        )
        frames.append(
            load_hollywood2_arff(
                path,
                annotator=annotator,
                participant_id=participant_id,
                trial_id=trial_id,
                split=split,
                expected_sampling_rate_hz=expected_sampling_rate_hz,
                sampling_rate_tolerance=sampling_rate_tolerance,
                coordinate_unit=coordinate_unit,
            )
        )

    rates = {round(item.sampling_rate_hz, 9) for item in frames}
    if len(rates) != 1:
        raise SchemaError(f"Hollywood2 files contain inconsistent sampling rates: {sorted(rates)}")
    combined = pd.concat([item.data for item in frames], ignore_index=True)
    return GazeFrame(
        data=combined,
        sampling_rate_hz=frames[0].sampling_rate_hz,
        metadata={
            "source_dataset": "Hollywood2EM",
            "annotator": annotator,
            "n_source_files": len(paths),
            "participant_identity_resolved": identity_parser is not None,
            "identity_policy": (
                "caller-supplied parser" if identity_parser is not None else "unresolved sentinel"
            ),
            "coordinate_source_unit": str(coordinate_unit).strip().lower(),
            "coordinate_unit_verified": str(coordinate_unit).strip().lower() == "pixels",
            "canonical_coordinate_alias_only": str(coordinate_unit).strip().lower() != "pixels",
            "source_files": [str(path.relative_to(data_root)) for path in paths],
        },
    )
