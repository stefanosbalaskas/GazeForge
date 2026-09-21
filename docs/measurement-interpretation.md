---
description: Audit what gaze-derived measures directly support, what substantive interpretations require extra evidence, and which validity checks should accompany a claim.
search:
  boost: 1.7
---

# Measurement & interpretation clinic

<div class="gf-doc-kind" role="note" aria-label="Documentation type">
<strong>Interpretation clinic</strong> · Connect gaze-derived observables to evidence requirements, validity threats, sensitivity checks, limitations, reporting language, and API/artifact provenance.
</div>

<nav class="gf-help" aria-label="Documentation help">
<a href="gazeforge-tour.md">Tour</a>
<a href="documentation-map.md">Task map</a>
<a href="troubleshooting.md">Troubleshooting</a>
<a href="runnable-examples.md">Examples</a>
<a href="https://github.com/stefanosbalaskas/GazeForge/issues">Ask / report</a>
</nav>

Use this page when the measurement table already exists and the next question is **what does this variable support me saying?** If the planned primary/secondary/exploratory outcomes or contrasts are not frozen yet, first use the [Outcome & estimand preregistration clinic](estimand-preregistration.md).

GazeForge can make event definitions, AOIs, denominators, censoring, confidence, sampling provenance, and review decisions explicit. It does **not** automatically turn those observables into trust, persuasion, comprehension, interest, memory, emotion, intent, diagnosis, preference, cognitive effort, or another latent construct.

