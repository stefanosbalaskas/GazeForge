# Correlated location random-slope scale model

GazeForge provides a separate **Gaussian hierarchical location-scale model with a correlated participant location intercept and location slope**. It addresses a specific limitation of the independent random-slope family: forcing the participant intercept and slope to be independent makes the model depend on the arbitrary zero point of the random-slope predictor.

## Model

For observation `i` from participant `g`:

```text
y_i ~ Normal(mu_i, sigma_i)
mu_i = X_i beta + b0_g + b1_g * w_i
log(sigma_i) = Z_i gamma + c_g

(b0_g, b1_g) ~ Normal(0, Sigma_location)
c_g ~ Normal(0, tau_scale^2)

Sigma_location = [ tau0^2                 rho * tau0 * tau1 ]
                 [ rho * tau0 * tau1      tau1^2             ]
```

The log-scale random intercept is independent of both location effects. This model therefore estimates exactly one population random-effect correlation: the correlation between the participant location intercept and the participant location slope.

`w` is the single `random_slope_predictor`, and it must also appear in `location_predictors` so the corresponding population-average fixed slope is present.

## Why the correlation matters

In the independent random-slope family, `Cov(b0, b1) = 0`. If the slope predictor is re-expressed around a different zero point, such as `w' = w - k`, the equivalent random intercept becomes:

```text
b0' = b0 + k * b1
```

and therefore:

```text
Cov(b0', b1) = Cov(b0, b1) + k * Var(b1)
```

A zero intercept-slope covariance at one predictor origin is generally non-zero at another. Consequently, an independence restriction changes the model family when the analyst merely changes the predictor's zero point.

The correlated 2 x 2 location block is closed under such finite affine zero-point shifts as long as the transformed covariance remains inside the package's numerical parameter bounds. This removes the scientific dependence on an arbitrary centring origin without introducing a full 3 x 3 covariance structure.

## Estimation

`fit_correlated_location_random_slope_scale()` fits the model by marginal maximum likelihood with **three-dimensional adaptive Gauss-Hermite quadrature (AGHQ)**.

The implementation uses an exact covariance reparameterization rather than a second numerical integration engine. For fitted standard deviations `tau0`, `tau1` and correlation `rho`, it defines independent latent effects `u0` and `u1` with:

```text
SD(u0) = tau0 * sqrt(1 - rho^2)
SD(u1) = tau1

delta = -rho * tau0 / tau1
b0 = u0 - delta * u1
b1 = u1
```

Thus:

```text
u0 + u1 * (w - delta) = b0 + b1 * w
```

and the transformed effects have exactly the requested `Sigma_location`. The transformation has determinant one, so no additional Jacobian term is introduced. GazeForge can therefore reuse the already validated independent 3D AGHQ integration machinery while recovering empirical-Bayes summaries in the original `b0`, `b1`, `c` coordinates.

The correlation is optimized through `rho = tanh(eta)`. Fits are rejected when the optimizer reaches the package's artificial correlation bound, when any random-effect standard deviation reaches a package-imposed numerical boundary, or when the latent covariance factor becomes boundary-censored. These are numerical certification rules, not scientific thresholds.

```python
from gazeforge.correlated_location_random_slope_scale import (
    CorrelatedLocationRandomSlopeScaleSpec,
    fit_correlated_location_random_slope_scale,
)

spec = CorrelatedLocationRandomSlopeScaleSpec(
    outcome_col="fixation_duration_ms",
    group_col="participant_id",
    random_slope_predictor="condition",
    location_predictors=("condition", "trial_index"),
    scale_predictors=("condition",),
    quadrature_points=5,
)

fit = fit_correlated_location_random_slope_scale(samples, spec=spec)
fit.fixed_effects()
fit.random_effect_correlation()
```

Predictors must already be finite numeric columns. Coding, transformations, interactions, contrasts, and the scientific definition of the random-slope predictor remain explicit analysis decisions.

Every participant must still have numerical rank 2 for `[Intercept, random_slope_predictor]`. The covariance extension does not make an unidentifiable participant slope identifiable.

## Relationship to the other location-scale families

