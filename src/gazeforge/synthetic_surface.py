"""Deterministic multi-condition robustness surfaces for synthetic known-truth validation."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from itertools import product
from math import prod
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .benchmarks import benchmark_fingerprint
from .provenance import fingerprint_frame
from .synthetic_benchmark import (
    SyntheticGazeSpec,
    build_synthetic_recovery_certificate,
    simulate_known_truth_gaze,
    validate_synthetic_recovery_certificate,
)

_SURFACE_SCHEMA = "gazeforge.synthetic-recovery-surface.v1"
_CONDITION_SCHEMA = "gazeforge.synthetic-recovery-surface-condition.v1"
_SURFACE_CLAIM_BOUNDARY = {
    "synthetic_validation_only": True,
    "empirical_device_validity": False,
    "subject_generalization": False,
    "cross_dataset_generalization": False,
    "human_reference_ground_truth": False,
    "eligible_for_public_frozen_empirical_evidence": False,
}
_SUMMARY_METRICS = (
    "coordinate_rmse_px",
    "coordinate_mae_px",
    "x_rmse_px",
    "y_rmse_px",
    "valid_coordinate_fraction",
    "valid_event_fraction",
    "event_accuracy",
    "event_macro_f1",
)
Estimator = Callable[[pd.DataFrame], pd.DataFrame]


def _float_axis(
    values: Sequence[float] | None,
    fallback: float,
    *,
    name: str,
) -> tuple[float, ...]:
    raw = (fallback,) if values is None else tuple(values)
    if not raw:
        raise ValueError(f"{name} cannot be empty.")
    cleaned: list[float] = []
    for value in raw:
        numeric = float(value)
        if not np.isfinite(numeric):
            raise ValueError(f"{name} values must be finite.")
        cleaned.append(numeric)
    return tuple(sorted(set(cleaned)))


def _integer_axis(
    values: Sequence[int] | None,
    fallback: int,
    *,
    name: str,
) -> tuple[int, ...]:
    raw = (fallback,) if values is None else tuple(values)
    if not raw:
        raise ValueError(f"{name} cannot be empty.")
    cleaned: list[int] = []
    for value in raw:
        numeric = int(value)
        if float(value) != float(numeric):
            raise ValueError(f"{name} values must be integers.")
        cleaned.append(numeric)
    return tuple(sorted(set(cleaned)))


def _bias_axis(
    values: Sequence[Sequence[float]] | None,
    fallback: tuple[float, float],
) -> tuple[tuple[float, float], ...]:
    raw: Sequence[Sequence[float]] = (fallback,) if values is None else values
    if not raw:
        raise ValueError("calibration_biases_px cannot be empty.")
    cleaned: list[tuple[float, float]] = []
    for pair in raw:
        if len(pair) != 2:
            raise ValueError("Each calibration bias must contain exactly two values.")
        x, y = float(pair[0]), float(pair[1])
        if not np.isfinite(x) or not np.isfinite(y):
            raise ValueError("Calibration-bias values must be finite.")
        cleaned.append((x, y))
    return tuple(sorted(set(cleaned)))


@dataclass(frozen=True, slots=True)
class SyntheticGazeSurfaceSpec:
    """A deterministic full-factorial robustness design around a base simulator spec.

    Any axis left as ``None`` inherits the corresponding value from ``base_spec``. Axes are
    normalized to sorted unique values before expansion, so semantically identical designs have
    the same condition inventory regardless of caller ordering or duplicate entries.
    """

    base_spec: SyntheticGazeSpec = field(default_factory=SyntheticGazeSpec)
    sampling_rates_hz: tuple[float, ...] | None = None
    measurement_noise_sd_px: tuple[float, ...] | None = None
    calibration_biases_px: tuple[tuple[float, float], ...] | None = None
    dropout_probabilities: tuple[float, ...] | None = None
    fixation_duration_samples: tuple[int, ...] | None = None
    saccade_duration_samples: tuple[int, ...] | None = None
    random_states: tuple[int, ...] | None = None
    max_conditions: int = 256

    def __post_init__(self) -> None:
        if not isinstance(self.base_spec, SyntheticGazeSpec):
            raise TypeError("base_spec must be a SyntheticGazeSpec.")
        if self.max_conditions < 1:
            raise ValueError("max_conditions must be at least 1.")
        # Force validation and explosion checking at construction time rather than at execution.
        axes = self.normalized_axes()
        count = prod(len(values) for values in axes.values())
        if count > self.max_conditions:
            raise ValueError(
                "Synthetic robustness surface exceeds max_conditions: "
                f"requested={count}, max_conditions={self.max_conditions}."
            )

    def normalized_axes(self) -> dict[str, tuple[Any, ...]]:
        """Return validated, sorted, duplicate-free axis values."""
        axes: dict[str, tuple[Any, ...]] = {
            "sampling_rate_hz": _float_axis(
                self.sampling_rates_hz,
                self.base_spec.sampling_rate_hz,
                name="sampling_rates_hz",
            ),
            "measurement_noise_sd_px": _float_axis(
                self.measurement_noise_sd_px,
                self.base_spec.measurement_noise_sd_px,
                name="measurement_noise_sd_px",
            ),
            "calibration_bias_px": _bias_axis(
                self.calibration_biases_px,
                self.base_spec.calibration_bias_px,
            ),
            "dropout_probability": _float_axis(
                self.dropout_probabilities,
                self.base_spec.dropout_probability,
                name="dropout_probabilities",
            ),
            "fixation_duration_samples": _integer_axis(
                self.fixation_duration_samples,
                self.base_spec.fixation_duration_samples,
                name="fixation_duration_samples",
            ),
            "saccade_duration_samples": _integer_axis(
                self.saccade_duration_samples,
                self.base_spec.saccade_duration_samples,
                name="saccade_duration_samples",
            ),
            "random_state": _integer_axis(
                self.random_states,
                self.base_spec.random_state,
                name="random_states",
            ),
        }
        # Reuse SyntheticGazeSpec's scientific guards for every axis value before execution.
        for rate in axes["sampling_rate_hz"]:
            replace(self.base_spec, sampling_rate_hz=float(rate))
        for noise in axes["measurement_noise_sd_px"]:
            replace(self.base_spec, measurement_noise_sd_px=float(noise))
        for bias in axes["calibration_bias_px"]:
            replace(self.base_spec, calibration_bias_px=tuple(bias))
        for dropout in axes["dropout_probability"]:
            replace(self.base_spec, dropout_probability=float(dropout))
        for duration in axes["fixation_duration_samples"]:
            replace(self.base_spec, fixation_duration_samples=int(duration))
        for duration in axes["saccade_duration_samples"]:
            replace(self.base_spec, saccade_duration_samples=int(duration))
        for seed in axes["random_state"]:
            replace(self.base_spec, random_state=int(seed))
        return axes

    @property
    def condition_count(self) -> int:
        """Return the full-factorial condition count after axis normalization."""
        return int(prod(len(values) for values in self.normalized_axes().values()))

    def to_dict(self) -> dict[str, Any]:
        """Serialize the normalized surface design to canonical JSON-compatible values."""
        axes = self.normalized_axes()
        return {
            "base_spec": self.base_spec.to_dict(),
            "axes": {
                "sampling_rate_hz": list(axes["sampling_rate_hz"]),
                "measurement_noise_sd_px": list(axes["measurement_noise_sd_px"]),
                "calibration_bias_px": [list(pair) for pair in axes["calibration_bias_px"]],
                "dropout_probability": list(axes["dropout_probability"]),
                "fixation_duration_samples": list(axes["fixation_duration_samples"]),
                "saccade_duration_samples": list(axes["saccade_duration_samples"]),
                "random_state": list(axes["random_state"]),
            },
            "max_conditions": int(self.max_conditions),
            "condition_count": self.condition_count,
            "design": "full-factorial-synthetic-known-truth-robustness-surface",
            "common_random_numbers_within_seed": True,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> SyntheticGazeSurfaceSpec:
        """Reconstruct a surface design from its serialized representation."""
        if not isinstance(payload, dict):
            raise TypeError("surface_spec must be an object.")
        base_payload = dict(payload.get("base_spec") or {})
        if "screen_size_px" in base_payload:
            base_payload["screen_size_px"] = tuple(base_payload["screen_size_px"])
        if "calibration_bias_px" in base_payload:
            base_payload["calibration_bias_px"] = tuple(base_payload["calibration_bias_px"])
        base = SyntheticGazeSpec(**base_payload)
        axes = dict(payload.get("axes") or {})
        biases = axes.get("calibration_bias_px")
        return cls(
            base_spec=base,
            sampling_rates_hz=tuple(axes.get("sampling_rate_hz") or ()),
            measurement_noise_sd_px=tuple(axes.get("measurement_noise_sd_px") or ()),
            calibration_biases_px=(
                tuple(tuple(pair) for pair in biases) if biases is not None else None
            ),
            dropout_probabilities=tuple(axes.get("dropout_probability") or ()),
            fixation_duration_samples=tuple(axes.get("fixation_duration_samples") or ()),
            saccade_duration_samples=tuple(axes.get("saccade_duration_samples") or ()),
            random_states=tuple(axes.get("random_state") or ()),
            max_conditions=int(payload.get("max_conditions", 256)),
        )


@dataclass(frozen=True, slots=True)
class SyntheticSurfaceCondition:
    """One deterministic simulator condition in a robustness surface."""

    condition_id: str
    spec: SyntheticGazeSpec
    condition_spec_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "condition_id": self.condition_id,
            "condition_spec_sha256": self.condition_spec_sha256,
            "spec": self.spec.to_dict(),
        }


@dataclass(slots=True)
class SyntheticRecoverySurfaceResult:
    """Condition ledger plus a fingerprinted multi-condition synthetic certificate."""

    condition_ledger: pd.DataFrame
    surface_certificate: dict[str, Any]

    @property
    def surface_fingerprint_sha256(self) -> str:
        return str(self.surface_certificate["surface_fingerprint_sha256"])


def _condition_fingerprint(spec: SyntheticGazeSpec) -> str:
    return benchmark_fingerprint({"schema": _CONDITION_SCHEMA, "spec": spec.to_dict()})


def expand_synthetic_gaze_surface(
    surface_spec: SyntheticGazeSurfaceSpec,
) -> tuple[SyntheticSurfaceCondition, ...]:
    """Expand a normalized full-factorial design into deterministic simulator conditions."""
    if not isinstance(surface_spec, SyntheticGazeSurfaceSpec):
        raise TypeError("surface_spec must be a SyntheticGazeSurfaceSpec.")
    axes = surface_spec.normalized_axes()
    names = tuple(axes)
    conditions: list[SyntheticSurfaceCondition] = []
    seen_ids: set[str] = set()
    for values in product(*(axes[name] for name in names)):
        settings = dict(zip(names, values, strict=True))
        spec = replace(
            surface_spec.base_spec,
            sampling_rate_hz=float(settings["sampling_rate_hz"]),
            measurement_noise_sd_px=float(settings["measurement_noise_sd_px"]),
            calibration_bias_px=tuple(settings["calibration_bias_px"]),
            dropout_probability=float(settings["dropout_probability"]),
            fixation_duration_samples=int(settings["fixation_duration_samples"]),
            saccade_duration_samples=int(settings["saccade_duration_samples"]),
            random_state=int(settings["random_state"]),
        )
        fingerprint = _condition_fingerprint(spec)
        condition_id = f"condition-{fingerprint[:16]}"
        if condition_id in seen_ids:
            raise RuntimeError("Synthetic surface condition identifier collision.")
        seen_ids.add(condition_id)
        conditions.append(
            SyntheticSurfaceCondition(
                condition_id=condition_id,
                spec=spec,
                condition_spec_sha256=fingerprint,
            )
        )
    if len(conditions) != surface_spec.condition_count:
        raise RuntimeError("Synthetic surface expansion produced an unexpected condition count.")
    return tuple(conditions)


def _metric_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for metric in _SUMMARY_METRICS:
        values: list[float] = []
        for row in rows:
            value = dict(row.get("metrics") or {}).get(metric)
            if value is None:
                continue
            numeric = float(value)
            if np.isfinite(numeric):
                values.append(numeric)
        if values:
            array = np.asarray(values, dtype=float)
            summary[metric] = {
                "n_finite": int(array.size),
                "min": float(np.min(array)),
                "max": float(np.max(array)),
                "mean": float(np.mean(array)),
            }
    return summary


def _threshold_overview(rows: list[dict[str, Any]]) -> dict[str, Any]:
    statuses = [row.get("thresholds_passed") for row in rows]
    thresholded = [bool(value) for value in statuses if isinstance(value, bool)]
    passed = sum(thresholded)
    return {
        "thresholded_conditions": int(len(thresholded)),
        "passed_conditions": int(passed),
        "failed_conditions": int(len(thresholded) - passed),
        "pass_fraction": float(passed / len(thresholded)) if thresholded else None,
        "unthresholded_conditions": int(len(rows) - len(thresholded)),
    }


def evaluate_synthetic_recovery_surface(
    surface_spec: SyntheticGazeSurfaceSpec,
    estimator: Estimator,
    *,
    estimator_name: str,
    x_col: str = "x_px",
    y_col: str = "y_px",
    event_col: str | None = None,
    thresholds: dict[str, float] | None = None,
) -> SyntheticRecoverySurfaceResult:
    """Run one observed-signal-only estimator over every known-truth condition.

    The callback receives only a deep copy of ``observed_signal``. Latent truth and the artifact
    ledger are never passed to the callback. Each condition is immediately scored and bound to the
    single-condition certificate contract before the surface is assembled.
    """
    if not callable(estimator):
        raise TypeError("estimator must be callable.")
    if not isinstance(estimator_name, str) or not estimator_name.strip():
        raise ValueError("estimator_name must be non-empty.")
    thresholds = dict(thresholds or {})
    conditions = expand_synthetic_gaze_surface(surface_spec)
    ledger_rows: list[dict[str, Any]] = []
    children: dict[str, dict[str, Any]] = {}

    for condition in conditions:
        run = simulate_known_truth_gaze(condition.spec)
        estimator_input = run.observed_signal.copy(deep=True)
        input_sha256 = fingerprint_frame(estimator_input)
        estimates = estimator(estimator_input)
        if not isinstance(estimates, pd.DataFrame):
            raise TypeError(
                "Synthetic surface estimator must return a pandas DataFrame; "
                f"condition={condition.condition_id}."
            )
        certificate = build_synthetic_recovery_certificate(
            run,
            estimates,
            estimator_name=estimator_name,
            x_col=x_col,
            y_col=y_col,
            event_col=event_col,
            thresholds=thresholds,
        )
        validate_synthetic_recovery_certificate(certificate, run=run, estimates=estimates)
        children[condition.condition_id] = certificate
        ledger_rows.append(
            {
                **condition.to_dict(),
                "observed_input_sha256": input_sha256,
                "run_contract_fingerprint_sha256": run.contract_fingerprint_sha256,
                "child_certificate_fingerprint_sha256": certificate[
                    "certificate_fingerprint_sha256"
                ],
                "estimate_sha256": certificate["estimate_sha256"],
                "metrics": dict(certificate["metrics"]),
                "thresholds_passed": certificate["thresholds_passed"],
            }
        )

    estimator_contract = {
        "name": estimator_name.strip(),
        "x_col": x_col,
        "y_col": y_col,
        "event_col": event_col,
        "callback_input": "observed_signal_only",
        "latent_truth_passed_to_callback": False,
        "artifact_ledger_passed_to_callback": False,
    }
    body = {
        "schema": _SURFACE_SCHEMA,
        "surface_spec": surface_spec.to_dict(),
        "estimator": estimator_contract,
        "thresholds": thresholds,
        "condition_count": int(len(ledger_rows)),
        "condition_ledger": ledger_rows,
        "child_certificates": children,
        "metric_summary": _metric_summary(ledger_rows),
        "threshold_overview": _threshold_overview(ledger_rows),
        "metric_replay_requires_estimator_outputs": True,
        "claim_boundary": dict(_SURFACE_CLAIM_BOUNDARY),
    }
    surface_certificate = {
        **body,
        "surface_fingerprint_sha256": benchmark_fingerprint(body),
    }
    condition_ledger = pd.DataFrame(ledger_rows)
    return SyntheticRecoverySurfaceResult(
        condition_ledger=condition_ledger,
        surface_certificate=surface_certificate,
    )


def _spec_from_condition_payload(payload: dict[str, Any]) -> SyntheticGazeSpec:
    spec_payload = dict(payload)
    if "screen_size_px" in spec_payload:
        spec_payload["screen_size_px"] = tuple(spec_payload["screen_size_px"])
    if "calibration_bias_px" in spec_payload:
        spec_payload["calibration_bias_px"] = tuple(spec_payload["calibration_bias_px"])
    return SyntheticGazeSpec(**spec_payload)


def validate_synthetic_recovery_surface(
    certificate: dict[str, Any],
    *,
    replay_contracts: bool = True,
) -> bool:
    """Validate surface integrity, exact condition inventory, children, and closed claims.

    ``replay_contracts=True`` deterministically regenerates each simulator condition and verifies
    its truth/observation/artifact/event fingerprints against the child certificate. Estimator
    outputs are intentionally not embedded in the surface artifact; exact metric replay therefore
    still requires the separately retained estimator outputs named by their SHA-256 fingerprints.
    """
    if certificate.get("schema") != _SURFACE_SCHEMA:
        raise ValueError("Unsupported synthetic recovery surface schema.")
    fingerprint = certificate.get("surface_fingerprint_sha256")
    if not isinstance(fingerprint, str) or len(fingerprint) != 64:
        raise ValueError("Synthetic recovery surface fingerprint is missing or malformed.")
    body = {
        key: value
        for key, value in certificate.items()
        if key != "surface_fingerprint_sha256"
    }
    if benchmark_fingerprint(body) != fingerprint:
        raise ValueError("Synthetic recovery surface fingerprint mismatch.")
    if certificate.get("claim_boundary") != _SURFACE_CLAIM_BOUNDARY:
        raise ValueError("Synthetic recovery surface claim boundary was promoted or altered.")
    if certificate.get("metric_replay_requires_estimator_outputs") is not True:
        raise ValueError("Synthetic recovery surface metric-replay boundary was altered.")

    surface_payload = certificate.get("surface_spec")
    if not isinstance(surface_payload, dict):
        raise ValueError("Synthetic recovery surface specification is malformed.")
    surface_spec = SyntheticGazeSurfaceSpec.from_dict(surface_payload)
    if surface_payload != surface_spec.to_dict():
        raise ValueError("Synthetic recovery surface specification is not canonical.")
    expected_conditions = expand_synthetic_gaze_surface(surface_spec)
    expected = {condition.condition_id: condition for condition in expected_conditions}
    rows = certificate.get("condition_ledger")
    children = certificate.get("child_certificates")
    if not isinstance(rows, list) or not isinstance(children, dict):
        raise ValueError("Synthetic recovery surface condition inventory is malformed.")
    if certificate.get("condition_count") != len(expected):
        raise ValueError("Synthetic recovery surface condition count is inconsistent.")
    row_ids = [row.get("condition_id") for row in rows if isinstance(row, dict)]
    if len(row_ids) != len(rows) or len(set(row_ids)) != len(row_ids):
        raise ValueError("Synthetic recovery surface condition identifiers are missing or duplicated.")
    if set(row_ids) != set(expected) or set(children) != set(expected):
        raise ValueError("Synthetic recovery surface condition inventory does not match its design.")

    estimator = certificate.get("estimator")
    if not isinstance(estimator, dict) or estimator.get("callback_input") != "observed_signal_only":
        raise ValueError("Synthetic recovery surface estimator contract is invalid.")
    if estimator.get("latent_truth_passed_to_callback") is not False:
        raise ValueError("Synthetic recovery surface latent-truth callback boundary was altered.")
    if estimator.get("artifact_ledger_passed_to_callback") is not False:
        raise ValueError("Synthetic recovery surface artifact callback boundary was altered.")
    thresholds = dict(certificate.get("thresholds") or {})

    row_by_id = {str(row["condition_id"]): row for row in rows}
    for condition_id, expected_condition in expected.items():
        row = row_by_id[condition_id]
        if row.get("condition_spec_sha256") != expected_condition.condition_spec_sha256:
            raise ValueError("Synthetic recovery surface condition-spec fingerprint mismatch.")
        if row.get("spec") != expected_condition.spec.to_dict():
            raise ValueError("Synthetic recovery surface condition spec does not match its design.")
        child = children[condition_id]
        if not isinstance(child, dict):
            raise ValueError("Synthetic recovery surface child certificate is malformed.")
        validate_synthetic_recovery_certificate(child)
        if row.get("child_certificate_fingerprint_sha256") != child.get(
            "certificate_fingerprint_sha256"
        ):
            raise ValueError("Synthetic recovery surface child fingerprint mismatch.")
        if row.get("run_contract_fingerprint_sha256") != child.get(
            "contract_fingerprint_sha256"
        ):
            raise ValueError("Synthetic recovery surface run-contract fingerprint mismatch.")
        if row.get("estimate_sha256") != child.get("estimate_sha256"):
            raise ValueError("Synthetic recovery surface estimate fingerprint mismatch.")
        if row.get("metrics") != child.get("metrics"):
            raise ValueError("Synthetic recovery surface metrics do not match the child certificate.")
        if row.get("thresholds_passed") is not child.get("thresholds_passed"):
            raise ValueError("Synthetic recovery surface threshold status mismatch.")
        if dict(child.get("thresholds") or {}) != thresholds:
            raise ValueError("Synthetic recovery surface child thresholds are inconsistent.")
        child_estimator = dict(child.get("estimator") or {})
        for key in ("name", "x_col", "y_col", "event_col"):
            if child_estimator.get(key) != estimator.get(key):
                raise ValueError("Synthetic recovery surface estimator identity is inconsistent.")
        if child.get("seed") != expected_condition.spec.random_state:
            raise ValueError("Synthetic recovery surface child seed is inconsistent.")
        if child.get("sampling_rate_hz") != expected_condition.spec.sampling_rate_hz:
            raise ValueError("Synthetic recovery surface child sampling rate is inconsistent.")

        if replay_contracts:
            run = simulate_known_truth_gaze(expected_condition.spec)
            replay_bindings = {
                "contract_fingerprint_sha256": run.contract_fingerprint_sha256,
                "truth_sha256": fingerprint_frame(run.truth),
                "observed_signal_sha256": fingerprint_frame(run.observed_signal),
                "artifact_sha256": fingerprint_frame(run.artifact),
                "event_truth_sha256": fingerprint_frame(run.event_truth),
            }
            for key, value in replay_bindings.items():
                if child.get(key) != value:
                    raise ValueError(
                        "Synthetic recovery surface child does not replay from condition spec: "
                        f"{condition_id}:{key}."
                    )
            if row.get("observed_input_sha256") != fingerprint_frame(run.observed_signal):
                raise ValueError("Synthetic recovery surface observed-input fingerprint mismatch.")

    if certificate.get("metric_summary") != _metric_summary(rows):
        raise ValueError("Synthetic recovery surface metric summary is inconsistent.")
    if certificate.get("threshold_overview") != _threshold_overview(rows):
        raise ValueError("Synthetic recovery surface threshold overview is inconsistent.")
    return True


def freeze_synthetic_recovery_surface(
    certificate: dict[str, Any],
    path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Validate and freeze a robustness surface without overwriting by default."""
    validate_synthetic_recovery_surface(certificate, replay_contracts=True)
    target = Path(path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"Synthetic recovery surface already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(certificate, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return target