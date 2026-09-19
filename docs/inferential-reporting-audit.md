---
description: Audit effect scale, uncertainty identity, multiplicity families, raw/adjusted inferential fields, diagnostic eligibility, and confirmatory versus exploratory status before reporting specialist-model results.
search:
  boost: 1.5
---

# Uncertainty, multiplicity & inferential reporting clinic

<div class="gf-doc-kind" role="note" aria-label="Documentation type">
<strong>Post-fit reporting audit</strong> · Verify that diagnostically admissible specialist-model results keep their estimand, scale, interval, multiplicity, and confirmatory status intact before manuscript interpretation.
</div>

<nav class="gf-help" aria-label="Documentation help">
<a href="gazeforge-tour.md">Tour</a>
<a href="documentation-map.md">Task map</a>
<a href="troubleshooting.md">Troubleshooting</a>
<a href="runnable-examples.md">Examples</a>
<a href="https://github.com/stefanosbalaskas/GazeForge/issues">Ask / report</a>
</nav>

Use this clinic after the [Model diagnostics & convergence clinic](model-diagnostics-convergence.md)
has established that a fitted result is computationally eligible for interpretation.
This layer does **not** fit the model or choose a multiplicity procedure. It checks
whether the reported inferential result still matches the registered scientific target.

!!! warning "An interpretable fit can still be reported incorrectly"
    A converged model can still be misreported if the effect scale is unclear, the
    interval method or level is missing, raw and adjusted p-values are conflated,
    the confirmatory family is incomplete, or an exploratory result is described as
    confirmatory.

## Run the worked audit

```bash
python examples/19_worked_inferential_reporting_audit.py \
  --output-dir worked-inferential-reporting-audit
```

The deterministic teaching bundle writes:

```text
01_result_registry.csv
02_uncertainty_audit.csv
03_multiplicity_family.csv
04_interpretation_gate.csv
05_reporting_language.csv
06_api_route_map.csv
README.md
inferential_reporting_manifest.json
```

The bundle is `synthetic_demo_not_empirical_evidence`. Every estimate, interval,
and p-value in the example is a teaching value rather than an empirical study result.

## What a reportable result needs

At minimum, retain:

- stable result/model ID;
- registered estimand ID;
- analysis-population ID;
- primary / secondary / exploratory role;
- diagnostic-gate status;
- reported effect scale;
- unit;
- point estimate;
- uncertainty type, level, method, and bounds;
- confirmatory-family identity when applicable;
- multiplicity procedure identity when applicable;
- raw and adjusted p-values as separate fields when p-values belong to the
  prespecified inferential workflow;
- specialist software/version and analysis identity in the study archive.

Do not let a manuscript table become the only surviving record of these identities.

## Effect scale and units

A number without its scale is not interpretable.

| Quantity | Possible reporting scale | Unit |
| --- | --- | --- |
| dwell contrast | arithmetic difference | ms |
| fixation-rate contrast | arithmetic difference | fixations/s |
| count model | log rate or exponentiated rate ratio | model-dependent |
| binary model | log-odds or odds ratio | model-dependent |
| survival model | log hazard or hazard ratio | model-dependent |
| standardized effect | standardized scale | SD units or declared standardization |

If a model is fitted on a transformed/link scale and results are back-transformed,
record both identities. Do not silently compare a ratio to a registered difference
estimand, or label a dimensionless ratio as milliseconds.

The worked audit deliberately blocks one result with a scale/unit mismatch.

## Uncertainty identity

A point estimate should not be detached from how its uncertainty was obtained.

Record, where applicable:

- standard error;
- confidence interval or credible interval;
- interval level, such as 95%;
- interval method, such as Wald, profile likelihood, bootstrap, or posterior
  quantiles;
- degrees-of-freedom / small-sample method where material;
- bootstrap or simulation settings when those define the reported uncertainty.

Do not write “95% CI” when the interval level or construction method cannot be
recovered from the specialist analysis record.

### Frequentist interval

A confidence interval should be named as a confidence interval. Do not reinterpret it
as a posterior probability statement.

### Bayesian interval

A Bayesian credible interval should retain:

- posterior quantity;
- credible level;
- interval convention when relevant;
- prior/model identity;
- chain/diagnostic eligibility from the specialist workflow.

Do not convert a credible interval into a frequentist confidence interval in prose.

## Multiplicity family

Multiplicity begins with the **family definition**, not the correction algorithm.

Before interpreting confirmatory p-values, answer:

1. Which outcomes/contrasts belong to the same confirmatory family?
2. Was that family declared before outcome inspection?
3. Which multiplicity procedure was prespecified or justified?
4. Are all members accounted for?
5. Are raw and adjusted values retained separately?
6. Did any analysis leave the confirmatory family because it became exploratory or
   changed estimand?

The [Outcome & estimand preregistration clinic](estimand-preregistration.md) should
freeze the family before confirmatory fitting when multiplicity is material.

!!! note "No universal correction"
    GazeForge does not choose Holm, Bonferroni, false-discovery-rate control, gatekeeping,
    or another procedure automatically. The appropriate strategy depends on the
    study's inferential goals and prespecified analysis plan.

## Raw and adjusted p-values are different fields

