# Worked tracker import and QC

Use this worked example when you have a tracker export and want to make the **import contract reviewable before event modelling**. It starts from a deterministic Gazepoint-style table, converts explicitly declared units into GazeForge's canonical schema, runs preflight diagnostics, adds non-destructive QC flags, and writes a manuscript-friendly audit bundle.

!!! warning "Executable import ≠ tracker validation"
    The demonstration is classified `synthetic_demo_not_empirical_evidence`. A successful `adapt_gazepoint_samples()` call shows that the declared software transformation can run on the supplied columns. It does not establish Gazepoint validity, GP3 validity, native 60 Hz validity, event-model validity, calibration quality, or measurement validity.

## Run the example

From a repository checkout with the base package installed:

```bash
python examples/07_worked_tracker_import_qc.py \
  --output-dir worked-tracker-import-qc-demo
```

No plotting or learned-model extra is required.

The example deliberately contains review cases rather than sanitising them away:

- one duplicated participant/trial/timestamp key;
- two off-screen coordinates after normalized→pixel conversion;
- one missing gaze coordinate; and
- no missing participant/trial identity.

Those rows remain present through canonicalisation and QC. The point is to show **how uncertainty and anomalies stay visible**, not how to make a source table look clean.

## Source contract

The demo uses ordinary Gazepoint-style fields and declares every transformation explicitly.

| Canonical meaning | Demo source column | Source representation | Transformation |
| --- | --- | --- | --- |
| participant | `USER_FILE` | identifier | copied to `participant_id` |
| trial/media | `MEDIA_ID` | identifier | copied to `trial_id` |
| time | `TIME` | seconds | multiplied by `1000` → `timestamp_ms` |
| horizontal gaze | `BPOGX` | normalized screen fraction | multiplied by screen width → `x_px` |
| vertical gaze | `BPOGY` | normalized screen fraction | multiplied by screen height → `y_px` |
| pupil | `PUPIL` | demo numeric field | copied to `pupil` |
| validity | `VALIDITY` | demo source field | copied to `validity` |

The screen geometry is declared as **1920 × 1080 px** in the demonstration:

```python
gaze = adapt_gazepoint_samples(
    source,
    screen_size_px=(1920, 1080),
    participant_col="USER_FILE",
    trial_col="MEDIA_ID",
    timestamp_col="TIME",
    x_col="BPOGX",
    y_col="BPOGY",
    pupil_col="PUPIL",
    validity_col="VALIDITY",
    time_unit="seconds",
    coordinates="normalized",
    sampling_rate_hz=None,
)
```

`time_unit="seconds"` and `coordinates="normalized"` are declarations about this source contract. They are not safe guesses for every Gazepoint export.

## The workflow

```text
Gazepoint-shaped source table
        │
        ├─ deep snapshot + deterministic fingerprint
        │
        ▼
explicit adapter contract
seconds → milliseconds
normalized → pixels
        │
        ▼
canonical gaze table
        │
        ├─ participant/trial identity
        ├─ duplicate-key diagnostic
        ├─ missing-identity diagnostic
        ├─ observed timestamp cadence
        ├─ coordinate-bounds diagnostic
        └─ source/canonical row-count check
        │
        ▼
non-destructive anomaly flags
        │
        ▼
trial-quality summary
        │
        ▼
import contract + provenance + manifest
```

The script mechanically verifies that the source table remains unchanged and that source, canonical, and QC sample tables contain the same number of rows.

## Preflight before QC

### Identity

Participant and trial identity are checked before temporal or model operations. The demo reports `missing_identity_rows = 0`.

A real export with missing identity needs source-level review. Do not turn missing identifiers into guessed participants or trials.

### Duplicate sample keys

The key is:

```text
participant_id + trial_id + timestamp_ms
```

The demonstration deliberately contains a duplicated key. It is **retained**, counted, and written to the preflight record.

A duplicate timestamp can arise from repeated export rows, clock quantisation, multiple streams, or another acquisition/export process. Canonicalisation does not tell you which explanation is correct, so the example does not deduplicate automatically.

### Nominal rate versus observed cadence

The example records two distinct concepts:

```text
nominal_rate_hz       = 60.0
observed_cadence_hz   = inferred from median positive within-trial timestamp intervals
```

The demonstration is intentionally 60 Hz-shaped, so the two values are close. Their agreement is a teaching property of the synthetic construction, **not proof of native 60 Hz hardware acquisition**.

For a real study, record the nominal/native acquisition rate from acquisition metadata and separately inspect the analysed timestamp cadence.

### Coordinate bounds

Normalized values are converted to pixels with the declared screen dimensions. The demonstration then checks:

```text
0 <= x_px <= width_px
0 <= y_px <= height_px
```

Two deliberate rows fall outside those bounds. They remain in the canonical and QC tables. Off-screen values can represent invalid-value encodings, coordinate mistakes, or genuine excursions; the software cannot decide that meaning by clipping them.

