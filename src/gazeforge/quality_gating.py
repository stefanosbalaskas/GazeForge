"""Time-varying motion-quality reliability weights for multimodal analysis."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .benchmarks import benchmark_fingerprint
from .exceptions import SchemaError
from .provenance import fingerprint_frame

_CERTIFICATE_SCHEMA = "gazeforge.motion-quality-certificate.v1"
_GATE_STATES = (
    "clean",
    "downweighted",
    "severe",
    "motion_unknown",
    "signal_missing",
)
_CLAIM_BOUNDARY = {
    "reliability_weighting_only": True,
    "removes_samples": False,
    "alters_signal_values": False,
    "corrects_motion_artifacts": False,
    "establishes_sensor_validity": False,
    "establishes_modality_contribution": False,
    "thresholds_empirically_validated": False,
    "requires_domain_threshold_justification": True,
}


@dataclass(frozen=True, slots=True)
class MotionQualityGateSpec:
    """Explicit thresholds and smoothing settings for a motion reliability gate.

    Thresholds use the units of ``motion_index``. For the bundled accelerometer
    index those units are acceleration-units per second because the index is a
    trailing RMS of vector jerk. GazeForge deliberately does not provide a
    universal threshold because accelerometer units, mounting, and tasks differ.
    """

    clean_threshold: float
    severe_threshold: float
    minimum_weight: float = 0.10
    smoothing_window_ms: float = 250.0
    threshold_basis: str = "user-specified-unvalidated"

    def __post_init__(self) -> None:
        clean = float(self.clean_threshold)
        severe = float(self.severe_threshold)
        minimum = float(self.minimum_weight)
        window = float(self.smoothing_window_ms)
        if not np.isfinite(clean) or clean < 0:
            raise ValueError("clean_threshold must be finite and non-negative.")
        if not np.isfinite(severe) or severe <= clean:
            raise ValueError("severe_threshold must be finite and greater than clean_threshold.")
        if not np.isfinite(minimum) or not 0.0 <= minimum <= 1.0:
            raise ValueError("minimum_weight must be finite and in [0, 1].")
        if not np.isfinite(window) or window <= 0:
            raise ValueError("smoothing_window_ms must be finite and positive.")
        if not isinstance(self.threshold_basis, str) or not self.threshold_basis.strip():
            raise ValueError("threshold_basis must be a non-empty string.")
        object.__setattr__(self, "clean_threshold", clean)
        object.__setattr__(self, "severe_threshold", severe)
        object.__setattr__(self, "minimum_weight", minimum)
        object.__setattr__(self, "smoothing_window_ms", window)
        object.__setattr__(self, "threshold_basis", self.threshold_basis.strip())

    def to_dict(self) -> dict[str, Any]:
        """Serialize the canonical gate specification."""
        return asdict(self)


def _require_columns(data: pd.DataFrame, columns: tuple[str, ...], *, purpose: str) -> None:
    missing = [column for column in columns if column not in data.columns]
    if missing:
        raise SchemaError(f"Missing columns for {purpose}: {missing}")


def _validate_column_names(columns: tuple[str, ...], *, purpose: str) -> None:
    if any(not isinstance(column, str) or not column for column in columns):
        raise ValueError(f"{purpose} column names must be non-empty strings.")
    if len(set(columns)) != len(columns):
        raise ValueError(f"{purpose} column names must be distinct.")


def _check_output_columns(
    data: pd.DataFrame,
    columns: tuple[str, ...],
    *,
    overwrite: bool,
    protected_columns: tuple[str, ...] = (),
) -> None:
    _validate_column_names(columns, purpose="Motion-quality output")
    protected = set(protected_columns)
    protected_collisions = [column for column in columns if column in protected]
    if protected_collisions:
        raise SchemaError(
            "Motion-quality output columns cannot overwrite protected input columns: "
            f"{protected_collisions}"
        )
    if overwrite:
        return
    collisions = [column for column in columns if column in data.columns]
    if collisions:
        raise SchemaError(
            "Motion-quality output columns already exist; set overwrite=True only after "
            f"intentional review: {collisions}"
        )


def derive_accelerometer_motion_index(
    data: pd.DataFrame,
    *,
    accel_cols: tuple[str, ...] = ("acc_x", "acc_y", "acc_z"),
    timestamp_col: str = "timestamp_ms",
    group_cols: tuple[str, ...] = ("participant_id", "trial_id"),
    smoothing_window_ms: float = 250.0,
    jerk_col: str = "motion_jerk",
    motion_index_col: str = "motion_index",
    overwrite: bool = False,
) -> pd.DataFrame:
    """Derive an auditable motion index from aligned accelerometer axes.

    The instantaneous index is the Euclidean norm of the vector acceleration
    derivative (vector jerk). The reported ``motion_index`` is a trailing RMS of
    jerk over ``smoothing_window_ms``. The first valid sample in every group has
    zero jerk. Rows whose motion transition cannot be evaluated remain missing;
    missing accelerometer evidence is never interpreted as a clean segment.

    Input order and source columns are preserved. ``overwrite=True`` may refresh
    prior motion-output columns, but output names can never alias timestamp,
    grouping, or accelerometer input columns.
    """
    _validate_column_names(accel_cols, purpose="Accelerometer")
    _validate_column_names(group_cols, purpose="Grouping")
    _validate_column_names((timestamp_col,), purpose="Timestamp")
    if not np.isfinite(float(smoothing_window_ms)) or float(smoothing_window_ms) <= 0:
        raise ValueError("smoothing_window_ms must be finite and positive.")

    required = (*group_cols, timestamp_col, *accel_cols)
    _require_columns(data, required, purpose="accelerometer motion indexing")
    _check_output_columns(
        data,
        (jerk_col, motion_index_col),
        overwrite=overwrite,
        protected_columns=required,
    )
    if data.empty:
        raise SchemaError("Accelerometer motion indexing requires at least one row.")

    work = data.reset_index(drop=True)
    jerk_values = np.full(len(work), np.nan, dtype=float)
    motion_values = np.full(len(work), np.nan, dtype=float)

    if group_cols:
        grouped_positions = work.groupby(
            list(group_cols), sort=False, dropna=False
        ).indices.values()
    else:
        grouped_positions = [np.arange(len(work), dtype=int)]

    window = pd.Timedelta(milliseconds=float(smoothing_window_ms))
    for positions_raw in grouped_positions:
        positions = np.asarray(positions_raw, dtype=int)
        part = work.iloc[positions]
        timestamps = pd.to_numeric(part[timestamp_col], errors="coerce").to_numpy(dtype=float)
        if not np.isfinite(timestamps).all():
            raise SchemaError("Motion timestamps must be finite within every group.")
        if len(timestamps) > 1 and np.any(np.diff(timestamps) <= 0):
            raise SchemaError("Motion timestamps must be strictly increasing within every group.")

        accel = part.loc[:, list(accel_cols)].apply(pd.to_numeric, errors="coerce").to_numpy(float)
        valid_accel = np.isfinite(accel).all(axis=1)
        jerk = np.full(len(part), np.nan, dtype=float)
        if len(part) and valid_accel[0]:
            jerk[0] = 0.0
        if len(part) > 1:
            dt_seconds = np.diff(timestamps) / 1000.0
            transitions_valid = valid_accel[1:] & valid_accel[:-1]
            deltas = np.diff(accel, axis=0)
            valid_rows = np.flatnonzero(transitions_valid) + 1
            if len(valid_rows):
                transition_indices = valid_rows - 1
                rates = deltas[transition_indices] / dt_seconds[transition_indices, None]
                jerk[valid_rows] = np.linalg.norm(rates, axis=1)

        elapsed = pd.to_timedelta(timestamps - timestamps[0], unit="ms")
        squared = pd.Series(jerk**2, index=elapsed)
        rms = np.sqrt(
            squared.rolling(window=window, min_periods=1).mean()
        ).to_numpy(dtype=float, copy=True)
        # A trailing window must not turn an unevaluable current transition into known motion.
        rms[~np.isfinite(jerk)] = np.nan
        jerk_values[positions] = jerk
        motion_values[positions] = rms

    out = data.copy()
    out[jerk_col] = jerk_values
    out[motion_index_col] = motion_values
    return out


def quality_weight_from_motion(
    motion_index: pd.Series | np.ndarray | list[float],
    *,
    clean_threshold: float,
    severe_threshold: float,
    minimum_weight: float = 0.10,
) -> pd.Series | np.ndarray:
    """Map a non-negative motion index to a bounded continuous reliability weight.

    Values at or below ``clean_threshold`` receive weight 1. Values at or above
    ``severe_threshold`` receive ``minimum_weight``. Intermediate values are
    linearly downweighted. Missing/non-finite motion remains missing rather than
    being silently treated as reliable.
    """
    spec = MotionQualityGateSpec(
        clean_threshold=clean_threshold,
        severe_threshold=severe_threshold,
        minimum_weight=minimum_weight,
    )
    is_series = isinstance(motion_index, pd.Series)
    index = motion_index.index if is_series else None
    values = pd.to_numeric(pd.Series(motion_index), errors="coerce").to_numpy(dtype=float)
    finite = np.isfinite(values)
    if np.any(values[finite] < 0):
        raise ValueError("motion_index must be non-negative where finite.")

    weights = np.full(len(values), np.nan, dtype=float)
    clean = finite & (values <= spec.clean_threshold)
    severe = finite & (values >= spec.severe_threshold)
    middle = finite & ~clean & ~severe
    weights[clean] = 1.0
    weights[severe] = spec.minimum_weight
    if np.any(middle):
        fraction = (values[middle] - spec.clean_threshold) / (
            spec.severe_threshold - spec.clean_threshold
        )
        weights[middle] = 1.0 - fraction * (1.0 - spec.minimum_weight)
    weights = np.clip(weights, 0.0, 1.0, out=weights, where=np.isfinite(weights))
    if is_series:
        return pd.Series(weights, index=index, name="quality_weight")
    return weights


def apply_motion_quality_gate(
    data: pd.DataFrame,
    *,
    spec: MotionQualityGateSpec,
    motion_index_col: str = "motion_index",
    modality: str,
    signal_cols: tuple[str, ...] = (),
    weight_col: str = "quality_weight",
    state_col: str = "quality_state",
    modality_col: str = "quality_modality",
    overwrite: bool = False,
) -> pd.DataFrame:
    """Append time-varying reliability weights without deleting or rewriting signals."""
    if not isinstance(modality, str) or not modality.strip():
        raise ValueError("modality must be a non-empty string.")
    _validate_column_names(signal_cols, purpose="Signal")
    _validate_column_names((motion_index_col,), purpose="Motion-index")
    _require_columns(data, (motion_index_col, *signal_cols), purpose="motion-quality gating")
    _check_output_columns(
        data,
        (weight_col, state_col, modality_col),
        overwrite=overwrite,
        protected_columns=(motion_index_col, *signal_cols),
    )

    motion = pd.to_numeric(data[motion_index_col], errors="coerce")
    values = motion.to_numpy(dtype=float)
    finite = np.isfinite(values)
    if np.any(values[finite] < 0):
        raise ValueError("motion_index must be non-negative where finite.")
    weights = np.array(
        quality_weight_from_motion(
            motion,
            clean_threshold=spec.clean_threshold,
            severe_threshold=spec.severe_threshold,
            minimum_weight=spec.minimum_weight,
        ),
        dtype=float,
        copy=True,
    )
    states = np.full(len(data), "motion_unknown", dtype=object)
    states[finite & (values <= spec.clean_threshold)] = "clean"
    states[
        finite & (values > spec.clean_threshold) & (values < spec.severe_threshold)
    ] = "downweighted"
    states[finite & (values >= spec.severe_threshold)] = "severe"

    if signal_cols:
        signal_missing = data.loc[:, list(signal_cols)].isna().any(axis=1).to_numpy(dtype=bool)
        weights[signal_missing] = 0.0
        states[signal_missing] = "signal_missing"

    out = data.copy()
    out[modality_col] = modality.strip()
    out[weight_col] = weights
    out[state_col] = states
    return out


def apply_accelerometer_quality_gate(
    data: pd.DataFrame,
    *,
    spec: MotionQualityGateSpec,
    modality: str,
    signal_cols: tuple[str, ...] = (),
    accel_cols: tuple[str, ...] = ("acc_x", "acc_y", "acc_z"),
    timestamp_col: str = "timestamp_ms",
    group_cols: tuple[str, ...] = ("participant_id", "trial_id"),
    jerk_col: str = "motion_jerk",
    motion_index_col: str = "motion_index",
    weight_col: str = "quality_weight",
    state_col: str = "quality_state",
    modality_col: str = "quality_modality",
    overwrite: bool = False,
) -> pd.DataFrame:
    """Derive vector-jerk motion and apply a continuous modality reliability gate."""
    _validate_column_names(signal_cols, purpose="Signal")
    _validate_column_names(accel_cols, purpose="Accelerometer")
    _validate_column_names(group_cols, purpose="Grouping")
    source_columns = (*group_cols, timestamp_col, *accel_cols, *signal_cols)
    _require_columns(data, source_columns, purpose="accelerometer quality gating")
    _check_output_columns(
        data,
        (jerk_col, motion_index_col, weight_col, state_col, modality_col),
        overwrite=overwrite,
        protected_columns=source_columns,
    )
    indexed = derive_accelerometer_motion_index(
        data,
        accel_cols=accel_cols,
        timestamp_col=timestamp_col,
        group_cols=group_cols,
        smoothing_window_ms=spec.smoothing_window_ms,
        jerk_col=jerk_col,
        motion_index_col=motion_index_col,
        overwrite=overwrite,
    )
    return apply_motion_quality_gate(
        indexed,
        spec=spec,
        motion_index_col=motion_index_col,
        modality=modality,
        signal_cols=signal_cols,
        weight_col=weight_col,
        state_col=state_col,
        modality_col=modality_col,
        overwrite=overwrite,
    )


def summarize_motion_quality(
    data: pd.DataFrame,
    *,
    group_cols: tuple[str, ...] = ("participant_id", "trial_id"),
    weight_col: str = "quality_weight",
    state_col: str = "quality_state",
    modality_col: str = "quality_modality",
) -> pd.DataFrame:
    """Summarize usability weights without interpreting them as artifact correction."""
    _validate_column_names(group_cols, purpose="Grouping")
    _validate_column_names((weight_col, state_col, modality_col), purpose="Quality summary")
    _require_columns(
        data,
        (*group_cols, weight_col, state_col, modality_col),
        purpose="motion-quality summary",
    )
    weights_all = pd.to_numeric(data[weight_col], errors="coerce").to_numpy(dtype=float)
    finite_all = np.isfinite(weights_all)
    if np.any((weights_all[finite_all] < 0.0) | (weights_all[finite_all] > 1.0)):
        raise ValueError("quality_weight must be in [0, 1] where finite.")
    unknown_states = sorted(set(data[state_col].astype(str)) - set(_GATE_STATES))
    if unknown_states:
        raise ValueError(f"Unknown motion-quality states: {unknown_states}")

    grouping = [*group_cols, modality_col]
    rows: list[dict[str, Any]] = []
    groups = data.groupby(grouping, sort=False, dropna=False)
    for keys, part in groups:
        if not isinstance(keys, tuple):
            keys = (keys,)
        weights = pd.to_numeric(part[weight_col], errors="coerce")
        finite = np.isfinite(weights.to_numpy(dtype=float))
        row = {column: value for column, value in zip(grouping, keys, strict=True)}
        row.update(
            n_samples=int(len(part)),
            n_known_weights=int(finite.sum()),
            n_unknown_weights=int((~finite).sum()),
            effective_weight_sum=float(weights[finite].sum()) if finite.any() else 0.0,
            mean_quality_weight=float(weights[finite].mean()) if finite.any() else None,
            min_quality_weight=float(weights[finite].min()) if finite.any() else None,
        )
        states = part[state_col].astype(str)
        for state in _GATE_STATES:
            row[f"{state}_fraction"] = float((states == state).mean())
        rows.append(row)
    return pd.DataFrame(rows)


def _global_quality_summary(
    gated: pd.DataFrame,
    *,
    weight_col: str,
    state_col: str,
) -> dict[str, Any]:
    weights = pd.to_numeric(gated[weight_col], errors="coerce")
    finite = np.isfinite(weights.to_numpy(dtype=float))
    states = gated[state_col].astype(str)
    return {
        "n_rows": int(len(gated)),
        "n_known_weights": int(finite.sum()),
        "n_unknown_weights": int((~finite).sum()),
        "effective_weight_sum": float(weights[finite].sum()) if finite.any() else 0.0,
        "mean_quality_weight": float(weights[finite].mean()) if finite.any() else None,
        "state_counts": {state: int((states == state).sum()) for state in _GATE_STATES},
    }


def build_motion_quality_certificate(
    data: pd.DataFrame,
    *,
    spec: MotionQualityGateSpec,
    modality: str,
    signal_cols: tuple[str, ...] = (),
    accel_cols: tuple[str, ...] = ("acc_x", "acc_y", "acc_z"),
    timestamp_col: str = "timestamp_ms",
    group_cols: tuple[str, ...] = ("participant_id", "trial_id"),
    jerk_col: str = "motion_jerk",
    motion_index_col: str = "motion_index",
    weight_col: str = "quality_weight",
    state_col: str = "quality_state",
    modality_col: str = "quality_modality",
) -> dict[str, Any]:
    """Build a replayable certificate for exact motion-quality gate inputs/settings."""
    gated = apply_accelerometer_quality_gate(
        data,
        spec=spec,
        modality=modality,
        signal_cols=signal_cols,
        accel_cols=accel_cols,
        timestamp_col=timestamp_col,
        group_cols=group_cols,
        jerk_col=jerk_col,
        motion_index_col=motion_index_col,
        weight_col=weight_col,
        state_col=state_col,
        modality_col=modality_col,
    )
    body = {
        "schema": _CERTIFICATE_SCHEMA,
        "input_fingerprint_sha256": fingerprint_frame(data),
        "output_fingerprint_sha256": fingerprint_frame(gated),
        "spec": spec.to_dict(),
        "gate_config": {
            "modality": modality.strip(),
            "signal_cols": list(signal_cols),
            "accel_cols": list(accel_cols),
            "timestamp_col": timestamp_col,
            "group_cols": list(group_cols),
            "jerk_col": jerk_col,
            "motion_index_col": motion_index_col,
            "weight_col": weight_col,
            "state_col": state_col,
            "modality_col": modality_col,
            "motion_index_definition": "trailing-rms-vector-jerk",
        },
        "summary": _global_quality_summary(
            gated,
            weight_col=weight_col,
            state_col=state_col,
        ),
        "claim_boundary": dict(_CLAIM_BOUNDARY),
    }
    return {**body, "certificate_fingerprint_sha256": benchmark_fingerprint(body)}


def validate_motion_quality_certificate(
    certificate: dict[str, Any],
    data: pd.DataFrame,
) -> bool:
    """Replay a motion-quality certificate from the exact bound input table."""
    if certificate.get("schema") != _CERTIFICATE_SCHEMA:
        raise ValueError("Unsupported motion-quality certificate schema.")
    fingerprint = certificate.get("certificate_fingerprint_sha256")
    if not isinstance(fingerprint, str) or len(fingerprint) != 64:
        raise ValueError("Motion-quality certificate fingerprint is missing or malformed.")
    body = {
        key: value
        for key, value in certificate.items()
        if key != "certificate_fingerprint_sha256"
    }
    if benchmark_fingerprint(body) != fingerprint:
        raise ValueError("Motion-quality certificate fingerprint mismatch.")
    if certificate.get("claim_boundary") != _CLAIM_BOUNDARY:
        raise ValueError("Motion-quality certificate claim boundary was promoted or altered.")

    spec_payload = certificate.get("spec")
    config = certificate.get("gate_config")
    if not isinstance(spec_payload, dict) or not isinstance(config, dict):
        raise ValueError("Motion-quality certificate is missing replay metadata.")
    spec = MotionQualityGateSpec(**spec_payload)
    rebuilt = build_motion_quality_certificate(
        data,
        spec=spec,
        modality=str(config.get("modality", "")),
        signal_cols=tuple(config.get("signal_cols") or ()),
        accel_cols=tuple(config.get("accel_cols") or ()),
        timestamp_col=str(config.get("timestamp_col", "")),
        group_cols=tuple(config.get("group_cols") or ()),
        jerk_col=str(config.get("jerk_col", "")),
        motion_index_col=str(config.get("motion_index_col", "")),
        weight_col=str(config.get("weight_col", "")),
        state_col=str(config.get("state_col", "")),
        modality_col=str(config.get("modality_col", "")),
    )
    if rebuilt != certificate:
        raise ValueError(
            "Motion-quality certificate does not replay from the exact input/settings."
        )
    return True


def freeze_motion_quality_certificate(
    certificate: dict[str, Any],
    path: str | Path,
    *,
    data: pd.DataFrame,
    overwrite: bool = False,
) -> Path:
    """Replay-validate and freeze a motion-quality certificate."""
    validate_motion_quality_certificate(certificate, data)
    target = Path(path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"Motion-quality certificate already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(certificate, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return target
