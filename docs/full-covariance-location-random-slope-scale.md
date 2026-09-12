# Full-covariance location random-slope scale model

GazeForge provides a separate **Gaussian hierarchical location-scale family with a full 3 × 3 participant random-effects covariance matrix**. It extends the correlated location random-slope family without adding another latent dimension: the participant location intercept, participant location slope, and participant log-scale intercept may all covary.

## Model

For observation `i` from participant `g`:

```text
y_i ~ Normal(mu_i, sigma_i)
mu_i = X_i beta + b0_g + b1_g * w_i
log(sigma_i) = Z_i gamma + c_g

(b0_g, b1_g, c_g) ~ Normal(0, Sigma)
```

`Sigma` is an unrestricted positive-definite 3 × 3 covariance matrix. The model therefore estimates three random-effect standard deviations and three marginal correlations:

- location intercept ↔ location slope;
- location intercept ↔ log-scale intercept; and
- location slope ↔ log-scale intercept.

`w` is the single `random_slope_predictor`, and it must also appear in `location_predictors`. The participant-level `[Intercept, random_slope_predictor]` design must have numerical rank 2 for every participant.

## Positive-definite correlation parameterization

The implementation does not optimize three unconstrained pairwise correlations directly. That would permit an invalid, non-positive-definite correlation matrix.

Instead it uses a three-coordinate vine parameterization:

```text
rho01 = tanh(eta01)
rho02 = tanh(eta02)
partial12_given_0 = tanh(eta12)

rho12 = rho01 * rho02
        + sqrt(1 - rho01^2)
        * sqrt(1 - rho02^2)
        * partial12_given_0
```

Here `0`, `1`, and `2` denote the location intercept, location slope, and log-scale intercept. The resulting matrix is positive definite for interior coordinates. The certificate stores the two first-order correlations, the derived slope/log-scale marginal correlation, and the partial-correlation coordinate so the parameterization can be reconstructed and checked exactly.

All three optimizer correlation coordinates are bounded only for numerical certification. A fit that reaches an artificial coordinate bound is rejected rather than clipped and reported as if it were an interior estimate.

## Estimation

`fit_full_covariance_location_random_slope_scale()` fits the model by marginal maximum likelihood with **three-dimensional adaptive Gauss-Hermite quadrature (AGHQ)**.

The latent dimension remains three because the model still has exactly three participant effects `(b0, b1, c)`. Full covariance changes their joint Gaussian prior; it does not add a fourth random effect.

The log prior is evaluated with the full covariance precision matrix and log determinant. Posterior modes, adaptive Hessians, quadrature grids, and empirical-Bayes participant summaries are all computed in the original random-effect coordinates.

```python
from gazeforge.full_covariance_location_random_slope_scale import (
    FullCovarianceLocationRandomSlopeScaleSpec,
    fit_full_covariance_location_random_slope_scale,
)

spec = FullCovarianceLocationRandomSlopeScaleSpec(
    outcome_col="fixation_duration_ms",
    group_col="participant_id",
    random_slope_predictor="condition",
    location_predictors=("condition", "trial_index"),
    scale_predictors=("condition",),
    quadrature_points=5,
)

fit = fit_full_covariance_location_random_slope_scale(samples, spec=spec)
fit.fixed_effects()
fit.random_effect_correlation_matrix()
fit.random_effect_covariance_matrix()
```

Predictors must already be finite numeric columns. Coding, centring, transformations, interactions, and the scientific meaning of the random-slope predictor remain explicit analysis decisions.

## Predictor zero-point semantics

If the random-slope predictor is re-expressed as:

```text
w_new = w_old - k
```

the equivalent participant effects are:

```text
b0_new = b0_old + k * b1_old
b1_new = b1_old
c_new  = c_old
```

Therefore the covariance transforms as:

```text
Sigma_new = T Sigma_old T'

T = [1  k  0]
    [0  1  0]
    [0  0  1]
```

This changes not only intercept-slope covariance but, when slope and scale covary, also intercept-scale covariance. The full 3 × 3 family is closed under this transformation whenever the transformed covariance remains inside the numerical support region.

`transform_full_covariance_for_predictor_shift()` exposes this exact covariance transformation. The test suite also verifies likelihood-level zero-point invariance, including corresponding transformations of fixed location and scale intercepts when the shifted predictor is present in both equations.

## Relationship to the other location-scale families

Use `gazeforge.hierarchical_location_scale` for independent participant location and log-scale random intercepts.

