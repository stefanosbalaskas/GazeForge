"""Numerically hardened bootstrap Monte Carlo precision adapter.

The certified #167 implementation is preserved byte-for-byte in the private
``_location_scale_bootstrap_monte_carlo_core`` module.  This adapter replaces
only the leave-one-bootstrap-replicate-out SD jackknife kernel with an
algebraically equivalent centered implementation that avoids catastrophic
cancellation for large-offset parameter estimates.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from . import _location_scale_bootstrap_monte_carlo_core as _core
from .exceptions import SchemaError
from .location_scale_hierarchical_bootstrap import (
    LocationScaleHierarchicalBootstrapResult,
)


def _jackknife_sd_mcse(values: np.ndarray) -> float:
    """Return a translation-stable jackknife MCSE for a bootstrap SD.

    The delete-one sample variances are obtained from the centered total
    sum of squares.  Centering on an observed anchor first removes any large
    common offset, and the exact delete-one identity then avoids the unstable
    ``sum(x**2) - sum(x)**2 / n`` subtraction used previously.
    """
    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or not np.isfinite(array).all():
        raise SchemaError("Bootstrap replicate estimates are invalid.")

    n = int(len(array))
    if n < 3:
        raise SchemaError(
            "Monte Carlo precision diagnostics require at least three "
            "bootstrap simulations."
        )

    # Remove the common location before any variance arithmetic.  Subtracting
    # one observed value is exactly translation invariant up to the precision
    # already present in the input floats and prevents large absolute levels
    # from dominating the second-moment calculation.
    shifted = array - float(array[0])
    if not np.isfinite(shifted).all():
        raise SchemaError(
            "Bootstrap SD jackknife could not form finite centered estimates."
        )
    mean = float(np.mean(shifted))
    centered = shifted - mean
    total_centered_ss = float(np.dot(centered, centered))
    if total_centered_ss < 0.0 or not np.isfinite(total_centered_ss):
        raise SchemaError(
            "Bootstrap SD jackknife produced an invalid centered sum of squares."
        )

    remaining_n = n - 1
    variance_denominator = remaining_n - 1
    leave_one_out = np.empty(n, dtype=float)
    eps = np.finfo(float).eps
    tiny = np.finfo(float).tiny

    for index, value in enumerate(shifted):
        delta = float(value) - mean
        # Exact delete-one identity:
        # M2_{(-i)} = M2 - n/(n-1) * (x_i - mean)^2.
        removed_centered_ss = (n / remaining_n) * delta * delta
        remaining_centered_ss = total_centered_ss - removed_centered_ss

        # A mathematically non-negative residual can be a few ulps below zero
        # after the subtraction above.  Clamp only roundoff-sized negatives;
        # anything materially negative remains a fail-closed numerical error.
        tolerance = 64.0 * eps * max(
            abs(total_centered_ss),
            abs(removed_centered_ss),
            tiny,
        )
        if (
            remaining_centered_ss < 0.0
            and abs(remaining_centered_ss) <= tolerance
        ):
            remaining_centered_ss = 0.0
        if remaining_centered_ss < 0.0 or not np.isfinite(
            remaining_centered_ss
        ):
            raise SchemaError(
                "Bootstrap SD jackknife produced an invalid leave-one-out "
                "variance."
            )

        variance = remaining_centered_ss / variance_denominator
        leave_one_out[index] = np.sqrt(variance)

    center = float(np.mean(leave_one_out))
    value = np.sqrt(
        (n - 1.0)
        / n
        * float(np.sum((leave_one_out - center) ** 2))
    )
    if not np.isfinite(value):
        raise SchemaError("Bootstrap SD jackknife MCSE is non-finite.")
    return float(value)


# The private core's public workflows recompute diagnostics during result and
# certificate validation.  Replacing this one private kernel therefore applies
# the stable arithmetic consistently to assessment, certificate construction,
# validation, and freezing without changing any schema or claim boundary.
_core._jackknife_sd_mcse = _jackknife_sd_mcse

LocationScaleBootstrapMonteCarloSpec = (
    _core.LocationScaleBootstrapMonteCarloSpec
)
LocationScaleBootstrapMonteCarloResult = (
    _core.LocationScaleBootstrapMonteCarloResult
)

# Preserve the historical public module identity for repr/pickle compatibility
# even though the certified implementation now lives in the private core.
LocationScaleBootstrapMonteCarloSpec.__module__ = __name__
LocationScaleBootstrapMonteCarloResult.__module__ = __name__


def assess_location_scale_bootstrap_monte_carlo(
    result: LocationScaleHierarchicalBootstrapResult,
    *,
    spec: LocationScaleBootstrapMonteCarloSpec | None = None,
) -> LocationScaleBootstrapMonteCarloResult:
    """Quantify Monte Carlo error in one certified hierarchical bootstrap."""
    return _core.assess_location_scale_bootstrap_monte_carlo(
        result,
        spec=spec,
    )


def build_location_scale_bootstrap_monte_carlo_certificate(
    result: LocationScaleBootstrapMonteCarloResult,
) -> dict[str, Any]:
    """Build a deterministic certificate for bootstrap Monte Carlo precision."""
    return _core.build_location_scale_bootstrap_monte_carlo_certificate(result)


def validate_location_scale_bootstrap_monte_carlo_certificate(
    certificate: dict[str, Any],
) -> None:
    """Fail closed on Monte Carlo diagnostic, lineage, or claim tampering."""
    _core.validate_location_scale_bootstrap_monte_carlo_certificate(certificate)


def freeze_location_scale_bootstrap_monte_carlo_certificate(
    result: LocationScaleBootstrapMonteCarloResult,
    path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Validate and freeze Monte Carlo diagnostics as canonical JSON."""
    return _core.freeze_location_scale_bootstrap_monte_carlo_certificate(
        result,
        path,
        overwrite=overwrite,
    )


__all__ = [
    "LocationScaleBootstrapMonteCarloResult",
    "LocationScaleBootstrapMonteCarloSpec",
    "assess_location_scale_bootstrap_monte_carlo",
    "build_location_scale_bootstrap_monte_carlo_certificate",
    "freeze_location_scale_bootstrap_monte_carlo_certificate",
    "validate_location_scale_bootstrap_monte_carlo_certificate",
]
