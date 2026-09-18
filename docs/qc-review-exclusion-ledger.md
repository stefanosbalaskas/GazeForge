# QC review and exclusion ledger

Use this clinic after you have created a canonical gaze table and **non-destructive QC evidence** but before you drop rows, trials, or participants from an analysis. The goal is to make the decision layer reconstructable: what was flagged, what required review, what was retained, what was excluded, which rule applied, and which denominator each decision used.

!!! warning "QC evidence ≠ automatic invalidity"
    `qc_flag`, anomaly scores, missingness summaries, bounds diagnostics, and trial-quality scores are **review evidence**. They do not by themselves prove that a sample, trial, participant, tracker, event model, calibration, or measurement is invalid. This worked workflow requires a separate decision ledger before exclusions affect the primary analysis.

## Run the worked example

From a repository checkout with GazeForge installed:

```bash
python examples/08_worked_qc_review_ledger.py \
  --output-dir worked-qc-review-ledger-demo
```

The demonstration is deterministic and classified:

```text
synthetic_demo_not_empirical_evidence
```

It uses three participants, three trials per participant, and 30 samples per trial. The teaching cases are intentionally small enough to audit by hand:

- `P001 / T02` contains 12/30 missing-gaze samples;
- `P002 / T03` contains 9/30 off-screen samples;
- `P003 / T01` contains an isolated within-screen jump;
- automated anomaly flags are generated with a fixed random state;
- one anomaly-flagged sample from a retained trial is explicitly reviewed and retained;
- two trial-level exclusion criteria are declared as prespecified;
- one additional criterion is labelled exploratory and sensitivity-only.

The result is a workflow where **flags and exclusions are different objects**.

## Why this stage exists

A reproducible analysis needs at least four layers to remain distinct:

```text
observed samples
      ↓
QC evidence
      ↓
review decision
      ↓
analysis derivative
```

Collapsing these layers creates common audit problems. A software flag can be mistaken for a scientific judgment, an exclusion can be applied without an explicit denominator, or a post-hoc sensitivity rule can be described as if it had been prespecified.

The ledger prevents that compression.

## The decision vocabulary

Use the terms consistently:

| State | Meaning |
| --- | --- |
| `flagged` | a diagnostic or model identified something for attention |
| `review_required` | a human or governed review step is still needed |
| `retained` | the reviewed unit remains eligible for the stated analysis |
| `excluded` | the reviewed unit is removed from the stated analysis under a recorded rule |
| `exploratory` | the rule or analysis was not part of the frozen primary decision policy |
| `sensitivity_only` | the rule is evaluated separately and does not alter the primary analysis table |

A row can be **flagged and retained**. That is an expected outcome, not a contradiction.

## Criteria registry

The example freezes four criteria before applying the decision ledger:

| ID | Scope | Status | Metric | Rule | Action |
| --- | --- | --- | --- | --- | --- |
| `C01` | trial | prespecified | `missing_rate` | `>= 0.30` | reviewed trial exclusion |
| `C02` | trial | prespecified | `offscreen_rate` | `>= 0.20` | reviewed trial exclusion |
| `C03` | sample | prespecified | `qc_flag` | `True` | review only |
| `S01` | trial | exploratory | `anomaly_rate` | `>= 1/30` | sensitivity only |

The numeric cutoffs are **teaching values**, not universal recommendations. A threshold is reproducible when it is written down; reproducibility does not make it externally validated.

## Primary workflow

```text
canonical source
      │
      ├─ fingerprint + deep copy
      ▼
non-destructive anomaly QC
      │
      ├─ qc_flag
      ├─ qc_anomaly_score
      └─ trial-quality summaries
      │
      ▼
criteria registry
      │
      ├─ prespecified C01 / C02
      ├─ review-only C03
      └─ exploratory S01
      │
      ▼
human-reviewed ledgers
      │
      ├─ sample review
      ├─ trial review
      └─ participant review
      │
      ▼
reviewed sample-status table
      │
      ├─ all pre-review rows still represented
      └─ explicit analysis_status
      │
      ▼
separate primary-analysis derivative
```

The canonical source and pre-review QC table are not overwritten.

## Sample-level review