!!! info "Methodological basis"
    This clinic operationalizes two complementary methodological sources rather than inventing a package-specific validity standard:

    - Dunn et al., *Minimal reporting guideline for research involving eye tracking (2023 edition)* — [DOI 10.3758/s13428-023-02187-1](https://doi.org/10.3758/s13428-023-02187-1)
    - Orquin & Holmqvist, *Threats to the validity of eye-movement research in psychology* — [DOI 10.3758/s13428-017-0998-z](https://doi.org/10.3758/s13428-017-0998-z)

    The clinic does not rely on the retracted “Eye tracking: empirical foundations for a minimal reporting guideline” article.

## The interpretation path

<div class="gf-flow" aria-label="Five-stage measurement interpretation path">
<div><strong>01</strong><span>Observable</span><small>Name exactly what was measured and at what unit.</small></div>
<div><strong>02</strong><span>Bridge</span><small>State the construct interpretation and evidence it requires.</small></div>
<div><strong>03</strong><span>Threats</span><small>Identify detector, AOI, quality, censoring, sampling, and design threats.</small></div>
<div><strong>04</strong><span>Sensitivity</span><small>Test justified alternatives without selecting the most favourable result.</small></div>
<div><strong>05</strong><span>Report</span><small>Write the observable, limitation, and supported scope explicitly.</small></div>
</div>

Keep **the observable** and **the proposed construct** as separate fields in the research record.

## Measure-by-measure interpretation guide

| Measure | Observable / possible use | Requires | Threats and sensitivity | Do not infer automatically | API / artifact |
| --- | --- | --- | --- | --- | --- |
| **AOI dwell** | observed fixation duration assigned to a frozen AOI; descriptive visual inspection | event definition, AOI provenance, exposure | detector choice, AOI boundary, missing exposure; use justified detector/AOI sensitivity | trust, persuasion, interest, comprehension, preference | [Semantic AOI API](api-reference.md#semantic-aois) · 04_trial_aoi_metrics.csv |
| **Fixation count** | declared fixation-event frequency | detector identity, AOI rule, exposure | detector fragmentation, unequal exposure, data loss; inspect detector/coverage sensitivity | interest, difficulty, engagement, cognitive effort | [Eye-events API](api-reference.md#eye-events) · [Semantic AOI API](api-reference.md#semantic-aois) |
| **First-fixation latency** | time from declared origin to first observed AOI fixation | origin, exposure, event indicator, censor time | no-fixation censoring, unequal exposure, AOI boundary; use censoring-aware analysis | noticeability, salience, preference, memory | [Eye-events API](api-reference.md#eye-events) · 04_trial_aoi_metrics.csv |
| **Event duration / boundaries** | timing under the declared event method | timebase, method identity, threshold/version, validation when claimed | sampling and detector dependence; run prespecified method/rate sensitivity | physiological truth of one algorithmic event definition | [Eye-events API](api-reference.md#eye-events) |
| **Scanpath / transitions** | ordered semantic AOI sequence | reviewed AOIs, sequence rule, repeat/unassigned policy | AOI semantics and sequence preprocessing | strategy, persuasion, comprehension, intent, diagnosis | [Scanpath API](api-reference.md#scanpaths) |
| **Model confidence** | probability-like model output | held-out labels, discrimination, calibration, coverage | miscalibration, distribution shift, selective coverage | correctness of an individual prediction | [Structural validation API](api-reference.md#structural-validation-scope) |
| **QC / coverage / data loss** | quality diagnostic or observed/usable proportion | original denominator, QC method, decision protocol | differential missingness, thresholds, exclusions | scientific invalidity of a flagged observation | [Quality-control API](api-reference.md#quality-control) |
| **Sampling / derivation** | native/nominal rate, observed cadence, derived rate | acquisition record, timestamps, derivation rule | conflating native/observed/derived conditions | native-device validity from derived-rate evidence | [Sampling-sensitivity API](api-reference.md#sampling-sensitivity) |

## First-fixation latency: absence is not zero

A trial with no fixation in an AOI does not have a latency of zero.

- **Zero latency** means the event occurred at the declared time origin.
- **No observed fixation** means the event was not observed during the available exposure.
- For time-to-event inference, preserve the no-fixation case as **right-censored** with an event indicator plus censoring/exposure time.

The [Analysis handoff](analysis-handoff.md) keeps these fields explicit. Do not discard no-fixation trials merely because a conventional mean-latency table cannot represent them.

## The construct bridge

A descriptive statement can often be supported directly:

> The claim AOI received greater observed fixation dwell under the declared event and AOI definitions.

A latent-construct statement needs more:

> Greater claim dwell indicates greater trust.

For the second statement, the gaze measure is only one component of the evidentiary chain. A defensible bridge usually needs:

1. theory explaining why the observable should covary with the construct in this task;
2. an independent outcome/criterion or validated measurement design;
3. evidence that detector, AOI, coverage, and quality choices do not manufacture the pattern;
4. an inferential model matching the repeated-measures structure and outcome distribution;
5. a conclusion limited to the population, task, stimuli, device, and validation design actually studied.

If those pieces are absent, report the gaze observable and keep the construct interpretation explicitly tentative or unsupported.

## Ten validity threats to check

1. **Construct bridge** — observable promoted to latent construct without independent evidence.
2. **Event definition** — result changes with detector, model, or threshold.
3. **AOI definition** — geometry, semantics, or overlap rule changes the outcome.
4. **Sampling/timebase** — native, observed, and derived rates are conflated.
5. **Data quality** — missingness or data loss differs systematically.
6. **Exclusion** — review choices materially change the analysis population.
7. **Inferential unit** — fixations or samples are treated as independent people/trials.
8. **Censoring** — no-event trials are discarded or encoded as zero.
9. **Generalisation** — task/device/stimulus-specific evidence is described universally.
10. **Researcher degrees of freedom** — many outcomes/thresholds are explored without primary/exploratory labels.

These are audit questions, not automatic truth labels.

## Sensitivity without cherry-picking

Sensitivity analysis asks whether a scientifically plausible alternative changes the conclusion. It should not search for the version with the smallest p-value or largest effect. After execution, use the [Sensitivity & robustness clinic](sensitivity-robustness-clinic.md) to retain failed/unevaluable variants, denominator changes, and same-estimand versus changed-estimand status.

Useful prespecified checks include AOI boundary perturbation, event-detector/threshold alternatives, QC/exclusion sensitivity, rate/derivation sensitivity, coverage/exposure sensitivity, censoring-aware latency analysis, and alternative held-out units only when identity evidence supports them.

Report the planned alternative set and what changed; do not silently choose the most favourable variant.

## Worked claim–evidence audit

~~~bash
python examples/12_worked_measurement_interpretation_audit.py \
  --output-dir worked-measurement-interpretation-audit
~~~

The example writes:

~~~text
01_claim_registry.csv
02_measurement_interpretation_matrix.csv
03_validity_threats.csv
04_sensitivity_plan.csv
05_reporting_language.csv
interpretation_audit.json
README.md
~~~

The claim registry uses scoped workflow states:

- **observable_supported**
- **requires_external_outcome**
- **requires_measurement_validation**
- **requires_sensitivity_analysis**
- **not_supported_by_gaze_alone**

It deliberately does **not** assign scientific truth labels named valid or invalid.

The example audits dwell→trust, fixation-count→interest, scanpath→persuasion strategy, confidence→correctness, QC-flag→invalidity, and derived-rate→native-rate claims. Each record states which evidence is missing or which narrower wording is supported.

## Reporting examples

### Dwell and a latent construct

**Avoid:** “Participants trusted the claim because they looked longer.”

**Prefer:** “Participants showed greater observed fixation dwell on the claim AOI under the declared event and AOI definitions. Trust was measured separately; the gaze result is interpreted as visual inspection rather than a direct trust measure.”

**Limitation:** AOI dwell can vary with event definition, exposure, AOI geometry, task demands, and missingness; it does not independently validate trust.

### No observed fixation

**Avoid:** “Participants never noticed the disclosure.”

**Prefer:** “No disclosure fixation was observed during the available trial exposure.”

**Limitation:** Absence of an observed fixation is not proof of absence of awareness or peripheral processing.

### Confidence

**Avoid:** “The model was 92% confident, therefore the label was correct.”

**Prefer:** “The model emitted 0.92 confidence. Discrimination and calibration were evaluated separately on held-out reference data.”

**Limitation:** A probability-like score is not individual-prediction correctness.

### Derived sampling condition

**Avoid:** “The method was validated at native 60 Hz.”

**Prefer:** “The method was evaluated on a derived 60 Hz condition created under the reported derivation rule.”

**Limitation:** Derived-rate evidence does not establish native-device validity.

## Minimum interpretation record

Before manuscript freeze, retain the exact observable, unit, event method, AOI source, exposure/denominator, missing-zero-censoring semantics, proposed construct, construct-bridge evidence, validity threats, sensitivity checks, inferential unit, generalisation scope, reporting boundary, and software identity.

## What this clinic does not do

This page does not provide universal rules such as “more dwell = more interest.” Interpretation depends on task, measurement model, preprocessing, missingness, event/AOI definitions, experimental design, external outcomes, and substantive theory.

GazeForge therefore remains a **measurement/process-data and provenance layer**. Construct validation belongs to the scientific design, not to an automatic package rule.

The worked measurement/interpretation audit is explicitly
`synthetic_demo_not_empirical_evidence`; it demonstrates the audit contract and does
not establish empirical measurement, construct, device, causal, or external validity.

## Continue through the research path

- [Outcome & estimand preregistration](estimand-preregistration.md) — freeze outcome status, estimands, contrasts, exposure/censoring rules, sensitivity checks, and deviations before modelling.
- [Analysis handoff](analysis-handoff.md) — preserve inferential units, denominators, missingness, and censoring.
- [Reporting & interpretation clinic](reporting-clinic.md) — translate frozen evidence into claim-safe Methods, Results, and captions.
- [Research terminology](research-terminology.md) — keep evidence labels consistent.
- [Sensitivity & robustness clinic](sensitivity-robustness-clinic.md) — audit the complete registered/executed sensitivity set without replacing the primary estimand.
- [Reviewer & replication handoff](reviewer-replication-handoff.md) — declare claim-artifact traceability, rerun access class, software identity, and limitations for external inspection.
- [Publication readiness](publication-readiness.md) — final manuscript/archive audit.
- [API reference](api-reference.md) — exact public interfaces behind the measurement pipeline.
