---
description: Post-analysis sensitivity and robustness clinic for preserving primary estimands, executing prespecified variants, retaining failed/non-evaluable conditions, and reporting complete sensitivity evidence without cherry-picking.
search:
  boost: 1.5
---

# Sensitivity & robustness clinic

<div class="gf-doc-kind" role="note" aria-label="Documentation type">
<strong>Method clinic</strong> · Connect preregistered sensitivity plans to executed variants, denominator changes, interpretation limits, and manuscript wording without silently changing the primary estimand.
</div>

<nav class="gf-help" aria-label="Documentation help">
<a href="gazeforge-tour.md">Tour</a>
<a href="documentation-map.md">Task map</a>
<a href="troubleshooting.md">Troubleshooting</a>
<a href="runnable-examples.md">Examples</a>
<a href="https://github.com/stefanosbalaskas/GazeForge/issues">Ask / report</a>
</nav>

Use this page **after** the primary outcome/estimand and sensitivity plan are frozen,
and after the relevant analysis outputs exist. If the sensitivity plan is not frozen
yet, start with [Outcome & estimand preregistration](estimand-preregistration.md).

!!! warning "Sensitivity consistency is not a validity certificate"
    A result that changes little across several specifications may be easier to audit,
    but that consistency does not establish measurement validity, construct validity,
    device validity, model generalisation, causal validity, or external validity.

## Run the worked audit

```bash
python examples/15_worked_sensitivity_robustness_audit.py \
  --output-dir worked-sensitivity-robustness-audit
```

The deterministic teaching bundle writes:

```text
01_sensitivity_registry.csv
02_executed_conditions.csv
03_result_comparison.csv
04_deviation_ledger.csv
05_interpretation_matrix.csv
06_reporting_language.csv
README.md
sensitivity_manifest.json
```

It is `synthetic_demo_not_empirical_evidence`. It generates no p-values,
significance decisions, causal claims, construct-validity claims, native-device
validity claims, or automatic `robust`/`not robust` verdict.

## Primary result versus sensitivity result

The primary result remains the reference even when a sensitivity variant looks more
favourable. A sensitivity analysis asks whether a scientifically defensible change in
one declared analysis decision materially changes what is observed.

Before comparing a variant to the primary result, verify that both target the same:

- outcome definition;
- estimand;
- contrast;
- inferential unit;
- analysis population, unless population change is the declared sensitivity target;
- missing/zero/censoring semantics;
- exposure/denominator definition;
- interpretation boundary.

If one of those changes, document the changed estimand or target population instead
of calling the result a direct robustness check.

## Keep the sensitivity status explicit

| Status | Meaning | Reporting rule |
| --- | --- | --- |
| **primary** | registered reference specification | remains the primary result |
| **prespecified sensitivity** | planned before outcome inspection | report whether executed, denominators, and result difference |
| **exploratory sensitivity** | scientifically useful but not prespecified as confirmatory | label exploratory everywhere |
| **deviation** | introduced after the frozen plan | append to the deviation ledger; do not rewrite history |

A later deviation can be informative. It cannot silently become the original plan.

## Sensitivity dimensions

### QC and coverage

Ask whether the result changes under a scientifically justified alternative usable-
exposure or QC rule. Preserve the original denominator and report the changed
analysis population.

