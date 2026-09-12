"""Design-conditional hierarchical parametric bootstrap for location-scale models."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ._certificate_schema import require_exact_mapping_keys
from .benchmarks import benchmark_fingerprint
from .correlated_location_random_slope_scale import (
    CorrelatedLocationRandomSlopeScaleResult,
)
from .correlated_location_scale import CorrelatedLocationScaleResult
from .exceptions import SchemaError
from .hierarchical_location_scale import HierarchicalLocationScaleResult
from .location_random_slope_scale import LocationRandomSlopeScaleResult
from .location_scale_refit_residual_calibration import _fit_function_for_result
from .location_scale_residual_calibration import (
    LocationScaleModelResult,
    _input_columns,
    _is_sha256_hex,
    _model_adapter,
    _require_certifiable_base_model,
    _require_exact_fitting_input,
)
from .provenance import fingerprint_frame

_CERTIFICATE_SCHEMA = "gazeforge.location-scale-hierarchical-bootstrap-certificate.v1"
_BOOTSTRAP_SCHEMA = "gazeforge.location-scale-hierarchical-bootstrap.v1"
_SUPPORTED_MODEL_FAMILIES = frozenset(
    {
        "independent_location_scale",
        "correlated_location_scale",
        "location_random_slope_scale",
        "correlated_location_random_slope_scale",
    }
)
_INVENTORY_FIELDS = frozenset({"parameter_id", "component", "term", "observed"})
_LEDGER_FIELDS = frozenset(
    {
        "simulation_index",
        "population_random_effects_fingerprint_sha256",
        "simulated_input_fingerprint_sha256",
        "model_fingerprint_sha256",
        "model_certificate_fingerprint_sha256",
        "parameter_estimates",
    }
)
_SUMMARY_COLUMNS = (
    "parameter_id",
    "component",
    "term",
    "observed",
    "bootstrap_mean",
    "bootstrap_se",
    "bootstrap_bias",
    "interval_lower",
    "interval_upper",
)
_CERTIFICATE_FIELDS = frozenset(
    {
        "schema",
        "bootstrap",
        "bootstrap_fingerprint_sha256",
        "summary",
        "refit_ledger",
        "claim_boundary",
        "certificate_fingerprint_sha256",
    }
)
_BOOTSTRAP_FIELDS = frozenset(
    {
        "schema",
        "spec",
        "model_family",
        "model_fingerprint_sha256",
        "base_model_certificate_fingerprint_sha256",
        "input_fingerprint_sha256",
        "n_obs",
        "n_groups",
        "parameter_inventory",
        "refit_ledger_fingerprint_sha256",
        "summary_fingerprint_sha256",
    }
)
_CLAIM_BOUNDARY = {
    "design_conditional_hierarchical_parametric_bootstrap_computed": True,
    "population_random_effects_resampled": True,
    "residual_errors_resampled": True,
    "observed_predictor_and_group_design_preserved": True,
    "same_model_specification_refit_per_simulation": True,
    "exact_fitting_input_required": True,
    "certifiable_base_model_required": True,
    "every_refit_must_converge_and_be_certifiable": True,
    "fixed_fitted_parameters_used_as_bootstrap_generating_values": True,
    "model_based_parameter_sampling_distribution_approximated": True,
    "percentile_intervals_computed": True,
    "empirical_bayes_random_effects_reused": False,
    "posterior_random_effect_uncertainty_integrated": False,
    "nonparametric_cluster_resampling_performed": False,
    "model_misspecification_robust": False,
    "frequentist_coverage_guaranteed": False,
    "fixed_effect_p_values_provided": False,
    "global_model_adequacy_established": False,
    "distributional_correctness_established": False,
    "causal_effects_established": False,
    "device_validity_established": False,
    "measurement_validity_established": False,
}


@dataclass(frozen=True, slots=True)
class LocationScaleHierarchicalBootstrapSpec:
    """Specification for a design-conditional hierarchical parametric bootstrap."""

    n_simulations: int = 200
    seed: int = 1618
    interval_level: float = 0.95
    max_refit_rows: int = 100_000

    def __post_init__(self) -> None:
        if (
            not isinstance(self.n_simulations, int)
            or isinstance(self.n_simulations, bool)
            or self.n_simulations < 2
            or self.n_simulations > 10_000
        ):
            raise ValueError("n_simulations must be an integer from 2 through 10000.")
        if not isinstance(self.seed, int) or isinstance(self.seed, bool) or self.seed < 0:
            raise ValueError("seed must be a non-negative integer.")
        level = float(self.interval_level)
        if not np.isfinite(level) or not 0.5 < level < 1.0:
            raise ValueError("interval_level must be finite and between 0.5 and 1.0.")
        if (
            not isinstance(self.max_refit_rows, int)
            or isinstance(self.max_refit_rows, bool)
            or self.max_refit_rows < 1
        ):
            raise ValueError("max_refit_rows must be a positive integer.")
        object.__setattr__(self, "interval_level", level)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the canonical bootstrap specification."""
        return asdict(self)