The example selects one `qc_flag=True` sample from a trial that remains eligible for the primary analysis. Its sample ledger records:

- participant;
- trial;
- timestamp;
- anomaly score;
- criterion ID;
- reviewer;
- review status;
- decision;
- denominator; and
- rationale.

The decision is `retained`.

This is deliberate. The example mechanically demonstrates that:

```text
qc_flag == True
```

does **not** imply:

```text
decision == "excluded"
```

If a study intends to exclude samples automatically, that would need a separately justified, prespecified rule and an evidence basis appropriate to the intended measurement claim.

## Trial-level review

The trial ledger contains all nine trials, not only the problematic ones.

For every trial it records:

- `decision_order`;
- reviewer and review timestamp;
- participant/trial key;
- triggered criterion IDs;
- review status;
- decision;
- sample denominator;
- missing rate;
- off-screen rate;
- anomaly rate;
- trial quality score; and
- rationale.

The deterministic primary result is:

```text
trial denominator = 9
excluded trials   = 2
retained trials   = 7
```

`P001 / T02` is excluded under `C01`.
`P002 / T03` is excluded under `C02`.

The other seven trials remain retained.

## Participant-level review

A bad trial is not silently promoted into a bad participant.

The example reports, for each participant:

- total trial denominator;
- excluded trials;
- retained trials;
- participant-level review status; and
- participant decision.

All three participants retain at least two reviewed trials, so all three participants remain retained:

```text
participant denominator = 3
retained participants   = 3
```

This makes the aggregation rule visible instead of inferring participant invalidity from a sample- or trial-level diagnostic.

## Denominator accounting

Every exclusion statement should identify its denominator.

The example writes `08_exclusion_flow.csv` with four stages:

1. **pre-review QC samples** — no rows removed;
2. **trial review** — reviewed trial denominator and retained/excluded counts;
3. **participant review** — participant denominator and decisions;
4. **primary analysis rows** — original QC-row denominator and final retained rows.

The deterministic sample flow is:

```text
pre-review QC rows    = 270
excluded trial rows   = 60
primary-analysis rows = 210
```

Because every trial has 30 samples, excluding two reviewed trials removes exactly 60 rows from the separate primary-analysis derivative.

## Prespecified and exploratory decisions

The example never mixes the primary exclusion policy with the exploratory sensitivity rule.

`C01` and `C02` are tagged:

```text
status  = prespecified
purpose = primary_analysis
```

`S01` is tagged:

```text
status  = exploratory
purpose = exploratory_sensitivity
action  = sensitivity_only
```

The exploratory table also contains:

```text
applied_to_primary_analysis = False
```

This distinction matters when an analyst notices a plausible extra rule after seeing the data. The rule can still be useful as a sensitivity analysis, but the record should not backfill it as prespecified.

## Output bundle

The command writes eleven CSV tables:

```text
01_canonical_source.csv
02_pre_review_qc_samples.csv
03_trial_quality.csv
04_decision_criteria.csv
05_sample_review_ledger.csv
06_trial_review_ledger.csv
07_participant_review_ledger.csv
08_exclusion_flow.csv
09_reviewed_sample_status.csv
10_primary_analysis_rows.csv
11_exploratory_sensitivity.csv
```

It also writes:

```text
analysis_plan.json
provenance.json
workflow_manifest.json
```

### `01_canonical_source.csv`

The canonical teaching source before QC.

### `02_pre_review_qc_samples.csv`

The full non-destructive QC derivative. It remains unchanged while decisions are recorded elsewhere.

### `04_decision_criteria.csv`

The frozen registry for every primary, review-only, and exploratory criterion.

### `05_sample_review_ledger.csv`

An explicit example of an anomaly flag that is reviewed and retained.

### `06_trial_review_ledger.csv`

The complete nine-trial primary decision ledger.

### `07_participant_review_ledger.csv`

Participant-level reconciliation after trial review.

### `08_exclusion_flow.csv`

Compact denominator accounting suitable for a Methods appendix, supplement, or audit bundle.

### `09_reviewed_sample_status.csv`

All pre-review QC rows plus an explicit `analysis_status`. This table is useful when a reviewer needs to reconcile each row with the trial ledger.

