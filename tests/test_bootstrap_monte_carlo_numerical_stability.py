import numpy as np
import pytest

from gazeforge.location_scale_bootstrap_monte_carlo import (
    LocationScaleBootstrapMonteCarloResult,
    LocationScaleBootstrapMonteCarloSpec,
    _jackknife_sd_mcse,
)


def _explicit_delete_one_sd_jackknife(values: np.ndarray) -> float:
    values = np.asarray(values, dtype=float)
    leave_one_out = np.asarray(
        [
            np.std(np.delete(values, index), ddof=1)
            for index in range(len(values))
        ],
        dtype=float,
    )
    center = float(np.mean(leave_one_out))
    return float(
        np.sqrt(
            (len(values) - 1.0)
            / len(values)
            * np.sum((leave_one_out - center) ** 2)
        )
    )


def test_sd_jackknife_matches_explicit_delete_one_reference():
    values = np.asarray([-2.5, -0.25, 0.5, 1.75, 3.0, 5.5], dtype=float)
    assert _jackknife_sd_mcse(values) == pytest.approx(
        _explicit_delete_one_sd_jackknife(values),
        rel=1e-14,
        abs=1e-14,
    )


def test_sd_jackknife_is_stable_under_large_common_offsets():
    centered = np.arange(6, dtype=float)
    expected = _explicit_delete_one_sd_jackknife(centered)

    for offset in (1.0e9, 1.0e12, 1.0e15, -1.0e12):
        shifted = centered + offset
        assert _jackknife_sd_mcse(shifted) == pytest.approx(
            expected,
            rel=1e-14,
            abs=1e-14,
        )


def test_sd_jackknife_constant_replicates_have_zero_mcse():
    values = np.full(8, 1.0e12, dtype=float)
    assert _jackknife_sd_mcse(values) == 0.0


def test_public_monte_carlo_types_keep_historical_module_identity():
    assert (
        LocationScaleBootstrapMonteCarloSpec.__module__
        == "gazeforge.location_scale_bootstrap_monte_carlo"
    )
    assert (
        LocationScaleBootstrapMonteCarloResult.__module__
        == "gazeforge.location_scale_bootstrap_monte_carlo"
    )