@dataclass(frozen=True, slots=True)
class LocationScaleHierarchicalBootstrapResult:
    """Model-based bootstrap distribution for certified location-scale parameters."""

    spec: LocationScaleHierarchicalBootstrapSpec
    model_family: str
    model_fingerprint_sha256: str
    base_model_certificate_fingerprint_sha256: str
    input_fingerprint_sha256: str
    n_obs: int
    n_groups: int
    parameter_inventory: tuple[dict[str, Any], ...]
    refit_ledger: tuple[dict[str, Any], ...]
    refit_ledger_fingerprint_sha256: str
    summary: pd.DataFrame
    summary_fingerprint_sha256: str
    bootstrap_fingerprint_sha256: str

    def parameters(self) -> pd.DataFrame:
        """Return a defensive copy of the bootstrap parameter summary."""
        _validate_result_identity(self)
        return self.summary.copy(deep=True)

    def replicates(self) -> pd.DataFrame:
        """Return the deterministic bootstrap replicate estimates."""
        _validate_result_identity(self)
        rows: list[dict[str, Any]] = []
        for row in self.refit_ledger:
            rows.append(
                {
                    "simulation_index": row["simulation_index"],
                    **dict(row["parameter_estimates"]),
                }
            )
        return pd.DataFrame(rows)


def _fixed_design(
    data: pd.DataFrame,
    predictors: tuple[str, ...],
    coefficients: np.ndarray,
    *,
    equation: str,
) -> np.ndarray:
    columns = [np.ones(len(data), dtype=float)]
    for predictor in predictors:
        values = pd.to_numeric(data[predictor], errors="coerce").to_numpy(dtype=float)
        if not np.isfinite(values).all():
            raise SchemaError(
                f"{equation} predictor '{predictor}' must be finite and numeric."
            )
        columns.append(values)
    design = np.column_stack(columns)
    coef = np.asarray(coefficients, dtype=float)
    if coef.ndim != 1 or coef.shape[0] != design.shape[1] or not np.isfinite(coef).all():
        raise SchemaError(f"{equation} fixed-effect coefficients are invalid.")
    values = design @ coef
    if not np.isfinite(values).all():
        raise SchemaError(f"{equation} fixed-effect surface is non-finite.")
    return values


def _parameter_inventory(
    result: LocationScaleModelResult,
) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for term, value in zip(result.location_terms, result.location_coef, strict=True):
        rows.append(
            {
                "parameter_id": f"location_fixed::{term}",
                "component": "location_fixed",
                "term": term,
                "observed": float(value),
            }
        )
    for term, value in zip(result.scale_terms, result.scale_coef, strict=True):
        rows.append(
            {
                "parameter_id": f"log_scale_fixed::{term}",
                "component": "log_scale_fixed",
                "term": term,
                "observed": float(value),
            }
        )
    if isinstance(result, (HierarchicalLocationScaleResult, CorrelatedLocationScaleResult)):
        random_values = (
            (
                "random_sd::location_intercept",
                "random_sd",
                "location_intercept",
                result.tau_location,
            ),
            (
                "random_sd::log_scale_intercept",
                "random_sd",
                "log_scale_intercept",
                result.tau_scale,
            ),
        )
    elif isinstance(
        result, (LocationRandomSlopeScaleResult, CorrelatedLocationRandomSlopeScaleResult)
    ):
        random_values = (
            (
                "random_sd::location_intercept",
                "random_sd",
                "location_intercept",
                result.tau_location_intercept,
            ),
            (
                "random_sd::location_slope",
                "random_sd",
                "location_slope",
                result.tau_location_slope,
            ),
            (
                "random_sd::log_scale_intercept",
                "random_sd",
                "log_scale_intercept",
                result.tau_scale,
            ),
        )
    else:
        raise TypeError("result must be a supported certified location-scale result type.")
    for parameter_id, component, term, value in random_values:
        rows.append(
            {
                "parameter_id": parameter_id,
                "component": component,
                "term": term,
                "observed": float(value),
            }
        )
    if isinstance(result, CorrelatedLocationScaleResult):
        rows.append(
            {
                "parameter_id": "random_correlation::location_log_scale",
                "component": "random_correlation",
                "term": "location_log_scale",
                "observed": float(result.rho_location_scale),
            }
        )
    elif isinstance(result, CorrelatedLocationRandomSlopeScaleResult):
        rows.append(
            {
                "parameter_id": "random_correlation::location_intercept_slope",
                "component": "random_correlation",
                "term": "location_intercept_slope",
                "observed": float(result.rho_location_intercept_slope),
            }
        )
    return _canonical_inventory(rows)


