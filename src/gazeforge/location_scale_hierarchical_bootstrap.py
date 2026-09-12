"""Design-conditional hierarchical parametric bootstrap for location-scale models.

The certified four-family implementation lives in the private core module. This
adapter preserves that implementation byte-for-byte and adds the certified full
3x3 random-effect covariance family without changing the public API or
certificate schema.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import _location_scale_hierarchical_bootstrap_core as _core
from .exceptions import SchemaError
from .full_covariance_location_random_slope_scale import (
    FullCovarianceLocationRandomSlopeScaleResult,
)
from .location_scale_residual_calibration import LocationScaleModelResult
from .provenance import fingerprint_frame

LocationScaleHierarchicalBootstrapSpec = (
    _core.LocationScaleHierarchicalBootstrapSpec
)
LocationScaleHierarchicalBootstrapResult = (
    _core.LocationScaleHierarchicalBootstrapResult
)

# Preserve the public class import path even though their certified
# implementation is retained in the private core module.
LocationScaleHierarchicalBootstrapSpec.__module__ = __name__
LocationScaleHierarchicalBootstrapResult.__module__ = __name__

_CORE_PARAMETER_INVENTORY = _core._parameter_inventory
_CORE_DRAW_POPULATION_EFFECTS = _core._draw_population_effects
_CORE_SIMULATE_HIERARCHICAL_OUTCOME = (
    _core._simulate_hierarchical_outcome
)

_SUPPORTED_MODEL_FAMILIES = frozenset(
    {
        *_core._SUPPORTED_MODEL_FAMILIES,
        "full_covariance_location_random_slope_scale",
    }
)

# Kept as a module-level hook because the established fail-closed test suite
# deliberately monkeypatches this name to prove that any failed refit aborts
# the bootstrap. ``bootstrap_location_scale_hierarchy`` synchronizes it into
# the preserved core before execution.
_fit_function_for_result = _core._fit_function_for_result


def _parameter_inventory(
    result: LocationScaleModelResult,
) -> tuple[dict[str, Any], ...]:
    """Return the canonical bootstrap parameter inventory for a supported fit."""
    if not isinstance(result, FullCovarianceLocationRandomSlopeScaleResult):
        return _CORE_PARAMETER_INVENTORY(result)

    rows: list[dict[str, Any]] = []
    for term, value in zip(
        result.location_terms,
        result.location_coef,
        strict=True,
    ):
        rows.append(
            {
                "parameter_id": f"location_fixed::{term}",
                "component": "location_fixed",
                "term": term,
                "observed": float(value),
            }
        )
    for term, value in zip(
        result.scale_terms,
        result.scale_coef,
        strict=True,
    ):
        rows.append(
            {
                "parameter_id": f"log_scale_fixed::{term}",
                "component": "log_scale_fixed",
                "term": term,
                "observed": float(value),
            }
        )
    for parameter_id, term, value in (
        (
            "random_sd::location_intercept",
            "location_intercept",
            result.tau_location_intercept,
        ),
        (
            "random_sd::location_slope",
            "location_slope",
            result.tau_location_slope,
        ),
        (
            "random_sd::log_scale_intercept",
            "log_scale_intercept",
            result.tau_scale,
        ),
    ):
        rows.append(
            {
                "parameter_id": parameter_id,
                "component": "random_sd",
                "term": term,
                "observed": float(value),
            }
        )
    for parameter_id, term, value in (
        (
            "random_correlation::location_intercept_slope",
            "location_intercept_slope",
            result.rho_location_intercept_slope,
        ),
        (
            "random_correlation::location_intercept_log_scale",
            "location_intercept_log_scale",
            result.rho_location_intercept_log_scale,
        ),
        (
            "random_correlation::location_slope_log_scale",
            "location_slope_log_scale",
            result.rho_location_slope_log_scale,
        ),
    ):
        rows.append(
            {
                "parameter_id": parameter_id,
                "component": "random_correlation",
                "term": term,
                "observed": float(value),
            }
        )
    return _core._canonical_inventory(rows)


def _draw_population_effects(
    result: LocationScaleModelResult,
    group_levels: tuple[Any, ...],
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Draw fresh participant effects from the fitted population hierarchy."""
    if not isinstance(result, FullCovarianceLocationRandomSlopeScaleResult):
        return _CORE_DRAW_POPULATION_EFFECTS(result, group_levels, rng)

    n_groups = len(group_levels)
    if n_groups < 2:
        raise SchemaError("Hierarchical bootstrap requires at least two groups.")
    covariance = np.asarray(
        result.random_effect_covariance_matrix(),
        dtype=float,
    )
    if (
        covariance.shape != (3, 3)
        or not np.isfinite(covariance).all()
        or not np.allclose(
            covariance,
            covariance.T,
            rtol=0.0,
            atol=1e-12,
        )
    ):
        raise SchemaError(
            "Hierarchical bootstrap full-covariance population matrix is invalid."
        )
    try:
        cholesky = np.linalg.cholesky(covariance)
    except np.linalg.LinAlgError as exc:
        raise SchemaError(
            "Hierarchical bootstrap full-covariance population matrix is not "
            "positive definite."
        ) from exc
    if not np.isfinite(cholesky).all():
        raise SchemaError(
            "Hierarchical bootstrap full-covariance Cholesky factor is non-finite."
        )

    draws = rng.standard_normal((n_groups, 3)) @ cholesky.T
    frame = pd.DataFrame(
        {
            result.spec.group_col: list(group_levels),
            "location_intercept": draws[:, 0],
            "location_slope": draws[:, 1],
            "log_scale_intercept": draws[:, 2],
        }
    )
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
    """Generate one design-conditional hierarchical bootstrap outcome table."""
    if not isinstance(result, FullCovarianceLocationRandomSlopeScaleResult):
        return _CORE_SIMULATE_HIERARCHICAL_OUTCOME(
            result,
            data,
            rng=rng,
        )

    spec = result.spec
    fixed_location = _core._fixed_design(
        data,
        spec.location_predictors,
        result.location_coef,
        equation="Location",
    )
    fixed_log_scale = _core._fixed_design(
        data,
        spec.scale_predictors,
        result.scale_coef,
        equation="Scale",
    )
    group_codes, levels = pd.factorize(data[spec.group_col], sort=False)
    if np.any(group_codes < 0):
        raise SchemaError("Hierarchical bootstrap group identities must be complete.")
    effects = _draw_population_effects(
        result,
        tuple(levels.tolist()),
        rng,
    )

    slope = pd.to_numeric(
        data[spec.random_slope_predictor],
        errors="coerce",
    ).to_numpy(dtype=float)
    if not np.isfinite(slope).all():
        raise SchemaError(
            "Hierarchical bootstrap random-slope predictor is non-finite."
        )
    location = (
        fixed_location
        + effects["location_intercept"].to_numpy(dtype=float)[group_codes]
        + effects["location_slope"].to_numpy(dtype=float)[group_codes] * slope
    )
    log_scale = (
        fixed_log_scale
        + effects["log_scale_intercept"].to_numpy(dtype=float)[group_codes]
    )
    sigma = np.exp(log_scale)
    if (
        not np.isfinite(location).all()
        or not np.isfinite(sigma).all()
        or np.any(sigma <= 0.0)
    ):
        raise SchemaError("Hierarchical bootstrap generating surface is invalid.")

    simulated = data.copy(deep=True)
    simulated[spec.outcome_col] = (
        location + sigma * rng.standard_normal(len(data))
    )
    return simulated, fingerprint_frame(effects)


