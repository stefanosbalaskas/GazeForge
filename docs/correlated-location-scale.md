# Correlated location-scale random effects

GazeForge provides a correlated extension of the Gaussian hierarchical location-scale model for repeated eye-tracking and multimodal outcomes.

Use this model when the scientific question includes whether participants with systematically higher conditional outcome levels also tend to show systematically higher or lower **within-participant variability**.

## Model

For observation `i` from participant `g`:

```text
y_i ~ Normal(mu_i, sigma_i)
mu_i = X_i beta + b_g
log(sigma_i) = Z_i gamma + c_g

[b_g, c_g]' ~ Normal(0, Sigma)

Sigma = [[tau_location^2, rho * tau_location * tau_scale],
         [rho * tau_location * tau_scale, tau_scale^2]]
```

`rho` is the participant-level correlation between the random location intercept and the random log-scale intercept. A positive fitted `rho` means that participants with higher conditional location effects tend, under the fitted model, to have higher conditional residual standard deviations. A negative value indicates the opposite association.

This association is a **random-effect distribution parameter**. It is not the correlation between raw participant means and raw participant standard deviations, and it is not a causal effect.

## Estimation

`fit_correlated_location_scale()` estimates the location equation, log-scale equation, both random-effect standard deviations, and `rho` jointly by marginal maximum likelihood.

Participant effects are integrated with two-dimensional adaptive Gauss-Hermite quadrature. Correlation is optimized on an unconstrained scale and mapped through `tanh`, which keeps the fitted value strictly inside `(-1, 1)`. An additional near-singularity guard prevents numerical evaluation arbitrarily close to `|rho| = 1`; this is a computational guard, not a scientific threshold.

```python
from gazeforge.correlated_location_scale import (
    CorrelatedLocationScaleSpec,
    fit_correlated_location_scale,
)

spec = CorrelatedLocationScaleSpec(
    outcome_col="fixation_duration_ms",
    group_col="participant_id",
    location_predictors=("condition", "trial_index"),
    scale_predictors=("condition",),
    quadrature_points=5,
)

fit = fit_correlated_location_scale(samples, spec=spec)
fit.fixed_effects()
fit.random_effect_correlation()
```

Predictors must already be numeric. Dummy coding, interactions, transformations, centring, and scaling remain explicit analysis-protocol decisions.

## Relationship to the independent model

The original `gazeforge.hierarchical_location_scale` model assumes independent participant location and log-scale random intercepts. The correlated model is a separate model family and certificate schema so that adding a stronger population-level association assumption does not silently change already frozen independent-model results.

At `rho = 0`, the bivariate Gaussian random-effect density reduces to the independent random-intercept density. GazeForge tests this special case directly and also checks the nonzero-correlation adaptive marginal likelihood against a high-order fixed Gaussian-Hermite reference.

The correlated model should therefore be selected because the association is scientifically relevant, not simply because an extra parameter can be estimated.

## Participant effects and prediction

The fitted result contains empirical-Bayes summaries for the two participant effects and their posterior covariance. The population parameter `rho_location_scale` remains distinct from those participant-specific posterior summaries.

For participants observed during fitting, `predict_correlated_location_scale()` can use the empirical-Bayes location and log-scale effects. For unseen participants, the default prediction is population-level because their participant effects are unknown.

```python
from gazeforge.correlated_location_scale import predict_correlated_location_scale

pred = predict_correlated_location_scale(fit, new_rows)
```

Set `allow_new_groups=False` when the analysis protocol should fail on unseen participant identities instead of using the population prediction.

## Diagnostics

`correlated_location_scale_diagnostics()` returns fitted conditional location, fitted conditional scale, raw residuals, and standardized residuals. These are diagnostics, not inferential tests.

```python
from gazeforge.correlated_location_scale import correlated_location_scale_diagnostics

diagnostics = correlated_location_scale_diagnostics(fit, samples)
```

The same Gaussian-outcome cautions apply as in the independent model. Strong skew, bounded outcomes, heavy tails, zero inflation, or discrete outcomes can make this conditional distribution inappropriate.

## Reproducibility certificate

The correlated certificate binds:

- the canonical model specification;
- location and log-scale fixed effects;
- both random-effect standard deviations;
- the fitted location/log-scale correlation;
- marginal log-likelihood;
- the empirical-Bayes participant table fingerprint;
- the exact modelling-input fingerprint; and
- optimizer convergence metadata.

```python
from gazeforge.correlated_location_scale import (
    build_correlated_location_scale_certificate,
    freeze_correlated_location_scale_certificate,
)

certificate = build_correlated_location_scale_certificate(fit)
freeze_correlated_location_scale_certificate(
    fit,
    "results/correlated-location-scale.json",
)
```

Result mutation and certificate tampering fail closed. Recomputing the outer certificate fingerprint after changing `rho` does not bypass the bound model fingerprint or the scientific claim boundary.

## Scientific claim boundary

This model supports **one grouping variable**, a random intercept in the location equation, a random intercept in the log-scale equation, and their population-level correlation.

It does **not** currently provide:

- random slopes;
- nested or crossed grouping structures;
- fixed-effect p-values;
- causal identification;
- device or measurement validity;
- known random effects for unseen participants; or
- automatic interpretation of motion-quality reliability weights as likelihood weights.

A nonzero fitted `rho` is a model-based association in the participant random-effect distribution. It should not be described as evidence that one latent participant characteristic causes the other.

## Numerical guidance

The default is five adaptive Gauss-Hermite points per random-effect dimension. Supported orders are odd integers from 3 through 15. The node count per participant grows with the square of the requested order.

For stable estimation:

- retain enough repeated observations per participant;
- avoid rank-deficient design matrices;
- centre or scale predictors when magnitudes differ substantially;
- inspect quadrature-order sensitivity for difficult fits;
- inspect whether `rho` is approaching its numerical boundary; and
- treat convergence as a numerical result, not proof that the Gaussian or random-effect assumptions are scientifically adequate.
