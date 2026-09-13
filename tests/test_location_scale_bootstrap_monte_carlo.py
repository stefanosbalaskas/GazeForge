from copy import deepcopy

import numpy as np
import pytest
from scipy.stats import binom

from gazeforge import _location_scale_hierarchical_bootstrap_core as core
from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import SchemaError
from gazeforge.location_scale_bootstrap_monte_carlo import (
    LocationScaleBootstrapMonteCarloSpec,
    assess_location_scale_bootstrap_monte_carlo,
    build_location_scale_bootstrap_monte_carlo_certificate,
    freeze_location_scale_bootstrap_monte_carlo_certificate,
    validate_location_scale_bootstrap_monte_carlo_certificate,
)
from gazeforge.location_scale_hierarchical_bootstrap import (
    LocationScaleHierarchicalBootstrapResult,
    LocationScaleHierarchicalBootstrapSpec,
    validate_location_scale_hierarchical_bootstrap_certificate,
)


def _sha(character: str) -> str:
    return character * 64


def _synthetic_bootstrap(
    n_simulations: int = 200,
) -> LocationScaleHierarchicalBootstrapResult:
    spec = LocationScaleHierarchicalBootstrapSpec(
        n_simulations=n_simulations,
        seed=811,
        interval_level=0.95,
        max_refit_rows=max(100, 10 * n_simulations),
    )
    inventory = core._canonical_inventory(
        [
            {
                "parameter_id": "location_fixed::Intercept",
                "component": "location_fixed",
                "term": "Intercept",
                "observed": 1.0,
            },
            {
                "parameter_id": "random_sd::location_intercept",
                "component": "random_sd",
                "term": "location_intercept",
                "observed": 0.35,
            },
        ]
    )
    ledger = []
    for index in range(n_simulations):
        location = (
            1.0
            + 0.22 * np.sin(0.37 * index)
            + 0.05 * np.cos(0.11 * index)
        )
        random_sd = (
            0.35
            + 0.04 * np.sin(0.19 * index + 0.3)
            + 0.01 * np.cos(0.07 * index)
        )
        ledger.append(
            {
                "simulation_index": index,
                "population_random_effects_fingerprint_sha256": _sha("a"),
                "simulated_input_fingerprint_sha256": _sha("b"),
                "model_fingerprint_sha256": _sha("c"),
                "model_certificate_fingerprint_sha256": _sha("d"),
                "parameter_estimates": {
                    "location_fixed::Intercept": float(location),
                    "random_sd::location_intercept": float(random_sd),
                },
            }
        )
    canonical_ledger = core._canonical_refit_ledger(
        ledger,
        inventory=inventory,
        n_simulations=n_simulations,
    )
    ledger_fingerprint = core._refit_ledger_fingerprint(
        canonical_ledger,
        inventory=inventory,
        n_simulations=n_simulations,
    )
    summary = core._bootstrap_summary(
        inventory,
        canonical_ledger,
        interval_level=spec.interval_level,
    )
    summary_fingerprint = core._summary_fingerprint(summary)
    identity = core._bootstrap_identity_payload(
        spec=spec,
        model_family="independent_location_scale",
        model_fingerprint=_sha("e"),
        base_model_certificate_fingerprint=_sha("f"),
        input_fingerprint=_sha("1"),
        n_obs=10,
        n_groups=2,
        parameter_inventory=inventory,
        refit_ledger_fingerprint=ledger_fingerprint,
        summary_fingerprint=summary_fingerprint,
    )
    return LocationScaleHierarchicalBootstrapResult(
        spec=spec,
        model_family="independent_location_scale",
        model_fingerprint_sha256=_sha("e"),
        base_model_certificate_fingerprint_sha256=_sha("f"),
        input_fingerprint_sha256=_sha("1"),
        n_obs=10,
        n_groups=2,
        parameter_inventory=inventory,
        refit_ledger=canonical_ledger,
        refit_ledger_fingerprint_sha256=ledger_fingerprint,
        summary=summary,
        summary_fingerprint_sha256=summary_fingerprint,
        bootstrap_fingerprint_sha256=benchmark_fingerprint(identity),
    )