def _canonical_inventory(rows: Any) -> tuple[dict[str, Any], ...]:
    if not isinstance(rows, (list, tuple)) or not rows:
        raise SchemaError("Hierarchical bootstrap parameter inventory is invalid.")
    canonical: list[dict[str, Any]] = []
    identifiers: set[str] = set()
    for raw in rows:
        row = require_exact_mapping_keys(
            raw,
            _INVENTORY_FIELDS,
            context="Hierarchical bootstrap parameter inventory row",
        )
        parameter_id = row.get("parameter_id")
        component = row.get("component")
        term = row.get("term")
        observed = row.get("observed")
        if (
            not isinstance(parameter_id, str)
            or not parameter_id
            or parameter_id in identifiers
            or not isinstance(component, str)
            or not component
            or not isinstance(term, str)
            or not term
            or not isinstance(observed, (int, float))
            or isinstance(observed, bool)
            or not np.isfinite(float(observed))
        ):
            raise SchemaError("Hierarchical bootstrap parameter inventory is invalid.")
        identifiers.add(parameter_id)
        canonical.append(
            {
                "parameter_id": parameter_id,
                "component": component,
                "term": term,
                "observed": float(observed),
            }
        )
    return tuple(canonical)


def _parameter_estimates(result: LocationScaleModelResult) -> dict[str, float]:
    return {
        row["parameter_id"]: float(row["observed"])
        for row in _parameter_inventory(result)
    }


def _draw_population_effects(
    result: LocationScaleModelResult,
    group_levels: tuple[Any, ...],
    rng: np.random.Generator,
) -> pd.DataFrame:
    n_groups = len(group_levels)
    if n_groups < 2:
        raise SchemaError("Hierarchical bootstrap requires at least two groups.")
    if isinstance(result, HierarchicalLocationScaleResult):
        z = rng.standard_normal((n_groups, 2))
        frame = pd.DataFrame(
            {
                result.spec.group_col: list(group_levels),
                "location_intercept": result.tau_location * z[:, 0],
                "log_scale_intercept": result.tau_scale * z[:, 1],
            }
        )
    elif isinstance(result, CorrelatedLocationScaleResult):
        z = rng.standard_normal((n_groups, 2))
        rho = float(result.rho_location_scale)
        orthogonal = float(np.sqrt(max(1.0 - rho**2, 0.0)))
        frame = pd.DataFrame(
            {
                result.spec.group_col: list(group_levels),
                "location_intercept": result.tau_location * z[:, 0],
                "log_scale_intercept": result.tau_scale
                * (rho * z[:, 0] + orthogonal * z[:, 1]),
            }
        )
    elif isinstance(result, LocationRandomSlopeScaleResult):
        z = rng.standard_normal((n_groups, 3))
        frame = pd.DataFrame(
            {
                result.spec.group_col: list(group_levels),
                "location_intercept": result.tau_location_intercept * z[:, 0],
                "location_slope": result.tau_location_slope * z[:, 1],
                "log_scale_intercept": result.tau_scale * z[:, 2],
            }
        )
    elif isinstance(result, CorrelatedLocationRandomSlopeScaleResult):
        z = rng.standard_normal((n_groups, 3))
        rho = float(result.rho_location_intercept_slope)
        orthogonal = float(np.sqrt(max(1.0 - rho**2, 0.0)))
        frame = pd.DataFrame(
            {
                result.spec.group_col: list(group_levels),
                "location_intercept": result.tau_location_intercept * z[:, 0],
                "location_slope": result.tau_location_slope
                * (rho * z[:, 0] + orthogonal * z[:, 1]),
                "log_scale_intercept": result.tau_scale * z[:, 2],
            }
        )
    else:
        raise TypeError("result must be a supported certified location-scale result type.")
    numeric = frame.drop(columns=[result.spec.group_col]).to_numpy(dtype=float)
    if not np.isfinite(numeric).all():
        raise SchemaError("Hierarchical bootstrap population effects are non-finite.")
    return frame


