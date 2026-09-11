# Hierarchical location-scale models

GazeForge provides a **Gaussian hierarchical location-scale model** for repeated eye-tracking and multimodal outcomes whose average level and within-participant variability may both change with predictors.

This is useful when the scientific question is not only whether a condition changes an outcome such as fixation duration, dwell time, pupil response, or another continuous measure, but also whether it changes the **conditional dispersion** of that outcome.

## Model

For observation `i` from participant `g`, the conditional model is:

```text
y_i ~ Normal(mu_i, sigma_i)
mu_i = X_i beta + b_g
log(sigma_i) = Z_i gamma + c_g
b_g ~ Normal(0, tau_location^2)
c_g ~ Normal(0, tau_scale^2)
```

The two participant random intercepts are independent in the current implementation. The location equation models the conditional mean. The scale equation models the logarithm of the conditional **standard deviation**, not the variance. A scale coefficient `gamma_j` has a multiplicative standard-deviation interpretation of `exp(gamma_j)` for a one-unit increase in its predictor, conditional on the rest of the model.

## Estimation

`fit_hierarchical_location_scale()` estimates both equations jointly by marginal maximum likelihood. Participant random effects are integrated with **two-dimensional adaptive Gauss-Hermite quadrature (AGHQ)**. For each participant, quadrature is centred at the participant-specific posterior mode and scaled by the local negative Hessian before the marginal likelihood is evaluated.

This is deliberately different from fitting a mean model and then regressing absolute or squared residuals in a second stage. The location and scale parameters are estimated as one likelihood model.

```python
from gazeforge.hierarchical_location_scale import (
    HierarchicalLocationScaleSpec,
    fit_hierarchical_location_scale,
)

spec = HierarchicalLocationScaleSpec(
    outcome_col="fixation_duration_ms",
    group_col="participant_id",
    location_predictors=("condition", "trial_index"),
    scale_predictors=("condition",),
    quadrature_points=5,
)

fit = fit_hierarchical_location_scale(samples, spec=spec)
fit.fixed_effects()
```

Predictors must already be numeric. Dummy coding, centring, transformations, interactions, and contrast choices remain explicit analysis decisions rather than hidden package behaviour.

## Participant effects and prediction

The fitted result includes empirical-Bayes summaries for participant location and log-scale intercepts. For participants observed during fitting, `predict_hierarchical_location_scale()` can add those posterior group effects. For a genuinely new participant, the default prediction is population-level because that participant's random effect is unknown.

```python
from gazeforge.hierarchical_location_scale import (
    predict_hierarchical_location_scale,
)

pred = predict_hierarchical_location_scale(fit, new_rows)
```

Set `allow_new_groups=False` when the analysis protocol requires prediction to fail rather than fall back to population-level prediction for unseen participant IDs.

A small prediction frame is allowed even when its local design matrix would be rank-deficient. Rank is an **estimation** requirement and is checked on the fitting data; it is not incorrectly re-imposed on a one-row prediction subset.

## Diagnostics

`hierarchical_location_scale_diagnostics()` returns fitted conditional location, fitted conditional scale, raw residuals, and standardized residuals. It does not manufacture inferential tests.

```python
from gazeforge.hierarchical_location_scale import (
    hierarchical_location_scale_diagnostics,
)

diagnostics = hierarchical_location_scale_diagnostics(fit, samples)
```

For strongly skewed positive outcomes, bounded outcomes, heavy tails, zero inflation, or discrete data, a Gaussian conditional outcome may be inappropriate. Transformations or a different distribution should be justified before interpreting the fitted model.

## Reproducibility certificate

A fitted result is bound to:

- the canonical model specification;
- location and scale fixed effects;
- both random-intercept standard deviations;
- marginal log-likelihood;
- the participant empirical-Bayes table fingerprint;
- the exact modelling-input fingerprint; and
- optimizer convergence metadata.

`build_hierarchical_location_scale_certificate()` and `freeze_hierarchical_location_scale_certificate()` fail closed if the fitted result has been mutated after fitting. Frozen certificate files are protected against overwrite by default.

```python
from gazeforge.hierarchical_location_scale import (
    build_hierarchical_location_scale_certificate,
    freeze_hierarchical_location_scale_certificate,
)

certificate = build_hierarchical_location_scale_certificate(fit)
freeze_hierarchical_location_scale_certificate(
    fit,
    "results/location_scale.json",
)
```

The certificate fixes the scientific claim boundary. Re-signing a modified certificate does not permit claim promotion.

## Scientific claim boundary

The current implementation supports a joint Gaussian location-scale model with **one grouping variable** and independent participant random intercepts in the location and log-scale equations. It does **not** currently estimate random slopes, nested or crossed grouping structures, or correlation between the two random intercepts.

It also does not provide fixed-effect p-values, establish causal effects, validate a device or measurement system, or infer random effects for unseen participants. A coefficient can describe a conditional association under the fitted model; it does not become a causal effect merely because it appears in a hierarchical model.

Motion-quality reliability weights are likewise **not automatically likelihood weights**. If motion-derived weighting is scientifically justified for a particular analysis, that requires a separately specified sensitivity analysis rather than silently passing quality weights into this likelihood.

## Numerical guidance

The default is five AGHQ points per random-effect dimension. Higher odd orders from 3 through 15 are available for sensitivity checks. Because the quadrature is two-dimensional, the per-participant node count is the square of the requested order.

For stable fitting:

- use enough repeated observations per participant;
- avoid rank-deficient predictor matrices;
- consider centring or scaling predictors with very different magnitudes;
- inspect quadrature-order sensitivity when the fitted random-effect distribution is difficult; and
- do not interpret optimizer convergence as evidence that the Gaussian model itself is scientifically adequate.

GazeForge constrains extreme intermediate log-scale values for numerical safety. That guard is computational, not an empirical threshold or substantive rule.