@pytest.fixture(scope="module")
def assessment():
    return assess_location_scale_bootstrap_monte_carlo(
        _synthetic_bootstrap()
    )


def test_monte_carlo_precision_matches_mean_and_jackknife_definitions(
    assessment,
):
    diagnostics = assessment.parameters()
    row = diagnostics.loc[
        diagnostics["parameter_id"] == "location_fixed::Intercept"
    ].iloc[0]
    source = _synthetic_bootstrap()
    values = source.replicates()["location_fixed::Intercept"].to_numpy()
    expected_se = float(np.std(values, ddof=1))
    assert row["bootstrap_se"] == pytest.approx(expected_se)
    assert row["mean_mcse"] == pytest.approx(
        expected_se / np.sqrt(len(values))
    )

    leave_one_out = np.asarray(
        [
            np.std(np.delete(values, index), ddof=1)
            for index in range(len(values))
        ],
        dtype=float,
    )
    expected_jackknife = np.sqrt(
        (len(values) - 1.0)
        / len(values)
        * np.sum((leave_one_out - leave_one_out.mean()) ** 2)
    )
    assert row["bootstrap_se_mcse_jackknife"] == pytest.approx(
        expected_jackknife
    )


def test_percentile_endpoint_bands_use_binomial_order_statistics(assessment):
    row = assessment.diagnostics[0]
    n = assessment.n_simulations
    alpha = 1.0 - assessment.bootstrap_interval_level
    confidence_alpha = 1.0 - assessment.spec.confidence_level
    lower_probability = alpha / 2.0
    upper_probability = 1.0 - alpha / 2.0

    expected_lower_rank = int(
        binom.ppf(
            confidence_alpha / 2.0,
            n,
            lower_probability,
        )
    )
    expected_lower_upper_rank = (
        int(
            binom.ppf(
                1.0 - confidence_alpha / 2.0,
                n,
                lower_probability,
            )
        )
        + 1
    )
    expected_upper_rank = int(
        binom.ppf(
            confidence_alpha / 2.0,
            n,
            upper_probability,
        )
    )
    expected_upper_upper_rank = (
        int(
            binom.ppf(
                1.0 - confidence_alpha / 2.0,
                n,
                upper_probability,
            )
        )
        + 1
    )

    assert row["interval_lower_mc_rank_lower"] == expected_lower_rank
    assert (
        row["interval_lower_mc_rank_upper"]
        == expected_lower_upper_rank
    )
    assert row["interval_upper_mc_rank_lower"] == expected_upper_rank
    assert (
        row["interval_upper_mc_rank_upper"]
        == expected_upper_upper_rank
    )
    assert (
        row["interval_lower_mc_binomial_coverage"]
        >= assessment.spec.confidence_level
    )
    assert (
        row["interval_upper_mc_binomial_coverage"]
        >= assessment.spec.confidence_level
    )


def test_small_tail_bands_can_be_explicitly_unbounded():
    result = assess_location_scale_bootstrap_monte_carlo(
        _synthetic_bootstrap(20)
    )
    row = result.diagnostics[0]
    assert row["interval_lower_mc_rank_lower"] == 0
    assert row["interval_lower_mc_band_lower"] is None
    assert row["interval_upper_mc_rank_upper"] == 21
    assert row["interval_upper_mc_band_upper"] is None


def test_monte_carlo_assessment_requires_three_bootstrap_simulations():
    with pytest.raises(SchemaError, match="at least three"):
        assess_location_scale_bootstrap_monte_carlo(
            _synthetic_bootstrap(2)
        )


