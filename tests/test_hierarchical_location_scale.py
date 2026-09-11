import json
from copy import deepcopy
from dataclasses import FrozenInstanceError

import numpy as np
import pandas as pd
import pytest
from numpy.polynomial.hermite import hermgauss
from scipy.special import logsumexp

from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import SchemaError
from gazeforge.hierarchical_location_scale import (
    HierarchicalLocationScaleSpec,
    _adaptive_group_quadrature,
    _quadrature,
    build_hierarchical_location_scale_certificate,
    fit_hierarchical_location_scale,
    freeze_hierarchical_location_scale_certificate,
    hierarchical_location_scale_diagnostics,
    predict_hierarchical_location_scale,
    validate_hierarchical_location_scale_certificate,
)


def _synthetic_location_scale(
    seed: int = 4,
    *,
    groups: int = 14,
    n_per_group: int = 16,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows: list[tuple[str, float, float]] = []
    for group in range(groups):
        random_location = rng.normal(0.0, 0.55)
        random_log_scale = rng.normal(0.0, 0.22)
        x = rng.normal(size=n_per_group)
        location = 1.1 + 0.65 * x + random_location
        sigma = np.exp(-0.2 + 0.30 * x + random_log_scale)
        y = rng.normal(location, sigma)
        rows.extend(
            (f"p{group}", xx, yy)
            for xx, yy in zip(x, y, strict=True)
        )
    return pd.DataFrame(rows, columns=["participant_id", "x", "y"])


@pytest.fixture(scope="module")
def fitted_model():
    data = _synthetic_location_scale()
    spec = HierarchicalLocationScaleSpec(
        outcome_col="y",
        group_col="participant_id",
        location_predictors=("x",),
        scale_predictors=("x",),
        quadrature_points=5,
    )
    return data, fit_hierarchical_location_scale(data, spec=spec)


def test_fit_recovers_known_direction_and_variance_structure(fitted_model):
    _, fitted = fitted_model
    assert fitted.converged
    assert fitted.location_coef[1] == pytest.approx(0.65, abs=0.22)
    assert fitted.scale_coef[1] == pytest.approx(0.30, abs=0.18)
    assert fitted.tau_location > 0.10
    assert fitted.tau_scale > 0.03
    assert len(fitted.group_effects) == 14

    fixed = fitted.fixed_effects()
    scale_x = fixed.query(
        "equation == 'log_scale' and term == 'x'"
    ).iloc[0]
    assert scale_x["sigma_ratio"] == pytest.approx(
        np.exp(scale_x["estimate"])
    )


def test_prediction_uses_known_effects_and_population_for_new_groups(
    fitted_model,
):
    data, fitted = fitted_model
    known = predict_hierarchical_location_scale(fitted, data.iloc[:3])
    assert known["group_effect_used"].all()

    unseen = pd.DataFrame({"participant_id": ["new"], "x": [0.2]})
    population = predict_hierarchical_location_scale(fitted, unseen)
    assert not population["group_effect_used"].iloc[0]

    with pytest.raises(SchemaError, match="unseen groups"):
        predict_hierarchical_location_scale(
            fitted,
            unseen,
            allow_new_groups=False,
        )


def test_prediction_subset_rank_is_not_a_fit_requirement(fitted_model):
    _, fitted = fitted_model
    one_row = pd.DataFrame({"participant_id": ["new"], "x": [0.0]})
    predicted = predict_hierarchical_location_scale(fitted, one_row)
    assert np.isfinite(
        predicted[["location_mean", "sigma"]].to_numpy()
    ).all()


def test_diagnostics_are_finite(fitted_model):
    data, fitted = fitted_model
    diagnostics = hierarchical_location_scale_diagnostics(fitted, data)
    assert np.isfinite(diagnostics["standardized_residual"]).all()
    assert (diagnostics["sigma"] > 0).all()


def test_certificate_rejects_resigned_claim_promotion(fitted_model):
    _, fitted = fitted_model
    certificate = build_hierarchical_location_scale_certificate(fitted)
    validate_hierarchical_location_scale_certificate(certificate)

    promoted = deepcopy(certificate)
    promoted["claim_boundary"]["causal_effects_established"] = True
    body = {
        key: value
        for key, value in promoted.items()
        if key != "certificate_fingerprint_sha256"
    }
    promoted["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)

    with pytest.raises(SchemaError, match="claim boundary"):
        validate_hierarchical_location_scale_certificate(promoted)


def test_certificate_rejects_resigned_model_promotion(fitted_model):
    _, fitted = fitted_model
    certificate = build_hierarchical_location_scale_certificate(fitted)
    tampered = deepcopy(certificate)
    tampered["model"]["scale_fixed_effects"]["x"] = 4.0
    body = {
        key: value
        for key, value in tampered.items()
        if key != "certificate_fingerprint_sha256"
    }
    tampered["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)

    with pytest.raises(SchemaError, match="model fingerprint"):
        validate_hierarchical_location_scale_certificate(tampered)


def test_certificate_accepts_reordered_fixed_effect_keys(fitted_model):
    _, fitted = fitted_model
    certificate = build_hierarchical_location_scale_certificate(fitted)
    reordered = deepcopy(certificate)
    location = reordered["model"]["location_fixed_effects"]
    scale = reordered["model"]["scale_fixed_effects"]
    reordered["model"]["location_fixed_effects"] = {
        "x": location["x"],
        "Intercept": location["Intercept"],
    }
    reordered["model"]["scale_fixed_effects"] = {
        "x": scale["x"],
        "Intercept": scale["Intercept"],
    }
    validate_hierarchical_location_scale_certificate(reordered)


def test_result_mutation_is_detected_before_reporting_or_prediction(
    fitted_model,
):
    _, fitted = fitted_model
    fitted.location_coef[0] += 0.5
    try:
        with pytest.raises(SchemaError, match="result identity"):
            build_hierarchical_location_scale_certificate(fitted)
        with pytest.raises(SchemaError, match="result identity"):
            predict_hierarchical_location_scale(
                fitted,
                pd.DataFrame({"participant_id": ["new"], "x": [0.0]}),
            )
    finally:
        fitted.location_coef[0] -= 0.5


def test_result_metadata_are_structurally_frozen(fitted_model):
    _, fitted = fitted_model
    with pytest.raises(FrozenInstanceError):
        fitted.converged = False
    with pytest.raises(FrozenInstanceError):
        fitted.optimizer_status = 999


def test_certificate_freeze_is_json_roundtrip_safe_and_protected(
    fitted_model,
    tmp_path,
):
    _, fitted = fitted_model
    target = tmp_path / "location-scale.json"
    freeze_hierarchical_location_scale_certificate(fitted, target)
    validate_hierarchical_location_scale_certificate(
        json.loads(target.read_text(encoding="utf-8"))
    )
    with pytest.raises(FileExistsError):
        freeze_hierarchical_location_scale_certificate(fitted, target)


def test_invalid_spec_and_missing_group_identity_fail_closed():
    with pytest.raises(ValueError, match="odd integer"):
        HierarchicalLocationScaleSpec("y", "g", quadrature_points=4)
    with pytest.raises(ValueError, match="must be distinct"):
        HierarchicalLocationScaleSpec("y", "y")
    with pytest.raises(ValueError, match="reserved term"):
        HierarchicalLocationScaleSpec(
            "y",
            "participant_id",
            location_predictors=("Intercept",),
        )

    data = _synthetic_location_scale(groups=3, n_per_group=4)
    data.loc[0, "participant_id"] = None
    spec = HierarchicalLocationScaleSpec("y", "participant_id")
    with pytest.raises(SchemaError, match="missing group identity"):
        fit_hierarchical_location_scale(data, spec=spec)


def test_rank_deficient_fit_fails_closed():
    data = _synthetic_location_scale(groups=4, n_per_group=5)
    data["x_copy"] = data["x"]
    spec = HierarchicalLocationScaleSpec(
        "y",
        "participant_id",
        location_predictors=("x", "x_copy"),
        quadrature_points=3,
    )
    with pytest.raises(SchemaError, match="rank deficient"):
        fit_hierarchical_location_scale(data, spec=spec)


def test_adaptive_quadrature_is_stable_across_orders():
    data = _synthetic_location_scale(seed=7, groups=8, n_per_group=10)
    low = fit_hierarchical_location_scale(
        data,
        spec=HierarchicalLocationScaleSpec(
            "y",
            "participant_id",
            ("x",),
            ("x",),
            quadrature_points=3,
        ),
    )
    high = fit_hierarchical_location_scale(
        data,
        spec=HierarchicalLocationScaleSpec(
            "y",
            "participant_id",
            ("x",),
            ("x",),
            quadrature_points=7,
        ),
    )
    assert low.location_coef == pytest.approx(high.location_coef, abs=0.03)
    assert low.scale_coef == pytest.approx(high.scale_coef, abs=0.03)
    assert low.tau_location == pytest.approx(high.tau_location, abs=0.03)
    assert low.tau_scale == pytest.approx(high.tau_scale, abs=0.03)
    assert low.log_likelihood == pytest.approx(
        high.log_likelihood,
        abs=0.03,
    )


def test_adaptive_group_likelihood_matches_fixed_quadrature_reference():
    data = _synthetic_location_scale(
        seed=12,
        groups=2,
        n_per_group=5,
    ).query("participant_id == 'p0'")
    y = data["y"].to_numpy(float)
    x = data["x"].to_numpy(float)
    location_design = np.column_stack([np.ones(len(data)), x])
    scale_design = np.column_stack([np.ones(len(data)), x])
    beta = np.array([1.05, 0.6])
    gamma = np.array([-0.18, 0.25])
    tau_location = 0.5
    tau_scale = 0.2

    spec = HierarchicalLocationScaleSpec(
        "y",
        "participant_id",
        ("x",),
        ("x",),
        quadrature_points=7,
    )
    nodes, log_weights = _quadrature(spec)
    adaptive, _, _, _ = _adaptive_group_quadrature(
        y,
        location_design,
        scale_design,
        beta,
        gamma,
        tau_location,
        tau_scale,
        nodes,
        log_weights,
    )

    reference_nodes, reference_weights = hermgauss(31)
    log_values = []
    log_node_weights = []
    for first_index, first in enumerate(reference_nodes):
        for second_index, second in enumerate(reference_nodes):
            b = np.sqrt(2.0) * tau_location * first
            c = np.sqrt(2.0) * tau_scale * second
            residual = y - (location_design @ beta + b)
            log_scale = scale_design @ gamma + c
            log_likelihood = np.sum(
                -0.5 * np.log(2.0 * np.pi)
                - log_scale
                - 0.5 * residual**2 * np.exp(-2.0 * log_scale)
            )
            log_values.append(log_likelihood)
            log_node_weights.append(
                np.log(reference_weights[first_index])
                + np.log(reference_weights[second_index])
            )
    fixed_reference = float(
        logsumexp(
            np.asarray(log_values) + np.asarray(log_node_weights)
        )
        - np.log(np.pi)
    )
    assert adaptive == pytest.approx(fixed_reference, abs=2e-4)