def _sync_core_adapters() -> None:
    """Bind the five-family adapter hooks into the preserved certified core."""
    _core._SUPPORTED_MODEL_FAMILIES = _SUPPORTED_MODEL_FAMILIES
    _core._parameter_inventory = _parameter_inventory
    _core._draw_population_effects = _draw_population_effects
    _core._simulate_hierarchical_outcome = _simulate_hierarchical_outcome
    _core._fit_function_for_result = _fit_function_for_result


_sync_core_adapters()


def bootstrap_location_scale_hierarchy(
    result: LocationScaleModelResult,
    data: pd.DataFrame,
    *,
    spec: LocationScaleHierarchicalBootstrapSpec | None = None,
) -> LocationScaleHierarchicalBootstrapResult:
    """Run a fail-closed five-family hierarchical parametric bootstrap."""
    _sync_core_adapters()
    return _core.bootstrap_location_scale_hierarchy(
        result,
        data,
        spec=spec,
    )


def build_location_scale_hierarchical_bootstrap_certificate(
    result: LocationScaleHierarchicalBootstrapResult,
) -> dict[str, Any]:
    """Build a deterministic certificate for the hierarchical bootstrap."""
    _sync_core_adapters()
    return _core.build_location_scale_hierarchical_bootstrap_certificate(result)


def validate_location_scale_hierarchical_bootstrap_certificate(
    certificate: dict[str, Any],
) -> None:
    """Fail closed on bootstrap lineage, schema, summary, or claim tampering."""
    _sync_core_adapters()
    _core.validate_location_scale_hierarchical_bootstrap_certificate(certificate)


def freeze_location_scale_hierarchical_bootstrap_certificate(
    result: LocationScaleHierarchicalBootstrapResult,
    path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Validate and freeze a hierarchical-bootstrap certificate as canonical JSON."""
    _sync_core_adapters()
    return _core.freeze_location_scale_hierarchical_bootstrap_certificate(
        result,
        path,
        overwrite=overwrite,
    )


__all__ = [
    "LocationScaleHierarchicalBootstrapResult",
    "LocationScaleHierarchicalBootstrapSpec",
    "bootstrap_location_scale_hierarchy",
    "build_location_scale_hierarchical_bootstrap_certificate",
    "freeze_location_scale_hierarchical_bootstrap_certificate",
    "validate_location_scale_hierarchical_bootstrap_certificate",
]