def _simulate_hierarchical_outcome(
    result: LocationScaleModelResult,
    data: pd.DataFrame,
    *,
    rng: np.random.Generator,
) -> tuple[pd.DataFrame, str]:
    spec = result.spec
    fixed_location = _fixed_design(
        data,
        spec.location_predictors,
        result.location_coef,
        equation="Location",
    )
    fixed_log_scale = _fixed_design(
        data,
        spec.scale_predictors,
        result.scale_coef,
        equation="Scale",
    )
    group_codes, levels = pd.factorize(data[spec.group_col], sort=False)
    if np.any(group_codes < 0):
        raise SchemaError("Hierarchical bootstrap group identities must be complete.")
    group_levels = tuple(levels.tolist())
    effects = _draw_population_effects(result, group_levels, rng)
    location = fixed_location + effects["location_intercept"].to_numpy(dtype=float)[
        group_codes
    ]
    if isinstance(
        result, (LocationRandomSlopeScaleResult, CorrelatedLocationRandomSlopeScaleResult)
    ):
        slope = pd.to_numeric(
            data[spec.random_slope_predictor], errors="coerce"
        ).to_numpy(dtype=float)
        if not np.isfinite(slope).all():
            raise SchemaError("Hierarchical bootstrap random-slope predictor is non-finite.")
        location = (
            location
            + effects["location_slope"].to_numpy(dtype=float)[group_codes] * slope
        )
    log_scale = fixed_log_scale + effects[
        "log_scale_intercept"
    ].to_numpy(dtype=float)[group_codes]
    sigma = np.exp(log_scale)
    if (
        not np.isfinite(location).all()
        or not np.isfinite(sigma).all()
        or np.any(sigma <= 0.0)
    ):
        raise SchemaError("Hierarchical bootstrap generating surface is invalid.")
    simulated = data.copy(deep=True)
    simulated[spec.outcome_col] = location + sigma * rng.standard_normal(len(data))
    return simulated, fingerprint_frame(effects)


def _canonical_parameter_estimates(
    raw: Any,
    *,
    parameter_ids: tuple[str, ...],
) -> dict[str, float]:
    if not isinstance(raw, dict) or set(raw) != set(parameter_ids):
        raise SchemaError("Hierarchical bootstrap parameter estimate mapping is invalid.")
    canonical: dict[str, float] = {}
    for parameter_id in parameter_ids:
        value = raw.get(parameter_id)
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not np.isfinite(float(value))
        ):
            raise SchemaError("Hierarchical bootstrap parameter estimates must be finite.")
        canonical[parameter_id] = float(value)
    return canonical


def _canonical_refit_ledger(
    rows: Any,
    *,
    inventory: tuple[dict[str, Any], ...],
    n_simulations: int,
) -> tuple[dict[str, Any], ...]:
    if not isinstance(rows, (list, tuple)) or len(rows) != n_simulations:
        raise SchemaError("Hierarchical bootstrap refit ledger length is invalid.")
    parameter_ids = tuple(row["parameter_id"] for row in inventory)
    canonical: list[dict[str, Any]] = []
    for expected_index, raw in enumerate(rows):
        row = require_exact_mapping_keys(
            raw,
            _LEDGER_FIELDS,
            context="Hierarchical bootstrap refit ledger row",
        )
        index = row.get("simulation_index")
        if (
            not isinstance(index, int)
            or isinstance(index, bool)
            or index != expected_index
        ):
            raise SchemaError("Hierarchical bootstrap ledger indices are invalid.")
        for name in (
            "population_random_effects_fingerprint_sha256",
            "simulated_input_fingerprint_sha256",
            "model_fingerprint_sha256",
            "model_certificate_fingerprint_sha256",
        ):
            if not _is_sha256_hex(row.get(name)):
                raise SchemaError(f"Hierarchical bootstrap ledger {name} is invalid.")
        canonical.append(
            {
                "simulation_index": index,
                "population_random_effects_fingerprint_sha256": row[
                    "population_random_effects_fingerprint_sha256"
                ],
                "simulated_input_fingerprint_sha256": row[
                    "simulated_input_fingerprint_sha256"
                ],
                "model_fingerprint_sha256": row["model_fingerprint_sha256"],
                "model_certificate_fingerprint_sha256": row[
                    "model_certificate_fingerprint_sha256"
                ],
                "parameter_estimates": _canonical_parameter_estimates(
                    row["parameter_estimates"],
                    parameter_ids=parameter_ids,
                ),
            }
        )
    return tuple(canonical)