Use `gazeforge.correlated_location_scale` for a correlated location/log-scale random-intercept pair without a participant location slope.

Use `gazeforge.location_random_slope_scale` when one participant location slope is required and all three participant effects are intentionally population-independent.

Use `gazeforge.correlated_location_random_slope_scale` when location intercept and location slope may covary but the log-scale random intercept is intentionally independent of both.

Use this full-covariance family when all three pairwise population associations are scientifically allowed and estimable.

These remain separate model and certificate families so a stronger covariance assumption cannot silently alter a frozen analysis.

## Participant effects and prediction

The fitted result stores empirical-Bayes posterior summaries for participant location intercept, location slope, and log-scale intercept, including their posterior covariance summaries.

For participants observed during fitting, `predict_full_covariance_location_random_slope_scale()` can add those participant summaries. For unseen participants, the default is population-level prediction because their random effects are unknown.

```python
from gazeforge.full_covariance_location_random_slope_scale import (
    predict_full_covariance_location_random_slope_scale,
)

pred = predict_full_covariance_location_random_slope_scale(fit, new_rows)
```

Set `allow_new_groups=False` to fail closed on unseen participant identities.

## Diagnostics

`full_covariance_location_random_slope_scale_diagnostics()` returns fitted conditional location, fitted conditional scale, raw residuals, and standardized residuals. These are descriptive model diagnostics, not automatic inferential tests.

## Reproducibility certificate

The dedicated certificate binds:

- the canonical specification and random-slope predictor;
- location and log-scale fixed effects;
- all three participant random-effect standard deviations;
- all three marginal random-effect correlations;
- the slope/log-scale partial correlation conditional on the location intercept;
- marginal log-likelihood;
- the empirical-Bayes participant-table fingerprint;
- the exact modelling-input fingerprint; and
- canonical optimizer metadata.

```python
from gazeforge.full_covariance_location_random_slope_scale import (
    build_full_covariance_location_random_slope_scale_certificate,
    freeze_full_covariance_location_random_slope_scale_certificate,
)

certificate = build_full_covariance_location_random_slope_scale_certificate(fit)
freeze_full_covariance_location_random_slope_scale_certificate(
    fit,
    "results/full-covariance-location-random-slope-scale.json",
)
```

Validation fails closed on fingerprint mutation, unknown fields, noncanonical JSON estimate types, inconsistent marginal/partial correlation coordinates, non-positive-definite covariance, correlation-boundary censoring, variance-boundary censoring, claim promotion, and inconsistent sample/group counts.

## Scientific claim boundary

This model supports:

- one grouping variable;
- one participant random location intercept;
- one participant random slope for one prespecified location predictor;
- one participant random log-scale intercept;
- an unrestricted positive-definite 3 × 3 covariance among those three effects;
- a Gaussian conditional outcome; and
- 3D AGHQ.

It does **not** provide:

- more than one location random slope;
- log-scale random slopes;
- nested or crossed grouping structures;
- fixed-effect p-values;
- causal identification;
- device or measurement validity;
- known random effects for unseen participants;
- automatic interpretation of motion-quality reliability weights as likelihood weights;
- residual-calibration support merely because the base model fits; or
- hierarchical-bootstrap support merely because the base model fits.

The last two exclusions are deliberate. The existing residual-calibration and hierarchical-bootstrap adapters were separately certified for four earlier Gaussian location-scale families. This new model family must be added to those adapters only through later parity tranches with their own exact-input lineage, simulation, certificate, and cross-platform qualification.

The fitted covariance describes population association under this Gaussian hierarchical specification. It is not a causal moderation mechanism, physiological mechanism, sensor-validity statement, or empirical/native-rate validation.

## Numerical guidance

The default is five adaptive Gauss-Hermite points per random-effect dimension; supported orders remain odd integers from 3 through 9. Node count grows with the cube of the requested order.

For stable estimation:

- retain enough repeated observations within each participant;
- require numerical rank 2 for every participant `[Intercept, random_slope_predictor]` design;
- avoid rank-deficient fixed-effect designs;
- use scientifically interpretable centring/scaling even though the full covariance family is closed under predictor zero-point shifts;
- inspect quadrature-order sensitivity for difficult fits;
- treat covariance/correlation/variance boundary rejection as non-certifiable numerical censoring rather than clipping estimates; and
- interpret optimizer convergence as a numerical property, not proof that Gaussian assumptions or the chosen covariance structure are scientifically adequate.
