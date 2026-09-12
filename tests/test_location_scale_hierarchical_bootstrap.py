from copy import deepcopy

import numpy as np
import pandas as pd
import pytest

from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.correlated_location_random_slope_scale import (
    CorrelatedLocationRandomSlopeScaleResult,
    CorrelatedLocationRandomSlopeScaleSpec,
    fit_correlated_location_random_slope_scale,
)
from gazeforge.correlated_location_scale import (
    CorrelatedLocationScaleResult,
    CorrelatedLocationScaleSpec,
)
from gazeforge.exceptions import SchemaError
from gazeforge.hierarchical_location_scale import (
    HierarchicalLocationScaleResult,
    HierarchicalLocationScaleSpec,
    fit_hierarchical_location_scale,
)
from gazeforge.location_random_slope_scale import (
    LocationRandomSlopeScaleResult,
    LocationRandomSlopeScaleSpec,
)
from gazeforge.location_scale_hierarchical_bootstrap import (
    LocationScaleHierarchicalBootstrapSpec,
    _draw_population_effects,
    _simulate_hierarchical_outcome,
    bootstrap_location_scale_hierarchy,
    build_location_scale_hierarchical_bootstrap_certificate,
    validate_location_scale_hierarchical_bootstrap_certificate,
)
from gazeforge.provenance import fingerprint_frame


def _synthetic(seed: int = 41) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows: list[dict[str, float | str]] = []
    x_grid = np.linspace(-1.4, 1.4, 12)
    for group_index in range(16):
        location_effect = rng.normal(0.0, 0.35)
        scale_effect = rng.normal(0.0, 0.12)
        for x in x_grid:
            location = 0.70 + 0.45 * x + location_effect
            sigma = np.exp(-0.15 + 0.06 * x + scale_effect)
            rows.append(
                {
                    "participant_id": f"p{group_index:02d}",
                    "x": float(x),
                    "y": float(rng.normal(location, sigma)),
                }
            )
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def independent_fit():
    data = _synthetic()
    spec = HierarchicalLocationScaleSpec(
        outcome_col="y",
        group_col="participant_id",
        location_predictors=("x",),
        scale_predictors=("x",),
        quadrature_points=3,
        max_iter=450,
        tolerance=1e-6,
    )
    fitted = fit_hierarchical_location_scale(data, spec=spec)
    assert fitted.converged
    return data, fitted


def _bootstrap_spec(seed: int = 811) -> LocationScaleHierarchicalBootstrapSpec:
    return LocationScaleHierarchicalBootstrapSpec(
        n_simulations=2,
        seed=seed,
        interval_level=0.90,
        max_refit_rows=1_000,
    )


@pytest.fixture(scope="module")
def independent_bootstrap(independent_fit):
    data, fitted = independent_fit
    return bootstrap_location_scale_hierarchy(
        fitted,
        data,
        spec=_bootstrap_spec(),
    )


def test_hierarchical_bootstrap_is_deterministic_with_complete_lineage(
    independent_fit,
    independent_bootstrap,
):
    data, fitted = independent_fit
    repeated = bootstrap_location_scale_hierarchy(
        fitted,
        data,
        spec=_bootstrap_spec(),
    )
    assert independent_bootstrap.model_family == "independent_location_scale"
    assert independent_bootstrap.model_fingerprint_sha256 == fitted.model_fingerprint_sha256
    assert independent_bootstrap.n_obs == len(data)
    assert independent_bootstrap.n_groups == data["participant_id"].nunique()
    assert len(independent_bootstrap.refit_ledger) == 2
    assert (
        independent_bootstrap.refit_ledger_fingerprint_sha256
        == repeated.refit_ledger_fingerprint_sha256
    )
    assert (
        independent_bootstrap.bootstrap_fingerprint_sha256
        == repeated.bootstrap_fingerprint_sha256
    )
    assert independent_bootstrap.refit_ledger == repeated.refit_ledger
    pd.testing.assert_frame_equal(
        independent_bootstrap.summary,
        repeated.summary,
    )
    replicate_frame = independent_bootstrap.replicates()
    assert tuple(replicate_frame["simulation_index"]) == (0, 1)
    assert set(replicate_frame.columns[1:]) == {
        row["parameter_id"] for row in independent_bootstrap.parameter_inventory
    }
    for row in independent_bootstrap.refit_ledger:
        assert len(row["population_random_effects_fingerprint_sha256"]) == 64
        assert len(row["simulated_input_fingerprint_sha256"]) == 64
        assert len(row["model_fingerprint_sha256"]) == 64
        assert len(row["model_certificate_fingerprint_sha256"]) == 64


