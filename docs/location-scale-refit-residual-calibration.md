# Conditional refit residual calibration

GazeForge provides a separate **conditional parametric refit residual calibration** for the four currently certified Gaussian location-scale model families. It complements, rather than replaces, the cheaper fixed-fit residual calibration.

The diagnostic asks a narrow question: **how unusual are selected properties of the fitted conditional standardized residuals when compared with synthetic outcomes generated from this fitted conditional mean/scale surface and then analysed by refitting the same model specification?**

It does not turn that comparison into proof that the model is globally correct.

## What is simulated

The fitted result must first pass its existing model-certificate validator, and the supplied table must reproduce the exact modelling-input fingerprint stored by that result.

For each observed row, GazeForge obtains the fitted conditional location and sigma using the model's existing diagnostic path. For known participants this includes the fitted empirical-Bayes participant effects used by that diagnostic. A simulation replicate then replaces only the outcome with

```text
y_i* = fitted_location_i + fitted_sigma_i * z_i,
z_i ~ Normal(0, 1).
```

The observed predictors, participant identities, row order, and grouping structure are retained exactly. No new participant random effects are drawn.

## What is refitted

Every synthetic outcome table is fitted from scratch using the **same model specification** as the certified base fit. The supported families are:

- independent participant location/log-scale random intercepts;
- correlated participant location/log-scale random intercepts;
- one participant location random slope with independent location-intercept, location-slope, and log-scale random effects; and
- one participant location random slope with an estimated location-intercept/location-slope population correlation and an independent log-scale random intercept.

Each replicate must converge and produce a valid existing GazeForge model certificate. A failed, boundary-censored, non-converged, or otherwise non-certifiable replicate aborts the calibration. Failed replicates are never silently discarded or replaced.

The refitted standardized residuals are scored with the same metric inventory used by the fixed-fit diagnostic:

- residual mean and standard deviation;
- residual skewness and excess kurtosis;
- absolute-tail fraction;
- normal Q-Q RMSE;
- participant mean RMS; and
- participant log-second-moment RMS.

The resulting simulation distribution supplies the envelope, simulation mean, and simulation percentile for each observed metric.

## What the refit step adds

Unlike fixed-fit calibration, model parameters are re-estimated for every simulation replicate. The reference distribution therefore includes variability induced by applying the package's fitting procedure repeatedly to synthetic outcomes generated on the fitted conditional surface.

This is deliberately described as **estimation-procedure variability in the reference distribution**. It is not a claim that full parameter-estimation uncertainty has been quantified.

In particular, this implementation is conditional on the fitted row-level participant effects. It does **not**:

- draw new population random effects;
- integrate posterior uncertainty in participant random effects;
- perform a population-level hierarchical parametric bootstrap;
- provide confidence intervals or p-values for fixed effects;
- establish global model adequacy or distributional correctness;
- establish causal effects; or
- establish device, sensor, or measurement validity.

These boundaries are encoded directly in the refit-calibration certificate and validation fails closed if they are promoted.

## Refit lineage and reproducibility

The diagnostic records a deterministic refit ledger. Each simulation index is bound to:

- the refitted model fingerprint;
- the refitted model-certificate fingerprint; and
- the fingerprint of the refitted residual diagnostic frame.

The ledger itself, the observed residual frame, the summary table, the original model, the original model certificate, the exact modelling input, and the refit specification all participate in deterministic diagnostic identity.

The seed controls the synthetic standard-normal innovations. With the same certified base fit, exact input, package implementation, and specification, the diagnostic is deterministic.

## Computational guards are not scientific thresholds

`max_refit_rows` bounds `n_observations × n_simulations` to prevent accidental computational explosions. It is a package resource safeguard only and has no substantive or inferential meaning.

The schema permits as few as two simulations so that deterministic software tests can exercise the complete refit path economically. Such a tiny simulation count produces extremely coarse Monte Carlo envelopes and is **not** a recommended scientific analysis setting. Analysts are responsible for choosing a simulation budget adequate for their inferential/diagnostic precision and for checking Monte Carlo stability.

Similarly, existing quadrature-point, optimizer-iteration, variance-component, and correlation bounds remain numerical safeguards inherited from the fitted model families; they are not scientific cutoffs.

## Relationship to fixed-fit calibration

Use fixed-fit residual calibration when the target is the conditional residual geometry relative to an `N(0, 1)` reference while holding the fitted model fixed.

Use conditional refit residual calibration when the target is the same residual metric inventory but the reference should also reflect repeated re-estimation of the same model on synthetic outcomes generated from the fitted conditional surface.

Neither diagnostic establishes model truth. They answer related but different conditional diagnostic questions and therefore use separate certificate schemas.