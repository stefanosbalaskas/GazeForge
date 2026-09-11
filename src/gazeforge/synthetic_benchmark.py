"""Known-truth synthetic gaze benchmarks with explicit artifact provenance."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score

from .benchmarks import BenchmarkDatasetCard, benchmark_fingerprint
from .provenance import fingerprint_frame

_CONTRACT_VERSION = "synthetic-gaze-benchmark-v1"
_CERTIFICATE_SCHEMA = "gazeforge.synthetic-recovery-certificate.v1"
_KEY_COLUMNS = ("participant_id", "trial_id", "sample_index")
_THRESHOLD_DIRECTIONS = {
    "coordinate_rmse_px": "max",
    "coordinate_mae_px": "max",
    "x_rmse_px": "max",
    "y_rmse_px": "max",
    "valid_coordinate_fraction": "min",
    "valid_event_fraction": "min",
    "event_accuracy": "min",
    "event_macro_f1": "min",
}
_CLAIM_BOUNDARY = {
    "synthetic_validation_only": True,
    "empirical_device_validity": False,
    "subject_generalization": False,
    "cross_dataset_generalization": False,
    "human_reference_ground_truth": False,
    "eligible_for_public_frozen_empirical_evidence": False,
}


@dataclass(frozen=True, slots=True)
class SyntheticGazeSpec:
    """Configuration for a deterministic known-truth gaze simulation."""

    n_participants: int = 8
    n_trials: int = 4
    samples_per_trial: int = 300
    sampling_rate_hz: float = 60.0
    screen_size_px: tuple[int, int] = (1920, 1080)
    fixation_duration_samples: int = 48
    saccade_duration_samples: int = 6
    fixation_sd_px: float = 4.0
    measurement_noise_sd_px: float = 8.0
    pupil_noise_sd_mm: float = 0.08
    calibration_bias_px: tuple[float, float] = (12.0, -8.0)
    dropout_probability: float = 0.015
    random_state: int = 42

    def __post_init__(self) -> None:
        """Reject impossible or ambiguous simulation settings."""
        if self.n_participants < 1:
            raise ValueError("n_participants must be at least 1.")
        if self.n_trials < 1:
            raise ValueError("n_trials must be at least 1.")
        if self.samples_per_trial < 2:
            raise ValueError("samples_per_trial must be at least 2.")
        if not np.isfinite(self.sampling_rate_hz) or self.sampling_rate_hz <= 0:
            raise ValueError("sampling_rate_hz must be finite and positive.")
        if len(self.screen_size_px) != 2 or any(value <= 0 for value in self.screen_size_px):
            raise ValueError("screen_size_px must contain two positive dimensions.")
        if self.fixation_duration_samples < 1:
            raise ValueError("fixation_duration_samples must be at least 1.")
        if self.saccade_duration_samples < 1:
            raise ValueError("saccade_duration_samples must be at least 1.")
        for name in ("fixation_sd_px", "measurement_noise_sd_px", "pupil_noise_sd_mm"):
            value = float(getattr(self, name))
            if value < 0 or not np.isfinite(value):
                raise ValueError(f"{name} must be finite and non-negative.")
        if len(self.calibration_bias_px) != 2 or not all(
            np.isfinite(value) for value in self.calibration_bias_px
        ):
            raise ValueError("calibration_bias_px must contain two finite values.")
        if not 0.0 <= self.dropout_probability < 1.0:
            raise ValueError("dropout_probability must be in [0, 1).")
        if self.random_state < 0:
            raise ValueError("random_state must be non-negative.")

    def to_dict(self) -> dict[str, Any]:
        """Serialize the specification to canonical JSON-compatible values."""
        payload = asdict(self)
        payload["screen_size_px"] = list(self.screen_size_px)
        payload["calibration_bias_px"] = list(self.calibration_bias_px)
        return payload


@dataclass(slots=True)
class SyntheticGazeBenchmarkRun:
    """One known-truth simulation and its separately corrupted observation."""

    spec: SyntheticGazeSpec
    truth: pd.DataFrame
    observed_signal: pd.DataFrame
    artifact: pd.DataFrame
    event_truth: pd.DataFrame
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def dataset_card(self) -> BenchmarkDatasetCard:
        """Describe this run as synthetic known-truth method-validation evidence."""
        return synthetic_known_truth_gaze_card(self.spec)

    @property
    def contract_fingerprint_sha256(self) -> str:
        """Fingerprint the complete simulation contract and generated tables."""
        return benchmark_fingerprint(
            {
                "contract_version": _CONTRACT_VERSION,
                "spec": self.spec.to_dict(),
                "truth_sha256": fingerprint_frame(self.truth),
                "observed_signal_sha256": fingerprint_frame(self.observed_signal),
                "artifact_sha256": fingerprint_frame(self.artifact),
                "event_truth_sha256": fingerprint_frame(self.event_truth),
                "metadata": self.metadata,
            }
        )


def synthetic_known_truth_gaze_card(
    spec: SyntheticGazeSpec | None = None,
) -> BenchmarkDatasetCard:
    """Return the fail-closed dataset card for known-truth simulation."""
    spec = spec or SyntheticGazeSpec()
    return BenchmarkDatasetCard(
        name="GazeForge known-truth synthetic gaze",
        version=_CONTRACT_VERSION,
        source="deterministic GazeForge generator",
        license="MIT-generated synthetic data",
        task="coordinate and eye-event recovery against exact latent truth",
        sampling_rates_hz=[float(spec.sampling_rate_hz)],
        participant_count=int(spec.n_participants),
        split_unit="participant_id",
        validation_scope="synthetic-known-truth-method-validation",
        annotation_origin="synthetic",
        sampling_origin="synthetic",
        reference_strength="synthetic-known-truth",
        reference_description=(
            "Exact simulator latent coordinates and event states; not human or device ground truth."
        ),
        notes=[
            "Supports recovery-error validation only under the simulator's generative assumptions.",
            "Does not establish empirical device, subject, or cross-dataset validity.",
        ],
    )


def _event_schedule(
    spec: SyntheticGazeSpec,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    width, height = spec.screen_size_px
    targets = np.column_stack(
        [
            rng.uniform(width * 0.12, width * 0.88, size=16),
            rng.uniform(height * 0.12, height * 0.88, size=16),
        ]
    )
    labels = np.empty(spec.samples_per_trial, dtype=object)
    latent = np.empty((spec.samples_per_trial, 2), dtype=float)
    cursor = target_index = 0
    current = targets[0]
    while cursor < spec.samples_per_trial:
        stop = min(cursor + spec.fixation_duration_samples, spec.samples_per_trial)
        latent[cursor:stop] = current + rng.normal(
            0.0, spec.fixation_sd_px, size=(stop - cursor, 2)
        )
        labels[cursor:stop] = "fixation"
        cursor = stop
        if cursor >= spec.samples_per_trial:
            break
        target_index = (target_index + 1) % len(targets)
        destination = targets[target_index]
        stop = min(cursor + spec.saccade_duration_samples, spec.samples_per_trial)
        n_saccade = stop - cursor
        progress = np.arange(1, n_saccade + 1, dtype=float) / spec.saccade_duration_samples
        smooth = np.clip(progress, 0.0, 1.0) ** 2
        smooth *= 3.0 - 2.0 * np.clip(progress, 0.0, 1.0)
        latent[cursor:stop] = current + (destination - current) * smooth[:, None]
        labels[cursor:stop] = "saccade"
        cursor = stop
        current = destination
    latent[:, 0] = np.clip(latent[:, 0], 0.0, float(width))
    latent[:, 1] = np.clip(latent[:, 1], 0.0, float(height))
    return latent, labels


def _event_segments(truth: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (participant_id, trial_id), group in truth.groupby(
        ["participant_id", "trial_id"], sort=False
    ):
        labels = group["event_label"].astype(str).to_numpy()
        indices = group["sample_index"].to_numpy(dtype=int)
        times = group["timestamp_ms"].to_numpy(dtype=float)
        start = 0
        event_number = 1
        for stop in range(1, len(group) + 1):
            if stop < len(group) and labels[stop] == labels[start]:
                continue
            rows.append(
                {
                    "participant_id": participant_id,
                    "trial_id": trial_id,
                    "event_id": f"{participant_id}:{trial_id}:E{event_number:03d}",
                    "event_label": labels[start],
                    "start_sample_index": int(indices[start]),
                    "end_sample_index": int(indices[stop - 1]),
                    "start_timestamp_ms": float(times[start]),
                    "end_timestamp_ms": float(times[stop - 1]),
                    "n_samples": int(stop - start),
                }
            )
            event_number += 1
            start = stop
    return pd.DataFrame(rows)


def simulate_known_truth_gaze(
    spec: SyntheticGazeSpec | None = None,
) -> SyntheticGazeBenchmarkRun:
    """Generate exact latent truth, an artifact ledger, and corrupted observations."""
    spec = spec or SyntheticGazeSpec()
    rng = np.random.default_rng(spec.random_state)
    truth_rows: list[dict[str, Any]] = []
    artifact_rows: list[dict[str, Any]] = []
    observed_rows: list[dict[str, Any]] = []
    dt_ms = 1000.0 / spec.sampling_rate_hz
    bias_x, bias_y = spec.calibration_bias_px

    for participant in range(spec.n_participants):
        participant_id = f"P{participant + 1:03d}"
        for trial in range(spec.n_trials):
            trial_id = f"T{trial + 1:02d}"
            latent_xy, labels = _event_schedule(spec, rng)
            pupil_truth = 3.2 + 0.15 * (labels == "saccade") + rng.normal(
                0.0, 0.025, size=spec.samples_per_trial
            )
            coordinate_noise = rng.normal(
                0.0, spec.measurement_noise_sd_px, size=(spec.samples_per_trial, 2)
            )
            pupil_noise = rng.normal(0.0, spec.pupil_noise_sd_mm, spec.samples_per_trial)
            dropout = rng.random(spec.samples_per_trial) < spec.dropout_probability

            for sample_index in range(spec.samples_per_trial):
                timestamp_ms = float(sample_index * dt_ms)
                x_true, y_true = map(float, latent_xy[sample_index])
                pupil_true = float(pupil_truth[sample_index])
                noise_x, noise_y = map(float, coordinate_noise[sample_index])
                is_dropout = bool(dropout[sample_index])
                x_observed = x_true + noise_x + float(bias_x)
                y_observed = y_true + noise_y + float(bias_y)
                pupil_observed = pupil_true + float(pupil_noise[sample_index])
                if is_dropout:
                    x_observed = y_observed = pupil_observed = np.nan
                keys = {
                    "participant_id": participant_id,
                    "trial_id": trial_id,
                    "sample_index": sample_index,
                    "timestamp_ms": timestamp_ms,
                }
                truth_rows.append(
                    {
                        **keys,
                        "x_true_px": x_true,
                        "y_true_px": y_true,
                        "pupil_true_mm": pupil_true,
                        "event_label": str(labels[sample_index]),
                    }
                )
                artifact_rows.append(
                    {
                        **keys,
                        "is_dropout": is_dropout,
                        "measurement_noise_x_px": noise_x,
                        "measurement_noise_y_px": noise_y,
                        "pupil_noise_mm": float(pupil_noise[sample_index]),
                        "calibration_bias_x_px": float(bias_x),
                        "calibration_bias_y_px": float(bias_y),
                    }
                )
                observed_rows.append(
                    {**keys, "x_px": x_observed, "y_px": y_observed, "pupil": pupil_observed}
                )

    truth = pd.DataFrame(truth_rows)
    metadata = {
        "contract_version": _CONTRACT_VERSION,
        "seed": int(spec.random_state),
        "sampling_rate_hz": float(spec.sampling_rate_hz),
        "truth_is_separate_from_observation": True,
        "artifact_model": {
            "measurement_noise": "independent Gaussian coordinate noise",
            "calibration_bias": "constant additive x/y bias",
            "dropout": "independent sample missingness",
            "pupil_noise": "independent Gaussian additive noise",
        },
        "expected_metric": [
            "coordinate_rmse_px",
            "coordinate_mae_px",
            "valid_coordinate_fraction",
            "event_accuracy_if_supplied",
            "event_macro_f1_if_supplied",
        ],
        "claim_boundary": {
            "synthetic_validation_only": True,
            "empirical_device_validity": False,
            "subject_generalization": False,
            "cross_dataset_generalization": False,
        },
    }
    return SyntheticGazeBenchmarkRun(
        spec=spec,
        truth=truth,
        observed_signal=pd.DataFrame(observed_rows),
        artifact=pd.DataFrame(artifact_rows),
        event_truth=_event_segments(truth),
        metadata=metadata,
    )


def _validate_estimate_keys(run: SyntheticGazeBenchmarkRun, estimates: pd.DataFrame) -> None:
    missing = [column for column in _KEY_COLUMNS if column not in estimates.columns]
    if missing:
        raise ValueError(f"Recovery estimates are missing key columns: {missing}")
    if estimates.duplicated(list(_KEY_COLUMNS)).any():
        raise ValueError("Recovery estimates contain duplicate participant/trial/sample keys.")
    expected = set(map(tuple, run.truth.loc[:, list(_KEY_COLUMNS)].astype(object).to_numpy()))
    observed = set(map(tuple, estimates.loc[:, list(_KEY_COLUMNS)].astype(object).to_numpy()))
    if expected != observed:
        raise ValueError(
            "Recovery estimates must contain exactly the synthetic truth keys; "
            f"missing={len(expected - observed)}, extra={len(observed - expected)}."
        )


def score_synthetic_gaze_recovery(
    run: SyntheticGazeBenchmarkRun,
    estimates: pd.DataFrame,
    *,
    x_col: str = "x_px",
    y_col: str = "y_px",
    event_col: str | None = None,
) -> dict[str, Any]:
    """Score estimates against exact coordinates and optional sample-level event truth."""
    _validate_estimate_keys(run, estimates)
    selected_columns = [x_col, y_col]
    if event_col is not None:
        selected_columns.append(event_col)
    if len(set(selected_columns)) != len(selected_columns):
        raise ValueError("Recovery estimate column selectors must be distinct.")
    for column in (x_col, y_col):
        if column not in estimates.columns:
            raise ValueError(f"Recovery estimates are missing coordinate column: {column!r}")
    columns = [*_KEY_COLUMNS, x_col, y_col]
    rename_map = {x_col: "__estimate_x", y_col: "__estimate_y"}
    if event_col is not None:
        if event_col not in estimates.columns:
            raise ValueError(f"Recovery estimates are missing event column: {event_col!r}")
        columns.append(event_col)
        rename_map[event_col] = "__estimate_event"
    estimate_view = estimates.loc[:, columns].rename(columns=rename_map)
    merged = run.truth.merge(
        estimate_view,
        on=list(_KEY_COLUMNS),
        how="left",
        validate="one_to_one",
        sort=False,
    )
    x_est = pd.to_numeric(merged["__estimate_x"], errors="coerce").to_numpy(dtype=float)
    y_est = pd.to_numeric(merged["__estimate_y"], errors="coerce").to_numpy(dtype=float)
    valid = np.isfinite(x_est) & np.isfinite(y_est)
    metrics: dict[str, Any] = {
        "n_truth_samples": int(len(merged)),
        "n_valid_coordinate_estimates": int(valid.sum()),
        "valid_coordinate_fraction": float(valid.mean()),
    }
    if valid.any():
        dx = x_est[valid] - merged.loc[valid, "x_true_px"].to_numpy(dtype=float)
        dy = y_est[valid] - merged.loc[valid, "y_true_px"].to_numpy(dtype=float)
        distance = np.hypot(dx, dy)
        metrics.update(
            {
                "coordinate_rmse_px": float(np.sqrt(np.mean(distance**2))),
                "coordinate_mae_px": float(np.mean(distance)),
                "x_rmse_px": float(np.sqrt(np.mean(dx**2))),
                "y_rmse_px": float(np.sqrt(np.mean(dy**2))),
            }
        )
    else:
        metrics.update(
            {
                "coordinate_rmse_px": None,
                "coordinate_mae_px": None,
                "x_rmse_px": None,
                "y_rmse_px": None,
            }
        )
    if event_col is not None:
        predicted = merged["__estimate_event"].astype("string")
        event_valid = predicted.notna()
        metrics["n_valid_event_estimates"] = int(event_valid.sum())
        metrics["valid_event_fraction"] = float(event_valid.mean())
        if event_valid.any():
            truth = merged.loc[event_valid, "event_label"].astype(str)
            estimate = predicted.loc[event_valid].astype(str)
            metrics["event_accuracy"] = float(accuracy_score(truth, estimate))
            metrics["event_macro_f1"] = float(
                f1_score(
                    truth,
                    estimate,
                    labels=["fixation", "saccade"],
                    average="macro",
                    zero_division=0.0,
                )
            )
        else:
            metrics["event_accuracy"] = None
            metrics["event_macro_f1"] = None
    return metrics


def _threshold_checks(
    metrics: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, bool]:
    unknown = sorted(set(thresholds) - set(_THRESHOLD_DIRECTIONS))
    if unknown:
        raise ValueError(f"Unknown synthetic recovery thresholds: {unknown}")
    nonfinite = sorted(name for name, value in thresholds.items() if not np.isfinite(float(value)))
    if nonfinite:
        raise ValueError(f"Synthetic recovery thresholds must be finite: {nonfinite}")
    checks: dict[str, bool] = {}
    for name, threshold in thresholds.items():
        raw_value = metrics.get(name)
        if raw_value is None or not np.isfinite(float(raw_value)):
            checks[name] = False
        elif _THRESHOLD_DIRECTIONS[name] == "max":
            checks[name] = float(raw_value) <= float(threshold)
        else:
            checks[name] = float(raw_value) >= float(threshold)
    return checks


def build_synthetic_recovery_certificate(
    run: SyntheticGazeBenchmarkRun,
    estimates: pd.DataFrame,
    *,
    estimator_name: str,
    x_col: str = "x_px",
    y_col: str = "y_px",
    event_col: str | None = None,
    thresholds: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Bind simulation, estimates, metrics, thresholds, and scientific claim limits."""
    if not isinstance(estimator_name, str) or not estimator_name.strip():
        raise ValueError("estimator_name must be non-empty.")
    metrics = score_synthetic_gaze_recovery(
        run, estimates, x_col=x_col, y_col=y_col, event_col=event_col
    )
    thresholds = dict(thresholds or {})
    checks = _threshold_checks(metrics, thresholds)
    body = {
        "schema": _CERTIFICATE_SCHEMA,
        "contract_fingerprint_sha256": run.contract_fingerprint_sha256,
        "truth_sha256": fingerprint_frame(run.truth),
        "observed_signal_sha256": fingerprint_frame(run.observed_signal),
        "artifact_sha256": fingerprint_frame(run.artifact),
        "event_truth_sha256": fingerprint_frame(run.event_truth),
        "estimate_sha256": fingerprint_frame(estimates),
        "seed": int(run.spec.random_state),
        "sampling_rate_hz": float(run.spec.sampling_rate_hz),
        "dataset_card": run.dataset_card.to_dict(),
        "estimator": {
            "name": estimator_name.strip(),
            "x_col": x_col,
            "y_col": y_col,
            "event_col": event_col,
        },
        "metrics": metrics,
        "thresholds": thresholds,
        "threshold_checks": checks,
        "thresholds_passed": bool(all(checks.values())) if checks else None,
        "claim_boundary": dict(_CLAIM_BOUNDARY),
    }
    return {**body, "certificate_fingerprint_sha256": benchmark_fingerprint(body)}


