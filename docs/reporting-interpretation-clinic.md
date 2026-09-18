---
description: Task-first clinic for translating frozen GazeForge artifacts into Methods, Results, captions, supplements, and manuscript archives without upgrading the evidence.
search:
  boost: 1.6
---

# Reporting & interpretation clinic

<div class="gf-doc-kind" role="note" aria-label="Documentation type">
<strong>Reporting clinic</strong> · Translate frozen artifacts into manuscript wording while preserving the exact evidence class, denominator, split unit, sampling provenance, and interpretation boundary.
</div>

<nav class="gf-help" aria-label="Documentation help">
<a href="gazeforge-tour.md">Tour</a>
<a href="documentation-map.md">Task map</a>
<a href="troubleshooting.md">Troubleshooting</a>
<a href="runnable-examples.md">Examples</a>
<a href="https://github.com/stefanosbalaskas/GazeForge/issues">Ask / report</a>
</nav>

<nav class="gf-study-path" aria-label="Research workflow path">
<a href="documentation-map.md"><strong>1</strong><span>Task</span></a>
<a href="method-chooser.md"><strong>2</strong><span>Method</span></a>
<a href="artifact-dictionary.md"><strong>3</strong><span>Artifacts</span></a>
<a href="research-evidence-bundle.md"><strong>4</strong><span>Evidence bundle</span></a>
<a href="reporting-interpretation-clinic.md" aria-current="step"><strong>5</strong><span>Report</span></a>
<a href="publication-readiness.md"><strong>6</strong><span>Submit</span></a>
</nav>

A reporting layer should make the analysis easier to inspect; it must **not make the evidence sound stronger than it is**. This clinic therefore starts from already-frozen artifacts and asks five questions for each output family:

**Interpret → Report → Do not say → Archive → Continue to.**

!!! warning "Reporting polish cannot upgrade evidence"
    A deterministic archive, fluent Methods paragraph, or polished figure caption cannot establish tracker validity, native-device validity, measurement validity, model validity, AOI construct validity, or a substantive psychological effect when the underlying study does not provide that evidence.

## Run the reporting example

~~~bash
python examples/10_worked_manuscript_reporting_bundle.py \
  --output-dir worked-manuscript-reporting-bundle \
  --analysis-commit DEMO_UNSPECIFIED_COMMIT
~~~

With no --evidence-dir, the script first creates the deterministic #209 worked evidence bundle in the sibling directory worked-manuscript-reporting-bundle-evidence/. The reporting directory then contains **only reporting derivatives**:

~~~text
worked-manuscript-reporting-bundle/
├── methods_record.json
├── denominator_flow.csv
├── artifact_citation_table.csv
├── reporting_boundaries.json
├── software_identity.json
├── methods_example.md
├── results_example.md
├── archive_readme.md
└── reporting_manifest.json
~~~

The script SHA-256 fingerprints every upstream evidence file before and after reporting and fails if anything changed.

## What to say about each output family

| Output family | Interpret | Report | Do not say | Archive | Continue to |
| --- | --- | --- | --- | --- | --- |
| **Import / canonicalisation** | declared mapping from source fields/units into the canonical table | source identity, timestamp unit, coordinate basis, geometry, row-count checks | “successful import validated the tracker” | source contract + source fingerprint + canonical mapping | [Artifact dictionary](artifact-dictionary.md) |
| **QC** | anomaly/missingness/bounds evidence for review | method, seed/settings, quality summaries, pre-review denominator | “the algorithm identified invalid samples” | pre-review QC + quality table | [QC review ledger](qc-review-exclusion-ledger.md) |
| **Exclusions** | recorded researcher/review decisions | scope, criterion ID/status, denominators before/after, rationale | “QC automatically removed bad data” | criteria + review ledgers + denominator flow | [Publication readiness](publication-readiness.md) |
| **Transparent events** | deterministic event labels under the declared algorithm/threshold | algorithm, threshold/unit, sampling condition, version | “this threshold is physiologically universal” | event samples/intervals + method identity | [I-VT tutorial](tutorial-ivt-baseline.md) |
| **Learned events** | predictions under a specific model and evidence design | model/version, predictors, split unit, held-out metrics, calibration where relevant | “high sample accuracy proves accurate boundaries” | split ledger + matched predictions + sample/event metrics | [Validation cookbook](validation-reporting-cookbook.md) |
| **Static AOIs** | membership in frozen researcher/reviewed geometry | AOI source, labels, geometry, overlap rule, review state | “AOI membership proves attention meaning or a construct” | AOI definitions + assignment table | [Research recipes](research-recipes.md) |
| **Dynamic AOIs** | membership only where reviewed temporal support exists | source/model, keyframes, support interval, interpolation rule, no-extrapolation behavior | “the tracker/model knew the object location outside support” | keyframes/tracks + interpolation audit + review state | [Dynamic AOIs](dynamic-aois.md) |
| **Scanpaths / transitions** | observable AOI sequence structure | sequence construction, repeat collapsing, missing/unassigned handling, grouping unit | “the scanpath reveals trust, emotion, intent, diagnosis, or comprehension” | semantic sequence table + AOI provenance | [Practical workflow](practical-workflow.md) |
| **Calibration / confidence** | distributional relation between probabilities and observed outcomes | metric, held-out design, bins/coverage, threshold status | “a calibrated probability guarantees this prediction is correct” | calibration bins + confidence/coverage | [Calibration](calibration.md) |
| **Sampling-rate evidence** | native acquisition and any derived analysis rate are different evidence facts | native/nominal rate, observed cadence, derivation/resampling rule, analysis-rate status | “observed cadence proves native hardware rate” | source record + resampling/sensitivity provenance | [Reproducible reporting](reproducible-reporting.md) |
| **Synthetic/demo outputs** | software behavior under controlled demonstration inputs | identify as synthetic_demo_not_empirical_evidence | “the example validates GazeForge/device/model performance” | code + deterministic outputs + manifest | [Evidence status](evidence-status.md) |

