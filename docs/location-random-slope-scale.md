# Location random-slope scale model

GazeForge provides a **Gaussian hierarchical location-scale model with one participant random slope in the location equation**. It is designed for repeated eye-tracking and multimodal outcomes when participants may differ not only in their baseline conditional mean and conditional dispersion, but also in their response to one prespecified location predictor.

This is a deliberately narrow extension of the independent random-intercept location-scale model. It does not silently promote the model to an unrestricted random-effects covariance structure.

## Model

For observation `i` from participant `g`:

```text
y_i ~ Normal(mu_i, sigma_i)
mu_i = X_i beta + b0_g + b1_g * w_i
log(sigma_i) = Z_i gamma + c_g

b0_g ~ Normal(0, tau_location_intercept^2)
b1_g ~ Normal(0, tau_location_slope^2)
c_g  ~ Normal(0, tau_scale^2)
```

The three participant effects are **independent at the population level** in this model family. `w` is the single `random_slope_predictor`, and it must also appear in `location_predictors` so that the corresponding population-average fixed slope is estimated.

The model therefore separates:

- population-average location effects;
- participant-specific location intercept deviations;
- participant-specific deviations from one population-average location slope;
- population-average log-scale effects; and
- participant-specific log-scale intercept deviations.

The scale equation models the logarithm of the conditional **standard deviation**, not the variance.

## Estimation

`fit_location_random_slope_scale()` estimates both equations and all three random-effect standard deviations jointly by marginal maximum likelihood.

Participant effects are integrated with **three-dimensional adaptive Gauss-Hermite quadrature (AGHQ)**. For each participant, the adaptive rule is centred on a three-dimensional posterior mode. GazeForge obtains that mode with an exact-Hessian trust-region optimizer before applying the local Hessian transformation used by adaptive quadrature. This avoids treating an unstable inner optimizer as an innocuous implementation detail of the outer marginal likelihood.

All three random-effect standard deviations are optimized on log scales within finite numerical evaluation ranges. If the location-intercept, location-slope, or log-scale variance component reaches a package-imposed lower or upper limit, GazeForge rejects the fit as **boundary-censored** before empirical-Bayes participant effects are recovered. Result and certificate validation independently enforce the same rule, including against fully re-signed boundary-valued identities. These limits are computational safeguards, not scientific thresholds.

```python
from gazeforge.location_random_slope_scale import (
    LocationRandomSlopeScaleSpec,
    fit_location_random_slope_scale,
)

spec = LocationRandomSlopeScaleSpec(
    outcome_col="fixation_duration_ms",
    group_col="participant_id",
    random_slope_predictor="condition",
    location_predictors=("condition", "trial_index"),
    scale_predictors=("condition",),
    quadrature_points=5,
)

fit = fit_location_random_slope_scale(samples, spec=spec)
fit.fixed_effects()
```

Predictors must already be finite numeric columns. Dummy coding, transformations, centring, interactions, contrasts, and the scientific choice of the random-slope predictor remain explicit analysis decisions.

Every participant must have a numerically identifiable random intercept/random slope design. Concretely, the participant-level matrix `[Intercept, random_slope_predictor]` must have **numerical rank 2** under NumPy's matrix-rank criterion. Exact value distinctness alone is not sufficient: a predictor with an extreme offset can contain different values while remaining numerically collinear with the intercept. When this guard fails, centre or rescale the random-slope predictor and re-evaluate the analysis specification rather than bypassing the check.

## Relationship to the other location-scale families

Use `gazeforge.hierarchical_location_scale` when independent participant location and log-scale random intercepts are sufficient.

Use `gazeforge.correlated_location_scale` when the scientific target is the population correlation between the participant location intercept and log-scale intercept.

Use this random-slope family when the scientific target instead requires **participant heterogeneity in one location effect**. This family keeps the location intercept, location slope, and log-scale intercept independent. It does not estimate correlations among those three effects.

Keeping these as separate model and certificate families prevents a stronger random-effects structure from silently changing the meaning of previously frozen analyses.

## Participant effects and prediction