def validate_synthetic_recovery_certificate(
    certificate: dict[str, Any],
    *,
    run: SyntheticGazeBenchmarkRun | None = None,
    estimates: pd.DataFrame | None = None,
) -> bool:
    """Validate integrity, closed claims, and optional exact-input replay."""
    if estimates is not None and run is None:
        raise ValueError("estimates require the matching synthetic benchmark run.")
    if certificate.get("schema") != _CERTIFICATE_SCHEMA:
        raise ValueError("Unsupported synthetic recovery certificate schema.")
    fingerprint = certificate.get("certificate_fingerprint_sha256")
    if not isinstance(fingerprint, str) or len(fingerprint) != 64:
        raise ValueError("Synthetic recovery certificate fingerprint is missing or malformed.")
    body = {
        key: value
        for key, value in certificate.items()
        if key != "certificate_fingerprint_sha256"
    }
    if benchmark_fingerprint(body) != fingerprint:
        raise ValueError("Synthetic recovery certificate fingerprint mismatch.")
    if certificate.get("claim_boundary") != _CLAIM_BOUNDARY:
        raise ValueError("Synthetic recovery certificate claim boundary was promoted or altered.")
    card = certificate.get("dataset_card")
    if not isinstance(card, dict) or (
        card.get("annotation_origin") != "synthetic"
        or card.get("sampling_origin") != "synthetic"
        or card.get("reference_strength") != "synthetic-known-truth"
        or card.get("validation_scope") != "synthetic-known-truth-method-validation"
    ):
        raise ValueError("Synthetic recovery certificate dataset-card semantics are invalid.")
    expected_checks = _threshold_checks(
        dict(certificate.get("metrics") or {}),
        dict(certificate.get("thresholds") or {}),
    )
    if certificate.get("threshold_checks") != expected_checks:
        raise ValueError("Synthetic recovery certificate threshold checks are inconsistent.")
    expected_pass = bool(all(expected_checks.values())) if expected_checks else None
    if certificate.get("thresholds_passed") is not expected_pass:
        raise ValueError("Synthetic recovery certificate threshold status is inconsistent.")

    if run is not None:
        expected_bindings = {
            "contract_fingerprint_sha256": run.contract_fingerprint_sha256,
            "truth_sha256": fingerprint_frame(run.truth),
            "observed_signal_sha256": fingerprint_frame(run.observed_signal),
            "artifact_sha256": fingerprint_frame(run.artifact),
            "event_truth_sha256": fingerprint_frame(run.event_truth),
            "seed": int(run.spec.random_state),
            "sampling_rate_hz": float(run.spec.sampling_rate_hz),
            "dataset_card": run.dataset_card.to_dict(),
        }
        for key, expected in expected_bindings.items():
            if certificate.get(key) != expected:
                raise ValueError(f"Synthetic recovery certificate does not match run field: {key}")
    if estimates is not None:
        estimator = certificate.get("estimator")
        if not isinstance(estimator, dict):
            raise ValueError("Synthetic recovery certificate is missing estimator metadata.")
        rebuilt = build_synthetic_recovery_certificate(
            run,
            estimates,
            estimator_name=str(estimator.get("name", "")),
            x_col=str(estimator.get("x_col", "x_px")),
            y_col=str(estimator.get("y_col", "y_px")),
            event_col=estimator.get("event_col"),
            thresholds=dict(certificate.get("thresholds") or {}),
        )
        if rebuilt != certificate:
            raise ValueError("Synthetic recovery certificate does not replay from exact inputs.")
    return True


def freeze_synthetic_recovery_certificate(
    certificate: dict[str, Any],
    path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Validate and freeze a deterministic certificate without overwriting by default."""
    validate_synthetic_recovery_certificate(certificate)
    target = Path(path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"Synthetic recovery certificate already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(certificate, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return target
