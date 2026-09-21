---
description: Audit specialist-model convergence, singularity, separation, covariance/Hessian validity, diagnostic completeness, and changed-estimand replacements before interpreting gaze-model results.
search:
  boost: 1.5
---

# Model diagnostics & convergence clinic

<div class="gf-doc-kind" role="note" aria-label="Documentation type">
<strong>Post-fit audit</strong> · Bring specialist-model results back into the GazeForge workflow without treating returned coefficients as valid inference when convergence or diagnostics failed.
</div>

<nav class="gf-help" aria-label="Documentation help">
<a href="gazeforge-tour.md">Tour</a>
<a href="documentation-map.md">Task map</a>
<a href="troubleshooting.md">Troubleshooting</a>
<a href="runnable-examples.md">Examples</a>
<a href="https://github.com/stefanosbalaskas/GazeForge/issues">Ask / report</a>
</nav>

Use this clinic **after** the model has been fitted in specialist statistical software.
GazeForge does not choose or fit the estimator here. The purpose is to record whether
the fitted object is computationally admissible for interpretation, whether the
registered estimand/population stayed fixed, and what must be reported when it did not.

!!! danger "A coefficient table is not a convergence certificate"
    A model that returned coefficients can still be non-converged, singular, on a
    parameter boundary, separated, based on an invalid covariance/Hessian, or missing
    required diagnostics. Those states must block interpretation until resolved.

## Run the worked audit

```bash
python examples/17_worked_model_diagnostics_audit.py \
  --output-dir worked-model-diagnostics-audit
```

The deterministic teaching bundle writes:

```text
01_model_fit_registry.csv
02_diagnostic_status.csv
03_interpretation_gate.csv
04_sensitivity_linkage.csv
05_reporting_language.csv
06_api_route_map.csv
README.md
model_diagnostics_manifest.json
```

The worked bundle is `synthetic_demo_not_empirical_evidence`. It fits no real model,
creates no p-values or effect sizes, and does not establish construct, device, causal,
or external validity.

## What must be identified before diagnostics

Every fitted result should retain at least:

- stable model ID;
- registered estimand ID;
- analysis-population ID;
- model family and link where relevant;
- primary / sensitivity / exploratory / deviation status;
- specialist software and version;
- full analysis commit/configuration identity when using a development checkout;
- input-table fingerprint or frozen artifact identity;
- replacement-for relationship when a new model was fitted after a failure.

A model with unknown input identity is not safely interchangeable with the
preregistered result merely because the formula looks similar.

## Diagnostic states in the worked example

| State | Meaning | Interpretation |
| --- | --- | --- |
| `pass` | declared required diagnostics are complete and no blocking computational failure is present | eligible for downstream interpretation, subject to all scientific limitations |
| `blocked_non_converged` | optimizer/convergence criterion failed | do not interpret |
| `blocked_singular_or_boundary` | random-effect/covariance parameterization is singular or at a relevant boundary | do not silently treat as ordinary valid fit |
| `blocked_missing_diagnostics` | required diagnostic record is incomplete | fail closed; do not default to pass |
| `blocked_separation_or_covariance` | separation/perfect prediction or invalid covariance/Hessian state | block inferential interpretation |

These are **workflow gates**, not scientific truth labels.

## GLM / GLMM checks

Depending on the model family and backend, review:

- optimizer convergence;
- warnings/messages;
- separation or quasi-separation for binary/count models where applicable;
- singular random-effects structure;
- variance components on package/numerical boundaries;
- covariance/Hessian validity;
- overdispersion or zero-inflation diagnostics where relevant;
- residual or influence diagnostics appropriate to the chosen model.

Do not switch optimizers, links, random-effects structures, or model families and then
silently call the replacement the original confirmatory model.

## Survival / time-to-event checks

For censored gaze latency models, retain:

- event indicator and censoring definition;
- event count and censoring count;
- time origin and censor time;
- convergence/optimizer status;
- model-specific assumptions such as proportional hazards when the chosen estimator
  requires them;
- influential observations or numerical pathologies where relevant.

A no-fixation trial is not a zero-latency event. Use the
[Denominator, exposure & censoring clinic](denominator-exposure-censoring.md) before
model fitting.

## SEM checks

For SEM or latent-variable workflows, review at minimum:

- convergence;
- identification;
- inadmissible solutions such as negative residual variances where applicable;
- covariance/parameter boundary problems;
- fit indices in the context of the prespecified model rather than as automatic
  construct-validity proof;