def _refit_ledger_fingerprint(
    rows: Any,
    *,
    inventory: tuple[dict[str, Any], ...],
    n_simulations: int,
) -> str:
    canonical = _canonical_refit_ledger(
        rows,
        inventory=inventory,
        n_simulations=n_simulations,
    )
    return benchmark_fingerprint(list(canonical))


def _bootstrap_summary(
    inventory: tuple[dict[str, Any], ...],
    ledger: tuple[dict[str, Any], ...],
    *,
    interval_level: float,
) -> pd.DataFrame:
    alpha = 1.0 - interval_level
    rows: list[dict[str, Any]] = []
    for parameter in inventory:
        parameter_id = parameter["parameter_id"]
        values = np.asarray(
            [row["parameter_estimates"][parameter_id] for row in ledger],
            dtype=float,
        )
        if len(values) < 2 or not np.isfinite(values).all():
            raise SchemaError("Hierarchical bootstrap replicate estimates are invalid.")
        observed = float(parameter["observed"])
        mean = float(np.mean(values))
        rows.append(
            {
                "parameter_id": parameter_id,
                "component": parameter["component"],
                "term": parameter["term"],
                "observed": observed,
                "bootstrap_mean": mean,
                "bootstrap_se": float(np.std(values, ddof=1)),
                "bootstrap_bias": mean - observed,
                "interval_lower": float(np.quantile(values, alpha / 2.0)),
                "interval_upper": float(np.quantile(values, 1.0 - alpha / 2.0)),
            }
        )
    return pd.DataFrame(rows, columns=_SUMMARY_COLUMNS)


def _summary_fingerprint(summary: pd.DataFrame) -> str:
    if not isinstance(summary, pd.DataFrame):
        raise TypeError("summary must be a pandas DataFrame.")
    if tuple(summary.columns) != _SUMMARY_COLUMNS:
        raise SchemaError("Hierarchical bootstrap summary columns are invalid.")
    return fingerprint_frame(summary)


def _bootstrap_identity_payload(
    *,
    spec: LocationScaleHierarchicalBootstrapSpec,
    model_family: str,
    model_fingerprint: str,
    base_model_certificate_fingerprint: str,
    input_fingerprint: str,
    n_obs: int,
    n_groups: int,
    parameter_inventory: tuple[dict[str, Any], ...],
    refit_ledger_fingerprint: str,
    summary_fingerprint: str,
) -> dict[str, Any]:
    return {
        "schema": _BOOTSTRAP_SCHEMA,
        "spec": spec.to_dict(),
        "model_family": model_family,
        "model_fingerprint_sha256": model_fingerprint,
        "base_model_certificate_fingerprint_sha256": base_model_certificate_fingerprint,
        "input_fingerprint_sha256": input_fingerprint,
        "n_obs": int(n_obs),
        "n_groups": int(n_groups),
        "parameter_inventory": [dict(row) for row in parameter_inventory],
        "refit_ledger_fingerprint_sha256": refit_ledger_fingerprint,
        "summary_fingerprint_sha256": summary_fingerprint,
    }