## Denominators: make every transition reconstructable

A manuscript should allow the reader to answer:

1. How many source observations/trials/participants existed?
2. What was present before review?
3. What rule triggered review?
4. What was excluded and at what unit?
5. What exactly entered the primary analysis?

The worked denominator_flow.csv deliberately reports sample and trial units separately. Do not subtract trial exclusions from a sample denominator or silently switch units between Methods and Results.

## Copy-ready Methods patterns

### Import and acquisition

> Source files were retained separately from canonical derivatives. Timestamp units, coordinate semantics, participant/trial identity fields, and display/stimulus geometry were declared before canonicalisation. Observed timestamp cadence was treated as a stream diagnostic and was not used as proof of native hardware sampling rate.

### QC and exclusions

> QC outputs were preserved before review. Automated flags were treated as review evidence rather than automatic exclusions. Exclusion decisions were recorded separately with their decision scope, criterion identifier, denominator, and rationale, and were applied to a distinct primary-analysis derivative.

### Transparent event detection

> Eye events were derived using <algorithm> with <threshold + unit> under the reported sampling condition. The threshold was an analysis setting for this study and was not interpreted as a universal physiological cutoff.

### AOI definition and review

> AOIs were <researcher-defined / AI-proposed + reviewed / other traceable source>. Final geometry, labels, overlap handling, and review status were frozen before manuscript-facing aggregation. For dynamic AOIs, temporal support and no-extrapolation behavior were retained explicitly.

### Scanpaths

> Semantic scanpaths were constructed from reviewed fixation-to-AOI assignments using <repeat/unassigned rule> within <participant × trial or other explicit unit>. The sequences were interpreted as observable attention structure rather than as direct measures of latent psychological states.

### Validation split identity

> Evaluation was <participant-disjoint / stimulus-disjoint / dataset-held-out / source-token-disjoint> using <identity field>. The held-out unit is stated explicitly because these split designs are not interchangeable.

### Native versus derived rate

> Data were acquired at <native rate> Hz and analysed at <analysis rate> Hz. The analysis-rate condition was <native / derived>; when derived, the resampling and label-purity procedure was recorded and the result was not described as native-device validation.

### Software identity

> Analyses used GazeForge <version> under <Python/environment>. Development-checkout analyses additionally record the exact full Git commit SHA. Manuscript artifacts are linked to deterministic file/report fingerprints where available.

## Results wording: report observables before interpretation

### Safer

> The reviewed primary-analysis derivative retained <n> of <N> sample rows after <k> of <K> trials were excluded under the prespecified review protocol.

### Overstated

> The QC model removed invalid gaze.

### Safer

> Fixations were assigned to the reviewed claim AOI under the frozen geometry and overlap rule.

### Overstated

> Participants trusted the claim.

### Safer

> The classifier achieved the reported sample-level and event-level metrics on participant-disjoint held-out data.

### Overstated

> The model is generally accurate for new users.

The broader population/generalisation statement requires evidence beyond a single held-out design.

## Figure and table captions

A useful caption carries the evidence qualifier close to the visual:

> **Synthetic/demo AOI sequence diagnostic.** Geometry and sequence structure are shown for the worked software example; this figure is not empirical validation evidence and does not imply a latent psychological state.

For derived-rate benchmark figures:

> **Derived 60 Hz condition.** Results were computed after the prespecified derivation from the native source; they should not be read as native 60 Hz device validation.

For model comparison:

> **Matched held-out comparison.** Models were evaluated on the same held-out rows. Sample-level and event-level estimands are reported separately; no universal model ranking is implied.

## What belongs in the reporting bundle?

Keep the reporting layer small and auditable:

- structured Methods facts;
- denominator flow;
- artifact-to-manuscript/archive mapping;
- software/commit identity;
- explicit evidence boundaries;
- worked or final Methods/Results text;
- reporting manifest with upstream and reporting hashes.

Do not copy the empirical source into a reporting directory merely for convenience. Keep source/access governance separate from presentation.

## How this page differs from the existing reporting guides

- **This clinic** is task-first: “I have frozen files; what can I say?”
- [Reproducible reporting](reproducible-reporting.md) explains software/evidence identity and manuscript structure.
- [Validation reporting cookbook](validation-reporting-cookbook.md) gives detailed wording for held-out model evaluation.
- [Publication readiness](publication-readiness.md) is the final pre-submission audit.
- [Research evidence bundle](research-evidence-bundle.md) explains what to freeze before reporting begins.

## Evidence boundary

The worked reporting bundle is synthetic_demo_not_empirical_evidence. It performs **no new scientific analysis**, changes **no upstream exclusion/AOI/event decision**, and is **not empirical validation evidence**. Reporting structure improves transparency; it cannot increase the evidentiary strength of the underlying study.