def test_hierarchical_bootstrap_certificate_roundtrip(independent_bootstrap):
    certificate = build_location_scale_hierarchical_bootstrap_certificate(
        independent_bootstrap
    )
    validate_location_scale_hierarchical_bootstrap_certificate(certificate)
    assert (
        certificate["bootstrap"]["model_family"]
        == "independent_location_scale"
    )
    assert certificate["claim_boundary"]["population_random_effects_resampled"] is True
    assert certificate["claim_boundary"]["empirical_bayes_random_effects_reused"] is False


def test_hierarchical_bootstrap_requires_exact_fitting_input(independent_fit):
    data, fitted = independent_fit
    changed = data.copy()
    changed.loc[0, "y"] += 0.01
    with pytest.raises(SchemaError, match="exact fitted modelling input"):
        bootstrap_location_scale_hierarchy(
            fitted,
            changed,
            spec=_bootstrap_spec(),
        )


def test_hierarchical_bootstrap_resource_budget_fails_before_refitting(independent_fit):
    data, fitted = independent_fit
    spec = LocationScaleHierarchicalBootstrapSpec(
        n_simulations=2,
        max_refit_rows=len(data),
    )
    with pytest.raises(SchemaError, match="resource budget exceeded"):
        bootstrap_location_scale_hierarchy(fitted, data, spec=spec)


def test_any_failed_hierarchical_bootstrap_refit_aborts(
    independent_fit,
    monkeypatch,
):
    data, fitted = independent_fit

    def fail_refit(*args, **kwargs):
        raise RuntimeError("synthetic refit failure")

    monkeypatch.setattr(
        "gazeforge.location_scale_hierarchical_bootstrap._fit_function_for_result",
        lambda result: fail_refit,
    )
    with pytest.raises(
        SchemaError,
        match="simulation 0 did not produce a converged certifiable refit",
    ):
        bootstrap_location_scale_hierarchy(
            fitted,
            data,
            spec=_bootstrap_spec(),
        )