def bootstrap_location_scale_hierarchy(
    result: LocationScaleModelResult,
    data: pd.DataFrame,
    *,
    spec: LocationScaleHierarchicalBootstrapSpec | None = None,
) -> LocationScaleHierarchicalBootstrapResult:
    """Run a fail-closed design-conditional hierarchical parametric bootstrap."""
    bootstrap_spec = spec or LocationScaleHierarchicalBootstrapSpec()
    model_family, model_spec, _ = _model_adapter(result)
    fit_function = _fit_function_for_result(result)
    base_model_certificate_fingerprint = _require_certifiable_base_model(result)
    input_fingerprint = _require_exact_fitting_input(result, data)
    total_refit_rows = len(data) * bootstrap_spec.n_simulations
    if total_refit_rows > bootstrap_spec.max_refit_rows:
        raise SchemaError(
            "Hierarchical bootstrap resource budget exceeded: "
            f"{total_refit_rows} requested refit rows > "
            f"{bootstrap_spec.max_refit_rows} allowed."
        )
    group_codes, levels = pd.factorize(data[model_spec.group_col], sort=False)
    if np.any(group_codes < 0):
        raise SchemaError("Hierarchical bootstrap group identities must be complete.")
    n_groups = int(len(levels))
    if n_groups < 2:
        raise SchemaError("Hierarchical bootstrap requires at least two groups.")
    inventory = _parameter_inventory(result)
    ledger: list[dict[str, Any]] = []
    rng = np.random.default_rng(bootstrap_spec.seed)
    input_columns = _input_columns(model_spec)
    for simulation_index in range(bootstrap_spec.n_simulations):
        simulated_data, effects_fingerprint = _simulate_hierarchical_outcome(
            result,
            data,
            rng=rng,
        )
        simulated_input_fingerprint = fingerprint_frame(
            simulated_data.loc[:, input_columns]
        )
        try:
            refitted = fit_function(simulated_data, spec=result.spec)
            if refitted.input_fingerprint_sha256 != simulated_input_fingerprint:
                raise SchemaError("Hierarchical bootstrap refit input lineage mismatch.")
            refit_certificate_fingerprint = _require_certifiable_base_model(refitted)
            estimates = _parameter_estimates(refitted)
        except Exception as exc:
            raise SchemaError(
                "Hierarchical bootstrap failed closed because simulation "
                f"{simulation_index} did not produce a converged certifiable refit."
            ) from exc
        ledger.append(
            {
                "simulation_index": simulation_index,
                "population_random_effects_fingerprint_sha256": effects_fingerprint,
                "simulated_input_fingerprint_sha256": simulated_input_fingerprint,
                "model_fingerprint_sha256": refitted.model_fingerprint_sha256,
                "model_certificate_fingerprint_sha256": refit_certificate_fingerprint,
                "parameter_estimates": estimates,
            }
        )
    canonical_ledger = _canonical_refit_ledger(
        ledger,
        inventory=inventory,
        n_simulations=bootstrap_spec.n_simulations,
    )
    refit_ledger_fingerprint = _refit_ledger_fingerprint(
        canonical_ledger,
        inventory=inventory,
        n_simulations=bootstrap_spec.n_simulations,
    )
    summary = _bootstrap_summary(
        inventory,
        canonical_ledger,
        interval_level=bootstrap_spec.interval_level,
    )
    summary_fingerprint = _summary_fingerprint(summary)
    identity = _bootstrap_identity_payload(
        spec=bootstrap_spec,
        model_family=model_family,
        model_fingerprint=result.model_fingerprint_sha256,
        base_model_certificate_fingerprint=base_model_certificate_fingerprint,
        input_fingerprint=input_fingerprint,
        n_obs=len(data),
        n_groups=n_groups,
        parameter_inventory=inventory,
        refit_ledger_fingerprint=refit_ledger_fingerprint,
        summary_fingerprint=summary_fingerprint,
    )
    return LocationScaleHierarchicalBootstrapResult(
        spec=bootstrap_spec,
        model_family=model_family,
        model_fingerprint_sha256=result.model_fingerprint_sha256,
        base_model_certificate_fingerprint_sha256=base_model_certificate_fingerprint,
        input_fingerprint_sha256=input_fingerprint,
        n_obs=int(len(data)),
        n_groups=n_groups,
        parameter_inventory=inventory,
        refit_ledger=canonical_ledger,
        refit_ledger_fingerprint_sha256=refit_ledger_fingerprint,
        summary=summary,
        summary_fingerprint_sha256=summary_fingerprint,
        bootstrap_fingerprint_sha256=benchmark_fingerprint(identity),
    )


def _current_result_identity(
    result: LocationScaleHierarchicalBootstrapResult,
) -> dict[str, Any]:
    inventory = _canonical_inventory(result.parameter_inventory)
    ledger_fingerprint = _refit_ledger_fingerprint(
        result.refit_ledger,
        inventory=inventory,
        n_simulations=result.spec.n_simulations,
    )
    expected_summary = _bootstrap_summary(
        inventory,
        _canonical_refit_ledger(
            result.refit_ledger,
            inventory=inventory,
            n_simulations=result.spec.n_simulations,
        ),
        interval_level=result.spec.interval_level,
    )
    expected_summary_fingerprint = _summary_fingerprint(expected_summary)
    if expected_summary_fingerprint != _summary_fingerprint(result.summary):
        raise SchemaError("Hierarchical bootstrap summary is inconsistent with its ledger.")
    return _bootstrap_identity_payload(
        spec=result.spec,
        model_family=result.model_family,
        model_fingerprint=result.model_fingerprint_sha256,
        base_model_certificate_fingerprint=result.base_model_certificate_fingerprint_sha256,
        input_fingerprint=result.input_fingerprint_sha256,
        n_obs=result.n_obs,
        n_groups=result.n_groups,
        parameter_inventory=inventory,
        refit_ledger_fingerprint=ledger_fingerprint,
        summary_fingerprint=expected_summary_fingerprint,
    )