### Row-count preservation

The worked script requires:

```text
source rows == canonical rows == QC rows
```

This protects the import/QC teaching contract from accidental silent deletion.

## Non-destructive QC

After preflight, the example calls:

```python
qc_samples = ai_flag_anomalies(
    canonical,
    sampling_rate_hz=gaze.sampling_rate_hz,
    random_state=42,
)

trial_quality = score_trial_quality(
    qc_samples,
    screen_size_px=(1920, 1080),
)
```

`ai_flag_anomalies()` adds model-derived QC fields to a copy. It does not delete source observations. `score_trial_quality()` aggregates missingness, bounds, anomaly rate, and large temporal gaps.

The output is review evidence, not an automatic exclusion rule.

## Output bundle

The command writes five CSV tables:

```text
01_source_tracker_export.csv
02_canonical_gaze.csv
03_import_preflight.csv
04_qc_samples.csv
05_trial_quality.csv
```

It also writes four JSON records:

```text
import_contract.json
analysis_plan.json
provenance.json
workflow_manifest.json
```

### `import_contract.json`

Records:

- exact source-column mapping;
- seconds→milliseconds transformation;
- normalized→pixel transformation;
- screen geometry;
- nominal rate and separately observed cadence;
- duplicate/missing/bounds diagnostics; and
- the no-silent-repair policy.

### `analysis_plan.json`

States that this is an import/QC demonstration, that no learned event model is fitted, that no exclusions are applied, and that the bundle is `synthetic_demo_not_empirical_evidence`.

### `provenance.json`

Carries fingerprints for the adaptation and QC operations plus their declared parameters and warnings.

### `workflow_manifest.json`

Freezes the bundle identity, source fingerprint, source CSV SHA-256, canonical/QC fingerprints, row-count and source-immutability checks, retained review cases, software version, and scientific boundary.

## Replace the demo with a real export

Before changing the input table, answer these from the acquisition/export record rather than from visual inspection of values:

| Question | Must be known before transformation |
| --- | --- |
| Which column identifies the participant? | exact source field and missing-value semantics |
| Which column identifies the trial/media/stimulus? | exact source field and grouping meaning |
| What unit is time stored in? | seconds, milliseconds, or another documented unit |
| What do x/y represent? | normalized fractions, pixels, or another coordinate system |
| What screen/stimulus geometry applies? | width × height used for conversion/bounds |
| What was the configured/native rate? | acquisition metadata, kept separate from observed cadence |
| What do pupil/validity fields mean? | source documentation for those export fields |
| Which exact file was analysed? | immutable original plus checksum/fingerprint |

Then change only the declarations that your source documentation supports.

Examples:

```python
# Export already stores milliseconds and pixels.
gaze = adapt_gazepoint_samples(
    source,
    screen_size_px=(1920, 1080),
    time_unit="milliseconds",
    coordinates="pixels",
)
```

If your source columns do not follow Gazepoint semantics, use `adapt_processed_table()` or a documented upstream transformation instead of forcing the Gazepoint adapter onto unrelated fields.

## What the example refuses to do

| Operation | Worked example policy |
| --- | --- |
| infer unknown participant/trial identity | **No** |
| guess timestamp units | **No** |
| guess screen geometry | **No** |
| infer native hardware rate from timestamps | **No** |
| delete duplicate keys | **No** |
| clip off-screen gaze | **No** |
| interpolate missing gaze | **No** |
| convert QC flags into automatic exclusions | **No** |
| fit a learned event model | **No** |
| claim Gazepoint/GP3/native-60-Hz validity | **No** |

## Archive this stage for a manuscript-facing study

At minimum retain:

- immutable original export or source file;
- file checksum and/or deterministic analysed-table fingerprint;
- source-column mapping;
- timestamp unit and conversion rule;
- coordinate basis and screen/stimulus geometry;
- nominal/native acquisition rate;
- observed timestamp cadence diagnostic;
- duplicate, missing-identity, missing-gaze, and bounds diagnostics;
- canonical sample table;
- pre-exclusion QC sample table;
- trial-quality summary;
- any later review/exclusion decisions as a separate record; and
- GazeForge version or exact development commit.

The archive should make it possible to reconstruct **what was transformed** without implying that the transformation validates the tracker.

## Continue the workflow

After the import/QC stage:

- use the [Event-model validation clinic](event-model-validation-clinic.md) if you intend to evaluate a learned event model;
- use [Research recipes](research-recipes.md) for static/dynamic AOIs and scanpaths;
- use the [Study lifecycle](study-lifecycle.md) to connect import, measurement, validation, freeze, and reporting;
- use [Publication readiness](publication-readiness.md) before analysis freeze or manuscript submission; and
- inspect the [Validation guide](validation-evidence-guide.md) before making device- or model-validity claims.

For deeper source-contract troubleshooting, continue with the [Real-data import clinic](data-import-clinic.md).