def test_hierarchical_bootstrap_claim_promotion_is_rejected(independent_bootstrap):
    certificate = build_location_scale_hierarchical_bootstrap_certificate(
        independent_bootstrap
    )
    promoted = deepcopy(certificate)
    promoted["claim_boundary"]["frequentist_coverage_guaranteed"] = True
    body = {
        key: value
        for key, value in promoted.items()
        if key != "certificate_fingerprint_sha256"
    }
    promoted["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)
    with pytest.raises(SchemaError, match="claim boundary"):
        validate_location_scale_hierarchical_bootstrap_certificate(promoted)


def test_certificate_summary_key_order_is_semantically_irrelevant(
    independent_bootstrap,
):
    certificate = build_location_scale_hierarchical_bootstrap_certificate(
        independent_bootstrap
    )
    reordered = deepcopy(certificate)
    first = reordered["summary"][0]
    reordered["summary"][0] = {
        key: first[key] for key in reversed(tuple(first))
    }
    body = {
        key: value
        for key, value in reordered.items()
        if key != "certificate_fingerprint_sha256"
    }
    reordered["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)
    validate_location_scale_hierarchical_bootstrap_certificate(reordered)


def test_hierarchical_bootstrap_ledger_parameter_tamper_is_rejected(
    independent_bootstrap,
):
    certificate = build_location_scale_hierarchical_bootstrap_certificate(
        independent_bootstrap
    )
    attacked = deepcopy(certificate)
    parameter_id = attacked["bootstrap"]["parameter_inventory"][0]["parameter_id"]
    attacked["refit_ledger"][0]["parameter_estimates"][parameter_id] += 0.25
    attacked["bootstrap"]["refit_ledger_fingerprint_sha256"] = benchmark_fingerprint(
        attacked["refit_ledger"]
    )
    attacked["bootstrap_fingerprint_sha256"] = benchmark_fingerprint(
        attacked["bootstrap"]
    )
    body = {
        key: value
        for key, value in attacked.items()
        if key != "certificate_fingerprint_sha256"
    }
    attacked["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)
    with pytest.raises(SchemaError, match="summary is inconsistent"):
        validate_location_scale_hierarchical_bootstrap_certificate(attacked)


def test_invalid_hierarchical_bootstrap_specs_fail_closed():
    with pytest.raises(ValueError, match="2 through 10000"):
        LocationScaleHierarchicalBootstrapSpec(n_simulations=1)
    with pytest.raises(ValueError, match="2 through 10000"):
        LocationScaleHierarchicalBootstrapSpec(n_simulations=10_001)
    with pytest.raises(ValueError, match="between 0.5 and 1.0"):
        LocationScaleHierarchicalBootstrapSpec(interval_level=1.0)
    with pytest.raises(ValueError, match="non-negative integer"):
        LocationScaleHierarchicalBootstrapSpec(seed=-1)
    with pytest.raises(ValueError, match="positive integer"):
        LocationScaleHierarchicalBootstrapSpec(max_refit_rows=0)


def _dummy_results():
    fingerprint = "0" * 64
    group_effects = pd.DataFrame()
    independent_spec = HierarchicalLocationScaleSpec(
        outcome_col="y",
        group_col="participant_id",
    )
    independent = HierarchicalLocationScaleResult(
        spec=independent_spec,
        location_terms=("Intercept",),
        scale_terms=("Intercept",),
        location_coef=np.array([0.0]),
        scale_coef=np.array([0.0]),
        tau_location=0.4,
        tau_scale=0.2,
        log_likelihood=-1.0,
        converged=True,
        optimizer_status=0,
        optimizer_message="ok",
        optimizer_iterations=1,
        n_obs=8,
        n_groups=4,
        group_effects=group_effects,
        input_fingerprint_sha256=fingerprint,
        model_fingerprint_sha256=fingerprint,
    )
    correlated_spec = CorrelatedLocationScaleSpec(
        outcome_col="y",
        group_col="participant_id",
    )
    correlated = CorrelatedLocationScaleResult(
        spec=correlated_spec,
        location_terms=("Intercept",),
        scale_terms=("Intercept",),
        location_coef=np.array([0.0]),
        scale_coef=np.array([0.0]),
        tau_location=0.4,
        tau_scale=0.2,
        rho_location_scale=0.3,
        log_likelihood=-1.0,
        converged=True,
        optimizer_status=0,
        optimizer_message="ok",
        optimizer_iterations=1,
        n_obs=8,
        n_groups=4,
        group_effects=group_effects,
        input_fingerprint_sha256=fingerprint,
        model_fingerprint_sha256=fingerprint,
    )
    slope_spec = LocationRandomSlopeScaleSpec(
        outcome_col="y",
        group_col="participant_id",
        random_slope_predictor="x",
        location_predictors=("x",),
    )
    slope = LocationRandomSlopeScaleResult(
        spec=slope_spec,
        location_terms=("Intercept", "x"),
        scale_terms=("Intercept",),
        location_coef=np.array([0.0, 0.0]),
        scale_coef=np.array([0.0]),
        tau_location_intercept=0.4,
        tau_location_slope=0.25,
        tau_scale=0.2,
        log_likelihood=-1.0,
        converged=True,
        optimizer_status=0,
        optimizer_message="ok",
        optimizer_iterations=1,
        n_obs=8,
        n_groups=4,
        group_effects=group_effects,
        input_fingerprint_sha256=fingerprint,
        model_fingerprint_sha256=fingerprint,
    )
    correlated_slope_spec = CorrelatedLocationRandomSlopeScaleSpec(
        outcome_col="y",
        group_col="participant_id",
        random_slope_predictor="x",
        location_predictors=("x",),
    )
    correlated_slope = CorrelatedLocationRandomSlopeScaleResult(
        spec=correlated_slope_spec,
        location_terms=("Intercept", "x"),
        scale_terms=("Intercept",),
        location_coef=np.array([0.0, 0.0]),
        scale_coef=np.array([0.0]),
        tau_location_intercept=0.4,
        tau_location_slope=0.25,
        tau_scale=0.2,
        rho_location_intercept_slope=0.35,
        log_likelihood=-1.0,
        converged=True,
        optimizer_status=0,
        optimizer_message="ok",
        optimizer_iterations=1,
        n_obs=8,
        n_groups=4,
        group_effects=group_effects,
        input_fingerprint_sha256=fingerprint,
        model_fingerprint_sha256=fingerprint,
    )
    return independent, correlated, slope, correlated_slope



def test_simulation_draws_fresh_population_effects_and_residuals_without_using_eb():
    independent, _, _, _ = _dummy_results()
    independent.group_effects.loc[0, "impossible_eb_value"] = 1.0e12
    data = pd.DataFrame(
        {
            "participant_id": ["a", "a", "b", "b"],
            "y": [99.0, 99.0, 99.0, 99.0],
        }
    )
    seed = 47
    simulated, effects_fingerprint = _simulate_hierarchical_outcome(
        independent,
        data,
        rng=np.random.default_rng(seed),
    )

    replay = np.random.default_rng(seed)
    z = replay.standard_normal((2, 2))
    location_effects = independent.tau_location * z[:, 0]
    scale_effects = independent.tau_scale * z[:, 1]
    group_codes = np.array([0, 0, 1, 1])
    expected_sigma = np.exp(scale_effects[group_codes])
    expected = (
        location_effects[group_codes]
        + expected_sigma * replay.standard_normal(len(data))
    )

    np.testing.assert_allclose(simulated["y"], expected)
    assert simulated["participant_id"].tolist() == data["participant_id"].tolist()
    assert effects_fingerprint == fingerprint_frame(
        pd.DataFrame(
            {
                "participant_id": ["a", "b"],
                "location_intercept": location_effects,
                "log_scale_intercept": scale_effects,
            }
        )
    )


def test_population_effect_draws_follow_each_family_covariance_parameterization():
    group_levels = ("a", "b", "c", "d")
    independent, correlated, slope, correlated_slope = _dummy_results()

    rng = np.random.default_rng(17)
    observed = _draw_population_effects(independent, group_levels, rng)
    expected_z = np.random.default_rng(17).standard_normal((4, 2))
    np.testing.assert_allclose(
        observed["location_intercept"],
        independent.tau_location * expected_z[:, 0],
    )
    np.testing.assert_allclose(
        observed["log_scale_intercept"],
        independent.tau_scale * expected_z[:, 1],
    )

    rng = np.random.default_rng(23)
    observed = _draw_population_effects(correlated, group_levels, rng)
    expected_z = np.random.default_rng(23).standard_normal((4, 2))
    rho = correlated.rho_location_scale
    np.testing.assert_allclose(
        observed["log_scale_intercept"],
        correlated.tau_scale
        * (rho * expected_z[:, 0] + np.sqrt(1.0 - rho**2) * expected_z[:, 1]),
    )

    rng = np.random.default_rng(29)
    observed = _draw_population_effects(slope, group_levels, rng)
    expected_z = np.random.default_rng(29).standard_normal((4, 3))
    np.testing.assert_allclose(
        observed["location_slope"],
        slope.tau_location_slope * expected_z[:, 1],
    )

    rng = np.random.default_rng(31)
    observed = _draw_population_effects(correlated_slope, group_levels, rng)
    expected_z = np.random.default_rng(31).standard_normal((4, 3))
    rho = correlated_slope.rho_location_intercept_slope
    np.testing.assert_allclose(
        observed["location_slope"],
        correlated_slope.tau_location_slope
        * (rho * expected_z[:, 0] + np.sqrt(1.0 - rho**2) * expected_z[:, 1]),
    )


def _correlated_slope_synthetic(seed: int = 419) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows: list[dict[str, float | str]] = []
    x_grid = np.linspace(-1.5, 1.5, 12)
    rho = 0.25
    for group_index in range(24):
        z0, z1 = rng.normal(size=2)
        b0 = 0.45 * z0
        b1 = 0.24 * (rho * z0 + np.sqrt(1.0 - rho**2) * z1)
        c = rng.normal(0.0, 0.14)
        for x in x_grid:
            sigma = np.exp(np.log(0.62) + 0.05 * x + c)
            mean = 1.30 + 0.75 * x + b0 + b1 * x
            rows.append(
                {
                    "participant_id": f"P{group_index:02d}",
                    "condition": float(x),
                    "outcome": float(rng.normal(mean, sigma)),
                }
            )
    return pd.DataFrame(rows)


def test_hierarchical_bootstrap_supports_correlated_random_slope_family():
    data = _correlated_slope_synthetic()
    model_spec = CorrelatedLocationRandomSlopeScaleSpec(
        outcome_col="outcome",
        group_col="participant_id",
        random_slope_predictor="condition",
        location_predictors=("condition",),
        scale_predictors=("condition",),
        quadrature_points=3,
        min_group_size=4,
        max_iter=500,
        tolerance=1e-6,
    )
    fitted = fit_correlated_location_random_slope_scale(data, spec=model_spec)
    assert fitted.converged
    bootstrap = bootstrap_location_scale_hierarchy(
        fitted,
        data,
        spec=LocationScaleHierarchicalBootstrapSpec(
            n_simulations=2,
            seed=313,
            interval_level=0.90,
            max_refit_rows=1_000,
        ),
    )
    assert bootstrap.model_family == "correlated_location_random_slope_scale"
    parameter_ids = {row["parameter_id"] for row in bootstrap.parameter_inventory}
    assert "random_sd::location_slope" in parameter_ids
    assert "random_correlation::location_intercept_slope" in parameter_ids
    assert len(bootstrap.refit_ledger) == 2
    certificate = build_location_scale_hierarchical_bootstrap_certificate(bootstrap)
    validate_location_scale_hierarchical_bootstrap_certificate(certificate)