def _validate_result_identity(
    result: LocationScaleHierarchicalBootstrapResult,
) -> dict[str, Any]:
    if not isinstance(result, LocationScaleHierarchicalBootstrapResult):
        raise TypeError("result must be a LocationScaleHierarchicalBootstrapResult.")
    if result.model_family not in _SUPPORTED_MODEL_FAMILIES:
        raise SchemaError("Hierarchical bootstrap model family is invalid.")
    for name, value in (
        ("model_fingerprint_sha256", result.model_fingerprint_sha256),
        (
            "base_model_certificate_fingerprint_sha256",
            result.base_model_certificate_fingerprint_sha256,
        ),
        ("input_fingerprint_sha256", result.input_fingerprint_sha256),
        ("refit_ledger_fingerprint_sha256", result.refit_ledger_fingerprint_sha256),
        ("summary_fingerprint_sha256", result.summary_fingerprint_sha256),
        ("bootstrap_fingerprint_sha256", result.bootstrap_fingerprint_sha256),
    ):
        if not _is_sha256_hex(value):
            raise SchemaError(f"{name} is not a valid SHA-256 fingerprint.")
    if result.n_obs < 2 or result.n_groups < 2 or result.n_obs < result.n_groups:
        raise SchemaError("Hierarchical bootstrap observation/group counts are invalid.")
    if result.n_obs * result.spec.n_simulations > result.spec.max_refit_rows:
        raise SchemaError("Hierarchical bootstrap result exceeds its resource budget.")
    identity = _current_result_identity(result)
    if identity["refit_ledger_fingerprint_sha256"] != result.refit_ledger_fingerprint_sha256:
        raise SchemaError("Hierarchical bootstrap ledger was mutated after computation.")
    if identity["summary_fingerprint_sha256"] != result.summary_fingerprint_sha256:
        raise SchemaError("Hierarchical bootstrap summary was mutated after computation.")
    if benchmark_fingerprint(identity) != result.bootstrap_fingerprint_sha256:
        raise SchemaError("Hierarchical bootstrap fingerprint mismatch.")
    return identity


def build_location_scale_hierarchical_bootstrap_certificate(
    result: LocationScaleHierarchicalBootstrapResult,
) -> dict[str, Any]:
    """Build a deterministic certificate for the hierarchical bootstrap."""
    identity = _validate_result_identity(result)
    body = {
        "schema": _CERTIFICATE_SCHEMA,
        "bootstrap": identity,
        "bootstrap_fingerprint_sha256": result.bootstrap_fingerprint_sha256,
        "summary": result.summary.to_dict(orient="records"),
        "refit_ledger": [dict(row) for row in result.refit_ledger],
        "claim_boundary": dict(_CLAIM_BOUNDARY),
    }
    return {**body, "certificate_fingerprint_sha256": benchmark_fingerprint(body)}