def test_monte_carlo_certificate_roundtrip_binds_source_bootstrap(assessment):
    certificate = build_location_scale_bootstrap_monte_carlo_certificate(
        assessment
    )
    validate_location_scale_bootstrap_monte_carlo_certificate(certificate)
    validate_location_scale_hierarchical_bootstrap_certificate(
        certificate["source_bootstrap_certificate"]
    )
    assert (
        certificate["assessment"]["source_bootstrap_fingerprint_sha256"]
        == certificate["source_bootstrap_certificate"][
            "bootstrap_fingerprint_sha256"
        ]
    )
    assert (
        certificate["claim_boundary"][
            "automatic_stability_threshold_applied"
        ]
        is False
    )
    assert (
        certificate["claim_boundary"][
            "bootstrap_interval_coverage_guaranteed"
        ]
        is False
    )


def test_resigned_diagnostic_tamper_is_rejected(assessment):
    certificate = build_location_scale_bootstrap_monte_carlo_certificate(
        assessment
    )
    attacked = deepcopy(certificate)
    attacked["diagnostics"][0]["mean_mcse"] += 0.001
    body = {
        key: value
        for key, value in attacked.items()
        if key != "certificate_fingerprint_sha256"
    }
    attacked["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)
    with pytest.raises(SchemaError, match="inconsistent"):
        validate_location_scale_bootstrap_monte_carlo_certificate(attacked)


def test_resigned_source_bootstrap_claim_promotion_is_rejected(assessment):
    certificate = build_location_scale_bootstrap_monte_carlo_certificate(
        assessment
    )
    attacked = deepcopy(certificate)
    source = attacked["source_bootstrap_certificate"]
    source["claim_boundary"]["frequentist_coverage_guaranteed"] = True
    source_body = {
        key: value
        for key, value in source.items()
        if key != "certificate_fingerprint_sha256"
    }
    source["certificate_fingerprint_sha256"] = benchmark_fingerprint(
        source_body
    )
    body = {
        key: value
        for key, value in attacked.items()
        if key != "certificate_fingerprint_sha256"
    }
    attacked["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)
    with pytest.raises(SchemaError, match="claim boundary"):
        validate_location_scale_bootstrap_monte_carlo_certificate(attacked)


def test_monte_carlo_claim_promotion_is_rejected(assessment):
    certificate = build_location_scale_bootstrap_monte_carlo_certificate(
        assessment
    )
    attacked = deepcopy(certificate)
    attacked["claim_boundary"]["automatic_stability_threshold_applied"] = True
    body = {
        key: value
        for key, value in attacked.items()
        if key != "certificate_fingerprint_sha256"
    }
    attacked["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)
    with pytest.raises(SchemaError, match="claim boundary"):
        validate_location_scale_bootstrap_monte_carlo_certificate(attacked)


def test_resigned_unknown_certificate_field_is_rejected(assessment):
    certificate = build_location_scale_bootstrap_monte_carlo_certificate(
        assessment
    )
    attacked = deepcopy(certificate)
    attacked["unsupported"] = True
    body = {
        key: value
        for key, value in attacked.items()
        if key != "certificate_fingerprint_sha256"
    }
    attacked["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)
    with pytest.raises(SchemaError, match="fields"):
        validate_location_scale_bootstrap_monte_carlo_certificate(attacked)


def test_result_mutation_is_rejected(assessment):
    original = assessment.diagnostics
    attacked = list(original)
    changed = dict(attacked[0])
    changed["mean_mcse"] += 0.001
    attacked[0] = changed
    object.__setattr__(assessment, "diagnostics", tuple(attacked))
    try:
        with pytest.raises(SchemaError, match="mutated"):
            build_location_scale_bootstrap_monte_carlo_certificate(
                assessment
            )
    finally:
        object.__setattr__(assessment, "diagnostics", original)


def test_invalid_monte_carlo_spec_fails_closed():
    with pytest.raises(ValueError, match="between 0.5 and 1.0"):
        LocationScaleBootstrapMonteCarloSpec(confidence_level=1.0)


def test_freeze_refuses_overwrite(tmp_path, assessment):
    target = tmp_path / "bootstrap-monte-carlo.json"
    freeze_location_scale_bootstrap_monte_carlo_certificate(
        assessment,
        target,
    )
    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        freeze_location_scale_bootstrap_monte_carlo_certificate(
            assessment,
            target,
        )
