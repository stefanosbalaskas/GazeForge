---
description: Audit denominators, exposure, observed zero, missingness, absent-by-design states, undefined metrics, and right-censored gaze latencies before modelling and reporting.
search:
  boost: 1.5
---

# Denominator, exposure & censoring clinic

<div class="gf-doc-kind" role="note" aria-label="Documentation type">
<strong>Method clinic</strong> · Reconcile who/what was observable before turning gaze counts, rates, proportions, dwell, or latency into model inputs.
</div>

<nav class="gf-help" aria-label="Documentation help">
<a href="gazeforge-tour.md">Tour</a>
<a href="documentation-map.md">Task map</a>
<a href="troubleshooting.md">Troubleshooting</a>
<a href="runnable-examples.md">Examples</a>
<a href="https://github.com/stefanosbalaskas/GazeForge/issues">Ask / report</a>
</nav>

Use this clinic after import/QC/review and before specialist modelling. The central
question is not “what number can I compute?” but **what denominator/exposure makes
that number meaningful, and what does each zero or missing value actually mean?**

!!! warning "Missing is not zero"
    Do not use `fillna(0)` to repair an analysis table. Observed zero, missing,
    absent-by-design, undefined denominator, and right-censored no-event latency
    are different scientific states.

## Run the worked audit

```bash
python examples/16_worked_denominator_exposure_audit.py \
  --output-dir worked-denominator-exposure-audit
```

The deterministic teaching bundle writes:

```text
01_observation_status_registry.csv
02_denominator_exposure_ledger.csv
03_count_rate_audit.csv
04_proportion_dwell_audit.csv
05_latency_censoring_audit.csv
06_reconciliation_flow.csv
07_reporting_language.csv
08_api_route_map.csv
README.md
denominator_exposure_manifest.json
```

It is `synthetic_demo_not_empirical_evidence` and is **not empirical validation
evidence**.

## Six observation states to keep separate

| Status | Meaning | Numeric zero allowed? | Latency censoring? |
| --- | --- | ---: | ---: |
| `observed_positive` | target was observable and a positive outcome was observed | no | event observed |
| `observed_zero` | target was observable and the declared outcome truly equalled zero | yes | right-censor only if the latency event was not observed |
| `partial_observed` | target was observable for partial exposure | yes, if zero was actually observed | censor at observed exposure when appropriate |
| `missing_trial` | trial/measurement unavailable | no | no |
| `absent_by_design` | target did not exist in that design condition | no | no |
| `undefined_denominator` | rate/proportion denominator is zero/unknown | no | no |

## Count, rate, proportion, dwell, and latency

**Counts:** retain the event count **and** observable exposure. Unequal exposure means
raw counts are not directly comparable.

**Rates:** compute only when the denominator is positive and defined:

```text
fixation_rate_per_s = fixation_count / aoi_observable_ms * 1000
```

**Proportions:** retain numerator and denominator; do not archive only a percentage.
If the denominator is zero or undefined, the proportion is undefined rather than zero.

**Dwell:** preserve AOI observability and gaze exposure so a dwell of zero can be
distinguished from unavailable measurement.

**First-fixation latency:** when the AOI was observable but no fixation occurred,
retain an event indicator and right-censor time. Missing or absent-by-design trials
are not censored events.

## Denominator reconciliation

At minimum, report:

1. expected participant × trial × AOI rows;
2. rows with observed gaze;
3. rows with observable AOI exposure;
4. rows eligible for rate/proportion calculation;
5. genuine observed-zero rows;
6. right-censored latency rows;
7. missing-trial rows;
8. absent-by-design rows;
9. undefined-denominator rows.

Do not silently complete-case filter between these stages.

## Coverage and partial observation

Coverage thresholds are analysis decisions, not universal validity rules. Preserve
the raw observed exposure and the threshold decision separately. A partially observed
trial can still contain a genuine zero under the declared rule, but the reduced
exposure must remain visible.

## API routes

- [Schema validation](api-reference.md#schema-validation) — source identities and units.
- [Quality control](api-reference.md#quality-control) — QC evidence without automatic exclusion.
- [Eye events](api-reference.md#eye-events) — event definitions and timing.
- [Semantic AOIs](api-reference.md#semantic-aois) — AOI identity/assignment provenance.
- [Scanpaths](api-reference.md#scanpaths) — sequence support without zero-filling absent states.

After denominator and censoring semantics are frozen, use the [Missing-data assumptions & treatment handoff](missing-data-assumptions.md) when unavailable or partial measurements require explicit assumptions or treatment planning, then continue with the [Analysis handoff](analysis-handoff.md). After the specialist model is fitted, use the
[Model diagnostics & convergence clinic](model-diagnostics-convergence.md) before
interpreting the result.

## Reporting examples

### Methods

> Participant-by-trial gaze outcomes retained the observed exposure used to construct counts, rates, proportions, and dwell measures. Observed zero, missing, absent-by-design, undefined-denominator, and right-censored states were represented separately; missing observations were not converted to zero.

### Results

> Denominator flow is reported from expected trials through observable exposure and analysis-eligible rows. Rate/proportion summaries exclude mathematically undefined denominators without recoding them as zero, and no-fixation latency observations remain right-censored when the AOI was observable.

### Limitations

> Differences in usable gaze exposure and AOI observability may alter the effective analysis population and precision. The denominator audit documents those changes but does not establish measurement, construct, device, causal, or external validity.

## Scientific boundary

This clinic does not select an inferential estimator, impute missing observations,
validate a QC threshold, establish construct validity, or turn derived/observed
sampling evidence into native-device validity. The worked example is
`synthetic_demo_not_empirical_evidence`.