def validate_location_scale_hierarchical_bootstrap_certificate(
    certificate: dict[str, Any],
) -> None:
    """Fail closed on bootstrap lineage, schema, summary, or claim tampering."""
    if not isinstance(certificate, dict):
        raise TypeError("certificate must be a dictionary.")
    require_exact_mapping_keys(
        certificate,
        _CERTIFICATE_FIELDS,
        context="Hierarchical bootstrap certificate",
    )
    if certificate.get("schema") != _CERTIFICATE_SCHEMA:
        raise SchemaError("Unsupported hierarchical bootstrap certificate schema.")
    fingerprint = certificate.get("certificate_fingerprint_sha256")
    body = {
        key: value
        for key, value in certificate.items()
        if key != "certificate_fingerprint_sha256"
    }
    if not _is_sha256_hex(fingerprint) or fingerprint != benchmark_fingerprint(body):
        raise SchemaError("Hierarchical bootstrap certificate fingerprint mismatch.")
    if certificate.get("claim_boundary") != _CLAIM_BOUNDARY:
        raise SchemaError("Hierarchical bootstrap scientific claim boundary was altered.")
    bootstrap = require_exact_mapping_keys(
        certificate.get("bootstrap"),
        _BOOTSTRAP_FIELDS,
        context="Hierarchical bootstrap identity",
    )
    if bootstrap.get("schema") != _BOOTSTRAP_SCHEMA:
        raise SchemaError("Hierarchical bootstrap identity is invalid.")
    try:
        canonical_spec = LocationScaleHierarchicalBootstrapSpec(**bootstrap["spec"])
    except (KeyError, TypeError, ValueError) as exc:
        raise SchemaError("Hierarchical bootstrap certificate has an invalid spec.") from exc
    if benchmark_fingerprint(canonical_spec.to_dict()) != benchmark_fingerprint(
        bootstrap["spec"]
    ):
        raise SchemaError("Hierarchical bootstrap certificate spec is not canonical.")
    if bootstrap.get("model_family") not in _SUPPORTED_MODEL_FAMILIES:
        raise SchemaError("Hierarchical bootstrap certificate model family is invalid.")
    for name in (
        "model_fingerprint_sha256",
        "base_model_certificate_fingerprint_sha256",
        "input_fingerprint_sha256",
        "refit_ledger_fingerprint_sha256",
        "summary_fingerprint_sha256",
    ):
        if not _is_sha256_hex(bootstrap.get(name)):
            raise SchemaError(f"Hierarchical bootstrap certificate {name} is invalid.")
    n_obs = bootstrap.get("n_obs")
    n_groups = bootstrap.get("n_groups")
    if (
        not isinstance(n_obs, int)
        or isinstance(n_obs, bool)
        or not isinstance(n_groups, int)
        or isinstance(n_groups, bool)
        or n_obs < 2
        or n_groups < 2
        or n_obs < n_groups
    ):
        raise SchemaError("Hierarchical bootstrap certificate counts are invalid.")
    if n_obs * canonical_spec.n_simulations > canonical_spec.max_refit_rows:
        raise SchemaError("Hierarchical bootstrap certificate exceeds its resource budget.")
    inventory = _canonical_inventory(bootstrap.get("parameter_inventory"))
    ledger = _canonical_refit_ledger(
        certificate.get("refit_ledger"),
        inventory=inventory,
        n_simulations=canonical_spec.n_simulations,
    )
    if (
        benchmark_fingerprint(list(ledger))
        != bootstrap["refit_ledger_fingerprint_sha256"]
    ):
        raise SchemaError("Hierarchical bootstrap ledger fingerprint mismatch.")
    summary_records = certificate.get("summary")
    if not isinstance(summary_records, list) or len(summary_records) != len(inventory):
        raise SchemaError("Hierarchical bootstrap certificate summary is invalid.")
    canonical_summary_records: list[dict[str, Any]] = []
    summary_fields = frozenset(_SUMMARY_COLUMNS)
    for raw_record in summary_records:
        record = require_exact_mapping_keys(
            raw_record,
            summary_fields,
            context="Hierarchical bootstrap summary row",
        )
        canonical_summary_records.append(
            {column: record[column] for column in _SUMMARY_COLUMNS}
        )
    summary = pd.DataFrame(canonical_summary_records, columns=_SUMMARY_COLUMNS)
    expected_summary = _bootstrap_summary(
        inventory,
        ledger,
        interval_level=canonical_spec.interval_level,
    )
    if _summary_fingerprint(summary) != _summary_fingerprint(expected_summary):
        raise SchemaError("Hierarchical bootstrap summary is inconsistent with its ledger.")
    if _summary_fingerprint(summary) != bootstrap["summary_fingerprint_sha256"]:
        raise SchemaError("Hierarchical bootstrap summary fingerprint mismatch.")
    bootstrap_fingerprint = certificate.get("bootstrap_fingerprint_sha256")
    if (
        not _is_sha256_hex(bootstrap_fingerprint)
        or bootstrap_fingerprint != benchmark_fingerprint(bootstrap)
    ):
        raise SchemaError("Hierarchical bootstrap identity fingerprint mismatch.")


def freeze_location_scale_hierarchical_bootstrap_certificate(
    result: LocationScaleHierarchicalBootstrapResult,
    path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Validate and freeze a hierarchical-bootstrap certificate as canonical JSON."""
    certificate = build_location_scale_hierarchical_bootstrap_certificate(result)
    validate_location_scale_hierarchical_bootstrap_certificate(certificate)
    destination = Path(path)
    if destination.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing file: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(certificate, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return destination
