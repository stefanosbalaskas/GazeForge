# Location-scale residual calibration

GazeForge provides deterministic **simulation-calibrated residual diagnostics** for both hierarchical location-scale model families:

- `HierarchicalLocationScaleResult`, with independent participant location and log-scale random intercepts; and
- `CorrelatedLocationScaleResult`, with an estimated participant location/log-scale random-effect correlation.

The diagnostic asks a deliberately narrow question: **how unusual are selected properties of the fitted conditional standardized residuals relative to an `N(0, 1)` reference with the same number of observations and the same participant grouping structure?**

It does not turn that comparison into a proof that the model is correct or incorrect.

## Certifiable-model and exact-input requirement

Residual calibration is an in-sample fitted-model diagnostic. Before calibration starts, the supplied fitted result must pass its own existing GazeForge model-certificate validator. This means a structurally usable but non-converged fit cannot be promoted into a residual-calibration certificate through a weaker downstream path. For correlated models, the same gate also inherits the certified correlation-boundary protections.

The resulting base-model certificate fingerprint is bound into the residual-calibration identity. The supplied table must also reproduce the exact modelling-input fingerprint stored in the fitted result. Together, these checks bind the diagnostic to a certifiable fit and to the exact rows, participant identities, outcome, and predictors that produced that fit.

```python
from gazeforge.location_scale_residual_calibration import (
    LocationScaleResidualCalibrationSpec,
    calibrate_location_scale_residuals,
)

calibration = calibrate_location_scale_residuals(
    fit,
    samples,
    spec=LocationScaleResidualCalibrationSpec(
        n_simulations=500,
        seed=1729,
        envelope_level=0.95,
    ),
)

calibration.metrics()
```

A non-certifiable base fit, a changed modelling column, changed row ordering, or another fingerprinted input mismatch causes the diagnostic to fail closed rather than silently analysing a weaker or different fitted object.

## Reference simulation

For the fitted sample, GazeForge first obtains the conditional standardized residuals

```text
z_i = (y_i - fitted_location_i) / fitted_sigma_i
```

using the existing estimator-specific diagnostics. It then draws deterministic reference residual vectors from `N(0, 1)` using the configured seed.

Each replicate preserves:

- the observed number of rows;
- the original participant membership of every row; and
- the observed per-participant sample sizes used by the group-level metrics.

The fitted coefficients, variance components, random-effect correlation when applicable, and empirical-Bayes participant effects are **held fixed**. The model is not re-fitted for each replicate. Consequently, these reference envelopes do not propagate parameter-estimation uncertainty.

## Diagnostic metrics

Eight diagnostics are computed on the observed standardized residuals and on every simulated reference replicate.

| Metric | Interpretation |
|---|---|
| `residual_mean` | Centring of conditional standardized residuals around zero. |
| `residual_sd` | Overall standardized-residual dispersion relative to one. |
| `residual_skewness` | Asymmetry of the standardized-residual distribution. |
| `residual_excess_kurtosis` | Tail/peakedness departure relative to Gaussian kurtosis. |
| `absolute_tail_fraction` | Fraction with `abs(z)` above the configured threshold, default `1.96`. |
| `normal_qq_rmse` | Root-mean-square deviation of ordered residuals from corresponding standard-normal quantiles. |
| `group_mean_rms` | Root-mean-square participant mean standardized residual, retaining participant structure. |
| `group_log_second_moment_rms` | Root-mean-square participant log second moment; a group-sensitive dispersion diagnostic. |

For every metric, the output records the observed value, reference-simulation mean, lower and upper envelope bounds, simulation percentile, and whether the observed value lies outside the requested envelope.

`outside_envelope=True` is a **diagnostic signal only**. It is not a p-value, an automatic rejection rule, or proof of a particular form of misspecification. Multiple diagnostics are examined simultaneously and the fitted model parameters are treated as fixed in the simulation reference.

## Resource guard

The simulation cost scales with `n_observations × n_simulations`. `max_simulated_residual_draws` therefore provides an explicit fail-closed computational budget. The default limit is five million simulated standardized residual draws.

Raise that limit only as an explicit analysis decision. The package does not silently reduce the requested number of simulations or subsample the fitted data.

## Reproducibility certificate

A calibration result binds:

- the diagnostic specification and random seed;
- model family;
- exact fitted-model fingerprint;
- the validated base-model certificate fingerprint, including its convergence/integrity gate;
- exact fitting-input fingerprint;
- observation and participant counts;
- a fingerprint of the fitted residual table; and
- a canonical fingerprint of the metric/envelope table.

```python
from gazeforge.location_scale_residual_calibration import (
    build_location_scale_residual_calibration_certificate,
    freeze_location_scale_residual_calibration_certificate,
)

certificate = build_location_scale_residual_calibration_certificate(calibration)
freeze_location_scale_residual_calibration_certificate(
    calibration,
    "results/location-scale-residual-calibration.json",
)
```

Frozen JSON is validated independently of dictionary key insertion order. Existing files are protected from overwrite unless `overwrite=True` is explicitly requested.

## Scientific claim boundary

This facility establishes only that a deterministic conditional residual calibration calculation was performed for a base fit that passed its model-certificate gate, under the frozen fitted-model and simulator assumptions.

It does **not** establish:

- global model adequacy or distributional correctness;
- causal identification;
- device, sensor, or measurement validity;
- that the observed residuals are independent;
- that parameter uncertainty has been propagated; or
- that the model would pass a refit-based posterior-predictive or bootstrap goodness-of-fit procedure.

An envelope exceedance should motivate scientific inspection of the model specification, outcome distribution, transformations, predictor structure, participant structure, influential observations, and alternative models. It should not be automatically translated into a substantive conclusion.