Use `gazeforge.hierarchical_location_scale` for independent participant location and log-scale random intercepts.

Use `gazeforge.correlated_location_scale` when the scientific target is correlation between the participant location intercept and the participant log-scale intercept.

Use `gazeforge.location_random_slope_scale` when one participant location slope is required and an explicit zero intercept-slope covariance restriction is scientifically intended.

Use this family when one participant location slope is required and the participant location intercept/slope covariance should be estimated rather than fixed to zero.

Keeping these model and certificate families separate prevents a stronger covariance structure from silently changing previously frozen analyses.

## Participant effects and prediction

The fitted result stores empirical-Bayes posterior summaries for the participant location intercept, location slope, and log-scale intercept in the **original raw-predictor coordinates**.

For participants observed during fitting, `predict_correlated_location_random_slope_scale()` can add those summaries. For a genuinely unseen participant, the default remains a population-level prediction because its random effects are unknown.

```python
from gazeforge.correlated_location_random_slope_scale import (
    predict_correlated_location_random_slope_scale,
)

pred = predict_correlated_location_random_slope_scale(fit, new_rows)
```

Set `allow_new_groups=False` to fail closed on unseen participant identities.

## Diagnostics

`correlated_location_random_slope_scale_diagnostics()` returns fitted conditional location, fitted conditional scale, raw residuals, and standardized residuals. These are model diagnostics, not automatic inferential tests.

## Reproducibility certificate

The dedicated certificate binds:

- the canonical specification and random-slope predictor;
- location and log-scale fixed effects;
- the location-intercept, location-slope, and log-scale random-effect standard deviations;
- `rho_location_intercept_slope`;
- marginal log-likelihood;
- the empirical-Bayes participant-table fingerprint;
- the exact modelling-input fingerprint; and
- canonical optimizer metadata.

```python
from gazeforge.correlated_location_random_slope_scale import (
    build_correlated_location_random_slope_scale_certificate,
    freeze_correlated_location_random_slope_scale_certificate,
)

certificate = build_correlated_location_random_slope_scale_certificate(fit)
freeze_correlated_location_random_slope_scale_certificate(
    fit,
    "results/correlated-location-random-slope-scale.json",
)
```

Validation fails closed on fingerprint mutation, claim promotion, unknown certificate/model/optimizer fields, noncanonical JSON estimate types, correlation-boundary censoring, variance-boundary censoring, and inconsistent sample/group counts.

## Scientific claim boundary

This model supports:

- one grouping variable;
- one participant random location intercept;
- one participant random slope for one prespecified location predictor;
- an estimated population correlation between those two location effects;
- one participant random log-scale intercept that remains population-independent of both location effects;
- a Gaussian conditional outcome; and
- 3D AGHQ.

It does **not** provide:

- location-intercept/log-scale or location-slope/log-scale population correlations;
- an unrestricted 3 x 3 random-effects covariance matrix;
- more than one location random slope;
- log-scale random slopes;
- nested or crossed grouping structures;
- fixed-effect p-values;
- causal identification;
- device or measurement validity;
- known random effects for unseen participants; or
- automatic interpretation of motion-quality reliability weights as likelihood weights.

The fitted correlation is a model parameter describing population covariance under this Gaussian hierarchical specification. It is not a causal moderation effect, a physiological mechanism, a sensor-validity statement, or empirical/native-rate validation.

## Numerical guidance

The default is five adaptive Gauss-Hermite points per random-effect dimension; supported orders are odd integers from 3 through 9. Node count therefore grows with the cube of the requested order.

For stable estimation:

- retain enough repeated observations within each participant;
- require numerical rank 2 for every participant `[Intercept, random_slope_predictor]` design;
- avoid rank-deficient fixed-effect designs;
- use scientifically interpretable centring/scaling even though the covariance family no longer imposes a zero-covariance restriction at that chosen origin;
- inspect quadrature-order sensitivity for difficult fits;
- treat correlation or variance boundary rejection as non-certifiable numerical censoring rather than clipping the estimate; and
- interpret optimizer convergence as a numerical property, not proof that Gaussian assumptions or the chosen random-effects structure are scientifically adequate.