- changes to the measurement/structural model introduced after seeing results.

A converged SEM does not validate the underlying gaze construct by itself.

## Bayesian checks

For Bayesian specialist workflows, review diagnostics appropriate to the backend,
including where relevant:

- chain convergence;
- R-hat;
- effective sample size;
- divergences;
- tree-depth/energy warnings;
- prior/posterior pathologies;
- posterior predictive checks appropriate to the model.

Do not replace a failed Bayesian fit with a different prior/model and present the new
result as though the original preregistered specification had succeeded.

## Changed-estimand replacement is not a repair

The worked example includes a diagnostically clean complete-case candidate whose
estimand/population differs from the registered primary target. It receives the gate:

`exploratory_changed_estimand`

That result can be informative, but it cannot silently replace the primary analysis.
Record it in the [Sensitivity & robustness clinic](sensitivity-robustness-clinic.md)
or the preregistration deviation ledger.

## Diagnostic completeness must fail closed

If a required diagnostic is absent, unknown, or unavailable:

- record that fact explicitly;
- do not assume the check passed;
- do not infer validity from the absence of a warning;
- retain the model/software identity so the missing check can be reproduced later.

“Software did not warn” is not equivalent to “all required diagnostics passed.”

## Reporting examples

### Methods

> Specialist statistical models were fitted under the prespecified analysis plan. Model, estimand, analysis-population, software, convergence, and required diagnostic identities were frozen before interpretation. Fits with non-convergence, singular/boundary states, separation/invalid covariance, or incomplete diagnostics were not treated as valid inferential results.

### Failed convergence

> The prespecified sensitivity model did not converge under the declared fitting procedure. The attempted model and diagnostic state are retained in the audit record, but its coefficients are not interpreted.

### Singular/boundary fit

> The fitted model exhibited a singular/boundary diagnostic state. The result is reported as a failed/review-required fit rather than as confirmatory evidence.

### Changed-estimand replacement

> A diagnostically admissible complete-case model changed the target population/estimand relative to the registered primary analysis and was therefore reported as an exploratory deviation rather than as a replacement primary result.

### Limitations

> Diagnostic admissibility concerns the fitted statistical object only. It does not establish measurement validity, construct validity, causal identification, device validity, or generalisability beyond the registered analysis design.

## Stop conditions

Do not interpret a model as a valid inferential result when:

- convergence failed;
- singular/boundary status is unresolved;
- required covariance/Hessian validity failed;
- separation/perfect prediction invalidates the intended fit;
- required diagnostics are missing;
- model/input/estimand identity cannot be reconstructed;
- the only “successful” replacement changes the estimand/population and has not been
  recorded as a sensitivity/deviation;
- the software returned coefficients but the diagnostic state is otherwise unknown.

## Archive record

Retain:

1. model registry;
2. diagnostic status table;
3. interpretation gate;
4. replacement/sensitivity linkage;
5. specialist software/version;
6. model formula/configuration outside this teaching example;
7. convergence/warning/diagnostic output from the specialist package;
8. analysis-table fingerprint and estimand/population identity;
9. reporting language for failed/review-required fits.

## Continue through the workflow

- [Analysis handoff](analysis-handoff.md) — construct model-ready tables without choosing the estimator.
- [Grouping, repeated measures & pseudoreplication clinic](grouping-repeated-measures.md) — preserve the design identities that a fitted model is supposed to represent; a small variance component does not erase the design.
- [Denominator, exposure & censoring clinic](denominator-exposure-censoring.md) — freeze exposure/missingness/censoring semantics.
- [Uncertainty, multiplicity & inferential reporting clinic](inferential-reporting-audit.md) — verify effect scale, uncertainty identity, multiplicity families, and confirmatory/exploratory status after the diagnostic gate passes.
- [Sensitivity & robustness clinic](sensitivity-robustness-clinic.md) — register alternative/replacement fits and changed-estimand deviations.
- [Reporting & interpretation clinic](reporting-clinic.md) — report only diagnostically admissible results with limitations.
- [Publication readiness](publication-readiness.md) — verify convergence/diagnostic status before manuscript freeze.
- [Reviewer & replication handoff](reviewer-replication-handoff.md) — expose model/software/diagnostic identity for external audit.

## Scientific boundary

This clinic provides a fail-closed **computational interpretation gate**.
Passing the gate does not make a model scientifically correct, causal, construct-valid,
device-valid, or externally valid. GazeForge does not silently select a replacement
estimator or promote a changed-estimand model to the primary analysis.
