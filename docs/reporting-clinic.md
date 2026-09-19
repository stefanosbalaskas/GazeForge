---
description: Claim-safe reporting guidance for GazeForge import, QC, events, AOIs, scanpaths, validation, sampling, and synthetic examples.
search:
  boost: 1.6
---

# Reporting & interpretation clinic

<div class="gf-doc-kind" role="note" aria-label="Documentation type">
<strong>Reporting clinic</strong> · Move from frozen GazeForge artifacts to manuscript, supplement, and archive language without strengthening the evidence in prose.
</div>

<nav class="gf-help" aria-label="Documentation help">
<a href="gazeforge-tour.md">Tour</a>
<a href="documentation-map.md">Task map</a>
<a href="troubleshooting.md">Troubleshooting</a>
<a href="runnable-examples.md">Examples</a>
<a href="https://github.com/stefanosbalaskas/GazeForge/issues">Ask / report</a>
</nav>

Use the [Denominator, exposure & censoring clinic](denominator-exposure-censoring.md) first when zero/missing/exposure/censoring semantics are not yet reconciled.

Use this clinic after reviewed measurement outputs, the statistical handoff, the [Model diagnostics & convergence clinic](model-diagnostics-convergence.md), the [Uncertainty, multiplicity & inferential reporting clinic](inferential-reporting-audit.md) where inferential results are reported, and any material sensitivity/robustness audit are frozen. Primary/secondary/exploratory outcome status and planned contrasts should trace back to the [Outcome & estimand preregistration clinic](estimand-preregistration.md) when that registry is part of the study. If the unresolved question is whether a gaze-derived observable supports a substantive construct, use the [Measurement & interpretation clinic](measurement-interpretation.md) first. If registered sensitivity variants have been executed, freeze the complete record through the [Sensitivity & robustness clinic](sensitivity-robustness-clinic.md) before summarizing robustness in prose.
For model-ready participant × trial tables, start with the
[Analysis handoff](analysis-handoff.md). For source/QC/review/analysis/provenance
packaging, use the [Research evidence bundle](research-evidence-bundle.md).

!!! warning "Reporting cannot strengthen the evidence"
    Better prose, a complete archive, a deterministic demo, or passing software tests
    cannot turn derived data into native-device evidence, a source token into a
    participant, a QC flag into ground-truth invalidity, or gaze structure into a
    latent psychological state.

