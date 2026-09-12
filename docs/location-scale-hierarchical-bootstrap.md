# Hierarchical parametric bootstrap

GazeForge provides a **design-conditional hierarchical parametric bootstrap** for the four Gaussian location-scale model families currently supported by this bootstrap adapter. It is the population-random-effect extension of the conditional refit calibration, but it has a different inferential target.

The method asks: **under this fitted hierarchical model, with the observed participant/predictor design held fixed, what parameter estimates would the same fitting procedure produce across repeated model-generated datasets?**

It approximates a model-based parameter sampling distribution. It does not establish that the fitted model is true, robust to misspecification, or causally identified.

## Generating process

The base result must pass its existing GazeForge model-certificate validator, and the supplied table must reproduce the exact modelling-input fingerprint stored by the fit.

For every simulation replicate, GazeForge retains:

- the original row count and row order;
- the observed participant identities and group sizes;
- all observed location and scale predictors; and
- the fitted model specification.

Unlike conditional refit residual calibration, the empirical-Bayes participant effects from the observed sample are **not reused**. Fresh participant effects are drawn from the fitted population distribution.

For the independent random-intercept family,

```text
b_g ~ Normal(0, tau_location^2)
c_g ~ Normal(0, tau_log_scale^2)

mu_i* = X_i beta + b_g
log(sigma_i*) = Z_i gamma + c_g
y_i* = mu_i* + sigma_i* epsilon_i
epsilon_i ~ Normal(0, 1)
```

For the correlated random-intercept family, `(b_g, c_g)` is drawn from the fitted bivariate Gaussian using the fitted location/log-scale correlation.

For the random-slope families,

```text
mu_i* = X_i beta + b0_g + b1_g w_i
log(sigma_i*) = Z_i gamma + c_g
```

where `w_i` is the prespecified random-slope predictor. In the independent family, `(b0_g, b1_g, c_g)` are independent population Gaussian effects. In the correlated-slope family, `(b0_g, b1_g)` use the fitted intercept/slope correlation and `c_g` remains independent.

The separate full-3×3-covariance random-slope family is not supported by this bootstrap adapter in this tranche. Base-model certification does not imply bootstrap parity.

The generating fixed effects, variance components, and supported correlations are the fitted base-model estimates. The bootstrap therefore conditions on those fitted generating values.

## Refit and parameter inventory

Every simulated table is refitted from scratch with the same certified model specification. Every replicate must converge and produce a valid model certificate. A failed, boundary-censored, non-converged, or otherwise non-certifiable replicate aborts the bootstrap; failed replicates are never silently discarded or replaced.

The canonical parameter inventory includes:

| Family | Bootstrapped parameters |
| --- | --- |
| Independent location-scale | all location fixed effects; all log-scale fixed effects; location-intercept SD; log-scale-intercept SD |
| Correlated location-scale | the above plus the location/log-scale random-effect correlation |
| Independent location random slope | all location fixed effects; all log-scale fixed effects; location-intercept SD; location-slope SD; log-scale-intercept SD |
| Correlated location random slope | the above plus the location-intercept/location-slope correlation |

Scale-equation fixed effects remain on the fitted **log-sigma scale**. The bootstrap does not silently convert them to sigma ratios.

For each parameter, the summary reports:

- the observed fitted estimate;
- bootstrap mean;
- bootstrap standard error;
- bootstrap bias;
- lower percentile limit; and
- upper percentile limit.

The interval is a percentile interval from the model-based bootstrap distribution. No fixed-effect p-value is produced.

## What is propagated

This tranche propagates two model-generated sources of repeated-sample variation:

1. fresh participant random effects drawn from the fitted population hierarchy; and
2. fresh row-level Gaussian residual errors.

The same model is then re-estimated in every replicate, so optimizer/refit variability induced by those generated datasets is represented as well.

For model-based parameter uncertainty, this targets a broader repeated-sample variation than conditional refit residual calibration because the participant effects are newly sampled from the fitted population distribution rather than held at their empirical-Bayes values.

## What remains conditional

The method is **design-conditional**. It does not resample or regenerate:

- participant counts;
- participant group sizes;
- covariate distributions;
- treatment/condition assignments;
- missingness mechanisms; or
- the fitted model family itself.

It is not a nonparametric participant/cluster bootstrap and it does not integrate a Bayesian posterior for random effects or fixed parameters.

For the correlated location random-slope family, the intercept/slope covariance is interpreted in the exact fitted predictor-origin parameterization. The bootstrap preserves that observed predictor design and does not promote the resulting interval to a zero-point-invariant covariance claim.

## Reproducibility and lineage

Each replicate is bound to a deterministic ledger containing:

- simulation index;
- fingerprint of the freshly sampled population random effects;
- fingerprint of the complete simulated modelling input;
- refitted model fingerprint;
- refitted model-certificate fingerprint; and
- the complete canonical parameter-estimate mapping.

The ledger, parameter inventory, summary, original fitted-model identity, original model certificate, exact modelling input, and bootstrap specification all participate in deterministic bootstrap identity.

With the same certified base fit, exact input, implementation, specification, and seed, the generated bootstrap is deterministic.

## Scientific claim boundary

The certificate explicitly records that the method:

- resamples population random effects;
- resamples residual errors;
- preserves the observed design;
- refits the same model in every replicate;
- approximates a **model-based parameter sampling distribution**; and
- computes percentile intervals.

It explicitly does **not** claim:

- reuse of empirical-Bayes random effects;
- posterior integration of participant-effect uncertainty;
- nonparametric cluster resampling;
- robustness to model misspecification;
- guaranteed frequentist coverage;
- fixed-effect p-values;
- global model adequacy or distributional correctness;
- causal effects; or
- device, sensor, or measurement validity.

Certificate validation fails closed if those boundaries are promoted.

## Computational guard is not an inferential threshold

`max_refit_rows` limits `n_observations × n_simulations` to prevent accidental computational explosions. It is a resource safeguard only.

The schema permits two simulations so the complete scientific-software path can be tested economically. Two replicates are not an adequate scientific bootstrap. Real analyses require a simulation budget sufficient for stable standard errors and interval quantiles, and analysts should evaluate Monte Carlo stability.

Existing quadrature, optimizer, variance-component, and correlation bounds remain numerical safeguards inherited from the fitted model families. They are not substantive cutoffs.

## Relationship to the two residual calibrations

Use **fixed-fit residual calibration** for conditional residual geometry against a standard-normal reference while keeping the fitted model fixed.

Use **conditional refit residual calibration** when the residual reference should include refitting variability but retain the observed empirical-Bayes participant effects in the generating surface.

Use **hierarchical parametric bootstrap** when the target is the model-based sampling distribution of fitted parameters and participant effects should be freshly drawn from the fitted population hierarchy.

These methods answer different questions and use separate certificate schemas.