### `10_primary_analysis_rows.csv`

A **new derivative**, not an overwritten QC table. Only reviewed retained trials are present.

### `11_exploratory_sensitivity.csv`

The post-hoc teaching criterion is evaluated here and is explicitly not applied to the primary analysis.

## Fingerprints and provenance

`workflow_manifest.json` records fingerprints for:

- canonical source;
- pre-review QC;
- reviewed sample status; and
- primary analysis rows.

It also records:

- source/pre-review row counts;
- trial denominator;
- retained/excluded trial counts;
- participant denominator;
- retained participant count;
- whether a flagged sample was reviewed and retained;
- whether `qc_flag` is an automatic exclusion rule;
- whether the exploratory rule affected the primary analysis; and
- explicit validity claims that were **not** created.

`provenance.json` records both the anomaly-QC operation and the reviewed primary-analysis derivation.

## Replace the teaching policy with your study policy

For a real study, do not copy the example thresholds mechanically.

Freeze or document, as appropriate:

| Question | Record |
| --- | --- |
| What unit can be excluded? | sample, event, trial, participant, stimulus, session |
| What is the denominator? | exact count before each decision |
| Which metric triggers review? | missingness, bounds, calibration, timing, anomaly score, etc. |
| Is the rule prespecified? | yes/no plus protocol or preregistration reference |
| Does a trigger automatically exclude? | usually separate this from review unless explicitly justified |
| Who reviewed it? | reviewer ID or governed role |
| What decision was made? | retained / excluded / review required |
| Why? | criterion ID plus rationale |
| What happened to downstream data? | separate derivative/fingerprint |
| Was a later rule exploratory? | label it explicitly and keep it out of the primary table |

## Suggested manuscript wording

A compact Methods description can report the rule and denominator without implying autonomous software judgment:

> Automated QC flags were retained as review evidence rather than treated as automatic exclusions. Trial-level exclusions were applied only after review against prespecified missingness and coordinate-bounds criteria. The pre-review QC table was preserved unchanged, and exclusions were recorded in a separate decision ledger with unit-level denominators.

For exploratory sensitivity decisions:

> An additional anomaly-rate rule was evaluated post hoc as a sensitivity analysis and was not applied to the primary analysis dataset.

Adapt these statements to the actual protocol; do not report the teaching thresholds unless your study truly used them.

## Reporting checklist

Before freezing a manuscript-facing exclusion bundle, verify:

- the source and pre-review QC derivatives are preserved;
- every criterion has an ID, scope, status, metric, operator, and threshold;
- prespecified and exploratory rules are distinguishable;
- every excluded unit has a review record and rationale;
- every reported count includes its denominator;
- sample-, trial-, and participant-level decisions are not conflated;
- a flagged observation can remain retained when review supports retention;
- the primary-analysis derivative is fingerprinted separately;
- sensitivity rules do not silently rewrite the primary analysis;
- the exact GazeForge version or commit SHA is recorded; and
- no validity claim is broader than the validation design supports.

## What the worked example refuses to do

| Operation | Policy |
| --- | --- |
| treat `qc_flag=True` as automatic exclusion | **No** |
| exclude a participant because one sample is anomalous | **No** |
| silently delete source or QC rows | **No** |
| overwrite the pre-review QC table | **No** |
| disguise an exploratory rule as prespecified | **No** |
| omit denominators from exclusion reporting | **No** |
| claim a reproducible threshold is validated | **No** |
| claim tracker/device/event-model/measurement validity | **No** |

## Continue the workflow

If you are starting from a tracker export, first use [Worked tracker import & QC](worked-tracker-import.md).

After review/exclusion decisions are frozen:

- continue to [Research recipes](research-recipes.md) for measurement/AOI workflows;
- use the [Event-model validation clinic](event-model-validation-clinic.md) for learned event models;
- use [Study lifecycle](study-lifecycle.md) to keep import, review, validation, freeze, and reporting connected;
- use [Publication readiness](publication-readiness.md) before manuscript submission; and
- archive the criteria registry, ledgers, exclusion flow, fingerprints, analysis plan, and exact software identity with the final evidence bundle.
