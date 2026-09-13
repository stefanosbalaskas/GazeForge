# Bootstrap Monte Carlo precision

A hierarchical parametric bootstrap can be scientifically well-defined and still be **numerically imprecise because the finite number of bootstrap replicates is too small for the reported summary**. GazeForge therefore treats Monte Carlo precision as a separate diagnostic problem from the bootstrap's inferential target.

The bootstrap itself asks what the fitted model would produce across repeated model-generated datasets. This diagnostic asks a narrower computational question:

> Given the bootstrap replicates that were actually computed, how much Monte Carlo uncertainty remains in the reported bootstrap mean, bootstrap standard deviation, and percentile endpoints?

The diagnostic does not refit the model and does not change the certified bootstrap distribution. It reuses the exact certified replicate ledger and is lineage-bound to the complete source bootstrap certificate.

## Why this is separate from the bootstrap

`bootstrap_location_scale_hierarchy()` already records a deterministic replicate ledger and reports, for each parameter:

- the bootstrap mean;
- the bootstrap standard error (the sample standard deviation of replicate estimates);
- bootstrap bias; and
- lower and upper percentile endpoints.

Those quantities are themselves estimated from a finite Monte Carlo sample of size `B = n_simulations`. A small `B` can make a tail percentile especially coarse even when every bootstrap refit is valid.

There is no universal simulation count that makes every bootstrap adequate. Required precision depends on the target statistic, the distribution of replicate estimates, the tail probability, and the scientific use of the result. For that reason GazeForge does **not** label a bootstrap automatically as stable/unstable and does not encode an arbitrary minimum adequate `B`.

## Mean Monte Carlo standard error

For bootstrap replicate estimates `theta_1*, ..., theta_B*`, let

```text
s* = sample standard deviation(theta_1*, ..., theta_B*)
```

The Monte Carlo standard error of the replicate mean is reported as

```text
MCSE(mean*) = s* / sqrt(B)
```

This measures finite-simulation uncertainty in the bootstrap mean. It is not the scientific standard error of the original estimator.

## Monte Carlo error of the bootstrap standard deviation

The reported bootstrap standard error is itself a statistic of the `B` bootstrap replicates. GazeForge estimates its Monte Carlo uncertainty with a leave-one-bootstrap-replicate-out jackknife.

For each bootstrap replicate `b`, compute the standard deviation after deleting replicate `b`, producing `s*_{(-b)}`. If their mean is `s*_{(.)}`, the diagnostic reports

```text
MCSE_jackknife(s*) =
    sqrt((B - 1) / B * sum_b (s*_{(-b)} - s*_{(.)})^2)
```

At least three bootstrap simulations are required so every leave-one-out sample still contains at least two values. This is a mathematical requirement of this diagnostic, not a claim that three simulations are scientifically adequate.

## Percentile-endpoint Monte Carlo bands

Tail percentiles require a different treatment. A density-based asymptotic standard error can become unstable exactly where finite-bootstrap diagnostics are most useful, so GazeForge uses a distribution-free **binomial order-statistic construction**.

For a target population quantile with probability `p`, the number of bootstrap draws below the true quantile follows

```text
K ~ Binomial(B, p)
```

under the usual continuous-distribution order-statistic argument. For a requested Monte Carlo confidence level, GazeForge obtains equal-tail binomial count limits and maps them to order-statistic ranks in the already-computed bootstrap values.

The result reports, separately for the lower and upper percentile endpoint:

- the target percentile probability;
- the lower and upper order-statistic ranks of the Monte Carlo band;
- the corresponding numerical replicate values where finite; and
- the achieved discrete binomial coverage.

Because the binomial construction is discrete, achieved coverage can be greater than the requested confidence level.

### Explicitly unbounded finite-sample ranks

For small `B` and extreme tail probabilities, a requested Monte Carlo band can extend beyond the smallest or largest observed bootstrap replicate. GazeForge does not silently clip such a band to the sample minimum or maximum.

Instead:

- rank `0` means the lower Monte Carlo band extends below the smallest observed replicate, and its numerical lower bound is `null`;
- rank `B + 1` means the upper Monte Carlo band extends above the largest observed replicate, and its numerical upper bound is `null`.

This makes inadequate tail resolution visible rather than disguising it as a finite interval.

## Five-family compatibility

The diagnostic operates on `LocationScaleHierarchicalBootstrapResult` and therefore inherits the exact parameter inventory of the already-certified source bootstrap. It is agnostic to which of the five supported Gaussian location-scale families produced that bootstrap:

1. independent location/log-scale random intercepts;
2. correlated location/log-scale random intercepts;
3. independent location random intercept + location random slope + log-scale random intercept;
4. correlated location-intercept/location-slope block + independent log-scale random intercept; and
5. full 3×3 covariance across location intercept, location slope, and log-scale intercept.

No additional model fitting occurs during the Monte Carlo diagnostic.

## Reproducibility and lineage

Before computing diagnostics, GazeForge builds and validates the complete hierarchical-bootstrap certificate. The Monte Carlo result is then bound to:

- the source bootstrap fingerprint;
- the source bootstrap certificate fingerprint;
- the source model family;
- the bootstrap interval level;
- the exact simulation count;
- the exact ordered parameter inventory; and
- a deterministic fingerprint of every diagnostic row.

The Monte Carlo certificate embeds the complete source bootstrap certificate. Validation revalidates that nested certificate and recomputes every diagnostic from its exact replicate ledger. Re-signing a modified diagnostic row, source claim boundary, or assessment identity does not bypass validation.

## Scientific claim boundary

The diagnostic certificate states that Monte Carlo precision has been quantified for the existing bootstrap replicates. It does **not** claim that:

- any additional model refits were performed;
- a universal stability threshold was applied;
- any minimum bootstrap simulation count is scientifically adequate;
- percentile intervals have guaranteed frequentist coverage;
- the fitted model is robust to misspecification;
- global model adequacy or distributional correctness is established;
- fixed-effect p-values are provided;
- causal effects are identified; or
- device, sensor, or measurement validity is established.

These are intentionally separate questions.

## Python API

```python
from gazeforge.location_scale_bootstrap_monte_carlo import (
    LocationScaleBootstrapMonteCarloSpec,
    assess_location_scale_bootstrap_monte_carlo,
    build_location_scale_bootstrap_monte_carlo_certificate,
)

precision = assess_location_scale_bootstrap_monte_carlo(
    bootstrap_result,
    spec=LocationScaleBootstrapMonteCarloSpec(
        confidence_level=0.95,
    ),
)

precision.parameters()
certificate = build_location_scale_bootstrap_monte_carlo_certificate(
    precision
)
```

Use `precision.parameters()` to inspect the per-parameter Monte Carlo diagnostics. A wide or unbounded percentile-endpoint Monte Carlo band is evidence that the finite bootstrap sample does not localize that endpoint tightly; it is not by itself evidence for or against the scientific model.

## Relationship to simulation budget decisions

The diagnostic is intended to support a transparent simulation-budget decision rather than replace one. A defensible workflow is to inspect the Monte Carlo uncertainty relative to the scientific precision needed for the analysis and, when necessary, rerun the bootstrap with a larger predeclared simulation budget.

The package deliberately does not convert that judgement into a hidden threshold. In particular, the fact that the schema permits very small simulation counts for inexpensive software-path testing must never be interpreted as a recommendation for scientific analysis.