!!! info "Aligned with the community minimum reporting guideline"
    The clinic complements Dunn et al.'s *Minimal reporting guideline for research
    involving eye tracking (2023 edition)* rather than replacing it. In particular,
    preserve tracker manufacturer/model, native sampling frequency, recorded
    parameters/coordinate system, calibration/validation information, and any
    resampling or later processing as distinct reportable facts.
    [Open the guideline (DOI) →](https://doi.org/10.3758/s13428-023-02187-1)

## Publication path

<div class="gf-flow" aria-label="Seven-stage publication path">
<div><strong>01</strong><span>Task</span><small>Define the observable question and unit.</small></div>
<div><strong>02</strong><span>Method</span><small>Choose from the question and evidence, not convenience.</small></div>
<div><strong>03</strong><span>Artifacts</span><small>Review source, QC, events, AOIs, and sequences.</small></div>
<div><strong>04</strong><span>Handoff</span><small>Preserve grouping, denominators, missingness, and censoring.</small></div>
<div><strong>05</strong><span>Bundle</span><small>Freeze source, review, analysis, and provenance identity.</small></div>
<div><strong>06</strong><span>Report</span><small>Translate evidence into claim-safe prose and captions.</small></div>
<div><strong>07</strong><span>Readiness</span><small>Audit the manuscript and archive before release.</small></div>
</div>

## Import and canonicalisation

**Interpret.** Successful import means the declared fields were transformed under the
stated source contract.

**Report.** Name participant/trial fields, timestamp field/unit, coordinates/basis,
screen or stimulus geometry, source identity/fingerprint, nominal/native acquisition
information, observed timestamp cadence, and software identity.

**Do not say:** “Successful import validated the eye tracker.”

Import compatibility does not establish device validity, calibration validity,
native-rate fidelity, or event validity.

**Archive.** Source identity, import/source contract, canonical mapping, preflight
diagnostics, fingerprints, software identity.

**Continue to:** [Worked tracker import](worked-tracker-import.md).

## QC and exclusions

**Interpret.** QC output is review evidence. Exclusion is a separate decision with a
declared unit, rule, status, and denominator.

**Report.** Name the QC procedure and parameters, denominator before review, decision
unit, criteria, prespecified/exploratory status, and retained/excluded denominator flow.

**Do not say:** “The QC algorithm removed invalid samples.”

Prefer: “Samples were flagged by the QC procedure; exclusions were applied only under
the separately documented review rule.”

**Archive.** Pre-review QC, criterion registry, sample/trial/participant ledgers,
denominator flow, separate primary-analysis derivative.

**Continue to:** [QC review & exclusion ledger](qc-review-exclusion-ledger.md) · [Quality-control API](api-reference.md#quality-control).

## Eye events

**Interpret.** Event labels are outputs of a declared algorithm/model under a stated
timebase, sampling condition, threshold/model identity, and validation context.

**Report.** Transparent algorithms need algorithm, threshold, units, timebase/rate, and
sensitivity where relevant. Learned models additionally need model/version, training
condition, reference-label provenance, held-out unit, split design, calibration where
relevant, and metrics matched to the estimand.

**Do not say:** “I-VT at this threshold is the physiologically correct definition,” or
“The classifier is validated because it produced plausible labels.”

**Archive.** Exact parameters/model identity, event-labelled samples/intervals, split
ledger, matched held-out predictions, sample/event/calibration metrics where applicable.

**Continue to:** [Event-model validation clinic](event-model-validation-clinic.md) · [Eye-events API](api-reference.md#eye-events).

## Static and dynamic AOIs

**Interpret.** AOI membership is a geometric/semantic assignment under a declared AOI
definition, review process, overlap rule, and—for dynamic AOIs—temporal support policy.

**Report.** State whether AOIs were researcher-defined, AI-proposed and reviewed, or
imported from a traceable source. For dynamic AOIs, retain reviewed keyframes/tracks,
timebase, interpolation rule, supported gap, and no-extrapolation policy.

**Do not say:** “The AI-detected AOI is ground truth,” or “Looking at this AOI proves
trust, persuasion, comprehension, preference, or intent.”

**Archive.** Frozen geometry, semantic labels, model/confidence provenance, review
history, interpolation audit, final assignments.

**Continue to:** [Worked dynamic-AOI study](worked-dynamic-aoi-study.md) · [Semantic AOI API](api-reference.md#semantic-aois) · [Dynamic AOI API](api-reference.md#dynamic-aois).

## Scanpaths, transitions, motifs, and embeddings

**Interpret.** These summarize sequence structure in reviewed gaze/AOI representations.

**Report.** Name the sequence construction, AOI-label source, repeat-collapse and
unassigned-state policy, and any later feature transformation.

**Do not say:** “This scanpath demonstrates strategy, persuasion, comprehension,
emotion, or intent.”

**Archive.** Fixation/AOI assignments, sequence table, transformation parameters, and
model identity for any learned representation.

**Continue to:** [Analysis handoff](analysis-handoff.md) · [Scanpath API](api-reference.md#scanpaths).

## Validation split identity

**Interpret.** Generalisation strength depends on what was actually held out.

**Report.** Use the exact supported term: participant-disjoint, stimulus-disjoint,
source-token-disjoint, dataset-held-out, or another explicitly defined grouping unit.
For comparisons, say whether models used matched held-out rows/folds.

**Do not say:** “Participant-held-out” when only source-token disjointness is known.

**Archive.** Split ledger, authoritative identity mapping when available, held-out
predictions, leakage checks, split policy.

**Continue to:** [Validation reporting cookbook](validation-reporting-cookbook.md).

## Calibration, confidence, and coverage

**Interpret.** Calibration is a distributional property of probabilities; it does not
guarantee an individual prediction is correct.

**Report.** Name the held-out probability source, calibration metric, bins/estimator,
confidence thresholds, and coverage for abstention/selective prediction.

**Do not say:** “The prediction was correct because confidence was 0.92.” Do not say
accuracy improved after abstention without also reporting retained coverage.

**Archive.** Held-out probabilities, calibration bins, Brier/ECE outputs,
confidence/coverage diagnostics, study-specific abstention policy.

**Continue to:** [Calibration & dataset holdouts](calibration.md) · [Validation reporting cookbook](validation-reporting-cookbook.md).

## Native, observed, and derived sampling

**Interpret.** Native/nominal acquisition rate, observed timestamp cadence, and derived
analysis rate are distinct facts.

**Report.** State all three when they differ and name the derivation rule.

**Do not say:** “Validated on native 60 Hz data” when the 60 Hz condition was derived
from higher-rate acquisition.

**Archive.** Acquisition record, cadence diagnostics, resampling/label-purity rules, and
native-versus-derived statement.

**Continue to:** [Sampling sensitivity](sampling-sensitivity.md) · [Sampling-sensitivity API](api-reference.md#sampling-sensitivity).

## Synthetic/demo versus empirical evidence

**Interpret.** Synthetic examples can verify deterministic software behavior,
contracts, edge cases, plotting, and reporting structure. They do not establish
empirical performance or measurement validity.

**Report.** Preserve the classification
`synthetic_demo_not_empirical_evidence`.

**Do not say:** “The worked example validates GazeForge, the tracker, the event
detector, the AOI method, or a psychological interpretation.”

**Archive.** Example version/commit, manifest, fingerprints, evidence boundary.

**Continue to:** [Evidence status](evidence-status.md) · [Research evidence bundle](research-evidence-bundle.md).

## Statistical results after the GazeForge handoff

GazeForge does not choose the inferential estimator. Downstream reporting should
distinguish the measurement table, inferential unit, repeated-measures grouping,
statistical family/link/estimator, hierarchical structure, missing/censoring treatment,
uncertainty method, and diagnostic/convergence status.

A failed convergence, singularity, separation problem, invalid covariance estimate, or
other failed diagnostic is **not a valid result** merely because coefficients were
printed.

## Copy-ready structures

### Acquisition/import Methods

> Source files were preserved separately from the canonical derivative. The source
> mapping, timestamp unit, coordinate basis, participant/trial identifiers, and
> geometry were declared before conversion. Native/nominal acquisition information
> was reported separately from observed timestamp cadence.

### QC/exclusion Methods

> Automated QC outputs were treated as review evidence rather than automatic exclusion
> labels. Decisions were recorded at the prespecified {unit} level under {criteria},
> with pre-review denominators and the retained/excluded flow preserved separately.

### Event-detection Methods

> Eye events were derived using {algorithm/model} under {sampling/timebase condition}
> with {threshold/model version}. Where validation was part of the claim, performance
> was evaluated under {held-out unit} using {metrics}.

### AOI Methods

> AOIs were {researcher-defined / AI-proposed and human-reviewed / imported from a
> traceable source}. Geometry, labels, overlap rules, and review state were frozen
> before manuscript-facing aggregation.

### Scanpath Methods

> Semantic scanpaths were derived from reviewed fixation-to-AOI assignments using
> {repeat/unassigned policy} and treated as observable structural representations
> rather than direct measurements of latent psychological states.

### Validation statement

> Evaluation was {participant-/stimulus-/source-token-/dataset-} disjoint according to
> the available identity evidence. The generalisation claim was restricted to that
> split identity.

### Sampling statement

> Native/nominal rate, observed timestamp cadence, and derived analysis rate were
> recorded separately. The {rate} analysis condition was {native/derived} under
> {derivation rule}.

### Software identity

> Analyses used GazeForge {version}. Analyses from an unreleased development checkout
> additionally recorded exact commit {full SHA}, Python {version}, and material optional
> dependencies.

### Evidence-boundary paragraph

> The workflow supports the software transformation, review, and analysis records
> described above. It does not by itself establish device validity, native-rate
> validity, event-model validity outside the reported design, AOI construct validity,
> causal effects, or unsupported psychological-state interpretations.

## Figure and table captions

Put the evidence qualifier in the caption when the visual could otherwise be overread.

Prefer:

> **Figure X.** Held-out event-level performance on a derived 60 Hz condition.
> Acquisition was native 500 Hz; this does not constitute native 60 Hz device
> validation.

Avoid:

> **Figure X.** 60 Hz validation results.

For synthetic figures, label them synthetic/demo in the caption or adjacent note.

## Worked manuscript/reporting bundle

```bash
python examples/11_worked_manuscript_reporting_bundle.py \
  --output-dir worked-manuscript-reporting-bundle
```

The script reuses the existing evidence-bundle example in a temporary directory,
fingerprints every upstream file before and after extraction, and fails if reporting
changes the upstream source/QC/review/analysis bundle.

It writes reporting derivatives only:

```text
methods_record.json
denominator_flow.csv
artifact_citation_table.csv
reporting_boundaries.json
software_identity.json
methods_example.md
results_example.md
archive_readme.md
reporting_manifest.json
```

It creates no p-values, effect sizes, inferential statistics, or substantive effects.
The bundle remains `synthetic_demo_not_empirical_evidence`.

## Final next step

After the reporting draft is frozen, build the [Reviewer & replication handoff](reviewer-replication-handoff.md) so an external reader can trace claims to artifacts, understand access requirements, and distinguish fully rerunnable, authorized-input rerunnable, and inspectable-only cases. Run [Publication readiness](publication-readiness.md) after the reporting draft is
assembled. That is the final audit that wording, denominators, identities, figures,
manifests, and evidence boundaries still match the frozen analysis.

[Research evidence bundle →](research-evidence-bundle.md) ·
[Sensitivity & robustness clinic →](sensitivity-robustness-clinic.md) ·
[Analysis handoff →](analysis-handoff.md) ·
[Measurement & interpretation →](measurement-interpretation.md) ·
[Reproducible reporting →](reproducible-reporting.md) ·
[Publication readiness →](publication-readiness.md)