When p-values are part of the study:

- retain the raw value;
- retain the adjusted value separately;
- retain the adjustment method/family;
- do not overwrite the raw value with the adjusted value;
- do not label an unadjusted value as adjusted;
- do not infer substantive truth from whether either value crosses a threshold.

The worked audit includes separate `p_value_raw` and `p_value_adjusted` columns and
a deliberately incomplete confirmatory family that fails closed.

## Exploratory is not failed confirmatory

An exploratory result can be scientifically useful while remaining exploratory.

The worked example gives the exploratory row:

`eligible_exploratory`

That status permits exploratory reporting but **not confirmatory language**. It does
not mean “weak,” “invalid,” or “unimportant”; it records the inferential role.

Do not promote an exploratory result into a confirmatory family after inspecting its
estimate or p-value.

## Interpretation gates

The worked example uses these workflow states:

| Gate | Meaning |
| --- | --- |
| `eligible_confirmatory` | diagnostic, scale/unit, uncertainty, and confirmatory-family records are complete |
| `eligible_exploratory` | diagnostically admissible exploratory result with complete scale/uncertainty identity |
| `blocked_missing_uncertainty_identity` | interval level/method or required uncertainty identity is incomplete |
| `blocked_multiplicity_incomplete` | confirmatory family/raw-adjusted/method record is incomplete |
| `blocked_scale_or_unit_mismatch` | reported scale/unit does not match the registered target |
| `blocked_diagnostic_failure` | the upstream model-diagnostics gate failed |

These are workflow gates, not scientific truth labels.

## Sensitivity analyses

For a sensitivity result, report changes in:

- estimate;
- uncertainty;
- denominator/population;
- effect scale if it changed;
- multiplicity role;
- diagnostic status;
- estimand identity.

A stable point estimate does not establish validity. A sensitivity result that changes
the estimand or population should remain a deviation/exploratory result rather than
being silently folded into the primary confirmatory family.

Use the [Sensitivity & robustness clinic](sensitivity-robustness-clinic.md) for the
complete registered/executed sensitivity set. When repeated observations or recurring stimuli are present, the [Grouping, repeated measures & pseudoreplication clinic](grouping-repeated-measures.md) should have preserved the inferential/generalisation identities underlying the reported uncertainty.

## Reporting examples

### Methods

> Primary and secondary specialist-model results were reported on their registered effect scales with explicit units and interval construction. Confirmatory multiplicity families and procedures were declared in the analysis plan; raw and adjusted p-values, where used, were retained as separate fields. Exploratory results remained outside the confirmatory family.

### Results

> For each reported contrast, the point estimate is accompanied by the declared uncertainty interval, interval level/method, analysis population, and inferential role. Confirmatory p-values are identified as raw or multiplicity-adjusted rather than presented interchangeably.

### Table footnote

> Estimates are shown on the stated reporting scale. Intervals use the method and level specified in the analysis plan. Adjusted p-values are reported only for members of the declared confirmatory family; exploratory analyses are labeled separately.

### Blocked result

> This fitted result is not interpreted because its uncertainty identity or confirmatory multiplicity record is incomplete. The attempted result remains in the audit ledger rather than being omitted.

### Limitations

> Complete inferential reporting improves traceability but does not establish construct validity, measurement validity, causal identification, device validity, or generalisability. Threshold-based p-value labels are not treated as scientific truth classifications.

## Figures

When a figure displays inferential results:

- label the effect scale and unit on the axis;
- state whether intervals are confidence or credible intervals;
- state the interval level;
- state the interval method in the caption or linked Methods;
- distinguish confirmatory and exploratory results visually/textually without implying
  a quality ranking;
- identify multiplicity adjustment in the caption/table note when adjusted p-values are
  shown;
- keep denominator/population identity accessible.

Do not draw a zero/reference line without making the effect scale clear.

## Archive record

Retain:

1. result registry;
2. uncertainty audit;
3. multiplicity-family registry;
4. interpretation gate;
5. reporting-language examples/templates;
6. specialist model/software identity;
7. input/model/result fingerprints where available;
8. preregistration/deviation identity;
9. sensitivity linkage;
10. manuscript table/figure provenance.

## Continue through the workflow

- [Outcome & estimand preregistration](estimand-preregistration.md) — freeze outcome, estimand, contrast, and confirmatory-family intent.
- [Model diagnostics & convergence clinic](model-diagnostics-convergence.md) — block computationally inadmissible fitted results.
- [Sensitivity & robustness clinic](sensitivity-robustness-clinic.md) — retain the complete registered/executed variant set.
- [Reporting & interpretation clinic](reporting-clinic.md) — translate only audit-eligible results into manuscript language.
- [Publication readiness](publication-readiness.md) — verify result scale, uncertainty, multiplicity, diagnostics, and provenance.
- [Reviewer & replication handoff](reviewer-replication-handoff.md) — expose result identities and audit records for external inspection.

## Scientific boundary

This clinic audits **inferential-reporting identity**, not scientific truth. A result
that passes the gate is reportable under its declared analysis contract; it is not
thereby proven causal, construct-valid, device-valid, externally valid, or important.
GazeForge does not choose the inferential estimator, multiplicity procedure, or
substantive conclusion.