The fitted result contains empirical-Bayes summaries for the participant location intercept, location slope, and log-scale intercept.

For participants observed during fitting, `predict_location_random_slope_scale()` can add those empirical-Bayes effects. For a genuinely new participant, the default is a population-level prediction because that participant's random effects are unknown.

```python
from gazeforge.location_random_slope_scale import (
    predict_location_random_slope_scale,
)

pred = predict_location_random_slope_scale(fit, new_rows)
```

Set `allow_new_groups=False` when an analysis protocol should fail on unseen participant identities rather than use population-level prediction.

## Diagnostics

`location_random_slope_scale_diagnostics()` returns fitted conditional location, fitted conditional scale, raw residuals, and standardized residuals. These outputs are diagnostics, not automatic inferential tests.

```python
from gazeforge.location_random_slope_scale import (
    location_random_slope_scale_diagnostics,
)

diagnostics = location_random_slope_scale_diagnostics(fit, samples)
```

The Gaussian conditional-outcome assumption should be assessed scientifically. Strongly skewed positive outcomes, bounded outcomes, heavy tails, zero inflation, or discrete outcomes can require transformation or a different distribution.

## Reproducibility certificate

The model has its own certificate schema. A fitted certificate binds:

- the canonical model specification, including the random-slope predictor;
- location and log-scale fixed effects;
- the location-intercept, location-slope, and log-scale random-effect standard deviations;
- marginal log-likelihood;
- the empirical-Bayes participant table fingerprint;
- the exact modelling-input fingerprint; and
- optimizer convergence metadata.

```python
from gazeforge.location_random_slope_scale import (
    build_location_random_slope_scale_certificate,
    freeze_location_random_slope_scale_certificate,
)

certificate = build_location_random_slope_scale_certificate(fit)
freeze_location_random_slope_scale_certificate(
    fit,
    "results/location-random-slope-scale.json",
)
```

`validate_location_random_slope_scale_certificate()` fails closed on tampering or scientific-claim promotion. Frozen certificate files are protected against overwrite by default. Mutating fitted-result content does not create a new scientifically valid identity merely by recomputing an outer fingerprint, and re-signing a result or certificate at an artificial variance-component boundary remains invalid.

## Scientific claim boundary

This model supports:

- one grouping variable;
- one participant random intercept in the location equation;
- one participant random slope for one prespecified location predictor;
- one participant random intercept in the log-scale equation;
- independent Gaussian population distributions for those three effects; and
- a Gaussian conditional outcome fitted with 3D AGHQ.

It does **not** currently provide:

- correlations among the three random effects or an unrestricted 3 x 3 covariance matrix;
- more than one location random slope;
- log-scale random slopes;
- nested or crossed grouping structures;
- fixed-effect p-values;
- causal identification;
- device or measurement validity;
- known random effects for unseen participants; or
- automatic interpretation of motion-quality reliability weights as likelihood weights.

A fitted random-slope standard deviation is evidence of modelled participant heterogeneity under this specification. It is not, by itself, a causal interaction, a sensor-validity statement, or proof that every participant has a reliably distinct individual slope.

## Numerical guidance

The default is five adaptive Gauss-Hermite points per random-effect dimension. Supported orders are odd integers from 3 through 9. Because quadrature is three-dimensional, the per-participant node count grows with the **cube** of the requested order.

For stable estimation:

- retain enough repeated observations within each participant;
- require numerical rank 2 for every participant-level `[Intercept, random_slope_predictor]` design;
- avoid rank-deficient fixed-effect design matrices;
- centre or scale continuous predictors when magnitudes or offsets differ substantially;
- inspect quadrature-order sensitivity for difficult fits;
- treat a random-effect SD boundary rejection as evidence that the variance component is not identified as an interior estimate under the current numerical/model specification rather than clipping or certifying the package boundary; and
- interpret optimizer convergence as a numerical result, not proof that the Gaussian or independent-random-effect assumptions are scientifically adequate.

The participant-level rank check, supported quadrature ceiling, and random-effect evaluation limits are computational guards, not substantive thresholds.