**API:** [Quality-control API](api-reference.md#quality-control)

**Do not infer:** that a stable estimate validates the QC threshold itself.

### Eye-event definition

Repeat the measurement under a prespecified detector/threshold alternative when the
scientific question depends on event segmentation.

**API:** [Eye-events API](api-reference.md#eye-events)

**Do not infer:** physiological truth from detector agreement.

### AOI definition

Use a documented alternative region boundary only when the alternative is
scientifically defensible. Preserve the semantic construct label and exposure rule.

**API:** [Semantic AOI API](api-reference.md#semantic-aois)

For moving regions, preserve the reviewed temporal support and no-extrapolation rule:
[Dynamic AOI API](api-reference.md#dynamic-aois).

**Do not infer:** construct validity from AOI-boundary stability.

### Scanpath preprocessing

Sensitivity can cover repeat-collapse rules, unassigned-state policy, transition
construction, or another prespecified sequence transformation.

**API:** [Scanpath API](api-reference.md#scanpaths)

**Do not infer:** a latent strategy, comprehension state, diagnosis, or intent.

### Sampling and derivation

A lower-rate or alternate-rate condition must preserve the derivation rule, source
provenance, label-purity policy, and retained-data fraction.

**API:** [Sampling-sensitivity API](api-reference.md#sampling-sensitivity)

**Do not infer:** native-device validity from a derived-rate sensitivity condition.

### Model family or estimator

If the scientific estimand is unchanged, a prespecified alternative specialist model
can be a sensitivity analysis. Record convergence/diagnostics instead of treating a
failed fit as a valid result.

**API:** [Model-comparison API](api-reference.md#model-comparison)

For held-out event-model differences, compare matched observations/folds:
[Matched-fold differences API](api-reference.md#matched-fold-model-differences).

**Do not infer:** universal model superiority from one sensitivity comparison.

## One-factor changes versus a planned multiverse

Changing one analysis decision at a time makes attribution easier. A planned
multiverse/factorial sensitivity can be appropriate when interactions among choices
are the scientific question, but the design should be frozen before results are
inspected and resource limits should be explicit.

Do not generate a large specification search and then report only the most favourable
subset. Report the complete registered set, including failures and unevaluable cells.

Before treating a fitted variant as an interpretable sensitivity result, pass it through the [Model diagnostics & convergence clinic](model-diagnostics-convergence.md). A model can be same-estimand yet still be blocked by convergence, singularity, separation, covariance/Hessian, or missing-diagnostic failures.

## Non-evaluable and non-converged are results of the audit

A sensitivity condition is not silently discarded because it fails to produce a
usable estimate.

Use explicit statuses such as:

- `completed`;
- `not_evaluable`;
- `non_converged`.

For `not_evaluable`, record why the data/denominator/coverage cannot support the
specified analysis. For `non_converged`, retain the attempted model identity and
relevant diagnostics. Do not substitute a different estimator silently.

A failed or unevaluable variant weakens the scope of the sensitivity claim; it does
not become missing from the scientific record.

## Compare denominators and exposure, not only estimates

A sensitivity result can look different because the underlying analysis population
changed. Always report, as relevant:

- participant/trial/sample denominator;
- observable exposure;
- missingness rate;
- censoring count/exposure;
- exclusions introduced by the variant;
- retained-data fraction for sampling/purity variants.

When those change, interpret estimate changes together with the population change.

## Same-estimand versus changed-estimand comparisons

A direct robustness comparison requires the same estimand. If a complete-case
restriction, alternate censoring rule, different target population, or transformed
outcome changes the estimand, label it explicitly.

A changed-estimand analysis can still be useful, but it answers a different question.
It should not be used as evidence that the registered primary estimand is unchanged.

## Do not reduce sensitivity to a binary verdict

Avoid automatically generating a `robust = TRUE/FALSE` field from arbitrary
thresholds. Instead report the evidence that a reader can inspect:

- which variants were planned;
- which were executed;
- which were not evaluable or did not converge;
- whether the estimand remained the same;
- denominator/exposure change;
- estimate or descriptive-result change;
- uncertainty change where supplied by the specialist model;
- direction consistency where scientifically meaningful;
- interpretation boundary.

The scientific conclusion remains a study-level judgement, not a software truth
label.

## Worked example interpretation

The worked audit deliberately includes:

- one primary reference specification;
- completed prespecified coverage, detector, and derived-rate variants;
- one prespecified alternative model that is `non_converged`;
- one strict-coverage condition that is `not_evaluable`;
- one exploratory AOI-boundary variant;
- one post-result complete-case deviation that changes `E01` to `E01_CC` and is
  therefore `changed_estimand_not_comparable`.

The synthetic values exist only to exercise the audit structure. They are not an
empirical effect estimate and do not establish that any real study is robust.

## Reporting examples

### Methods

> Sensitivity analyses followed the preregistered registry. Prespecified variants evaluated alternative coverage, event-definition, sampling, and model-family specifications while retaining the registered primary estimand where declared. Exploratory and post-registration deviations were recorded separately and did not replace the primary specification.

### Results

> All registered sensitivity conditions are reported. Same-estimand completed variants are presented with their denominator/exposure and estimate differences relative to the primary specification. One prespecified model-family variant did not converge and one strict-coverage condition was not evaluable; both remain in the sensitivity record rather than being omitted.

### Sampling limitation

> The lower-rate condition was a derived-rate sensitivity analysis under the declared derivation rule and does not establish native-device validity.

### Changed-estimand deviation

> A post-registration complete-case analysis changed the target population and was therefore treated as an exploratory deviation rather than as a direct robustness test of the registered primary estimand.

### Limitations

> The sensitivity analysis is limited to the registered and executed specifications. Untested decisions, non-evaluable conditions, non-converged variants, and any changed-estimand deviations remain explicit limits on the scope of the robustness discussion.

## Figure and table guidance

A sensitivity figure/table should identify:

- primary reference row/line;
- prespecified versus exploratory/deviation status;
- same-estimand versus changed-estimand status;
- denominator or retained-data fraction;
- execution status (`completed`, `not_evaluable`, `non_converged`);
- estimate/summary difference without suppressing failed conditions;
- evidence boundary in the caption when derived-rate or synthetic/demo output could
  be overread.

Do not use visual emphasis to hide unfavourable or failed variants.

## Archive record

Archive at least:

1. the frozen preregistration sensitivity registry;
2. exact executed specifications;
3. complete comparison table;
4. deviations and timing;
5. non-evaluable/non-converged reasons and diagnostics;
6. input/output/software fingerprints where available;
7. reporting language and interpretation boundaries.

The [Reviewer & replication handoff](reviewer-replication-handoff.md) should point to
these artifacts when sensitivity analyses are material to a manuscript claim.

## Continue through the research path

- [Outcome & estimand preregistration](estimand-preregistration.md) — freeze sensitivity intent before model fitting.
- [Denominator, exposure & censoring clinic](denominator-exposure-censoring.md) — reconcile exposure, observed zero, missingness, and censoring before comparing variants.
- [Analysis handoff](analysis-handoff.md) — preserve inferential units, exposure, missingness, and censoring.
- [Measurement & interpretation clinic](measurement-interpretation.md) — distinguish observable sensitivity from construct validity.
- [Reporting & interpretation clinic](reporting-clinic.md) — translate the complete sensitivity record into claim-safe prose.
- [Publication readiness](publication-readiness.md) — verify complete sensitivity reporting before submission.
- [Reviewer & replication handoff](reviewer-replication-handoff.md) — expose the complete sensitivity set and rerun/access requirements.

## Scientific boundary

Sensitivity analysis improves transparency about dependence on declared analysis
choices. It does not select the correct estimator, create construct validity, make an
observational contrast causal, validate a tracker, turn derived rate into native rate,
or authorize a universal robustness verdict. The worked bundle is
`synthetic_demo_not_empirical_evidence` and is **not empirical validation evidence**.
