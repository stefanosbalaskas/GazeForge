# Native 60 Hz expert-event validation

GazeForge now includes a dedicated intake path for a **genuinely native-rate human-labelled eye-event corpus**. This is the infrastructure required for the next evidence gate after the derived-60-Hz Lund2013 benchmark.

The feature does **not** create GP3-specific validity by itself. No native GP3 expert-labelled event dataset is bundled with GazeForge, and no native GP3 performance result should be reported until a real empirical corpus has been collected or independently obtained, audited, and frozen through this workflow.

## Why a separate native intake is necessary

Resampling a 500 Hz expert-labelled benchmark to 60 Hz is useful for studying lower temporal resolution, but it is not equivalent to recording and annotating gaze natively at 60 Hz. Native validation may differ because of tracker noise, missingness, timestamp behaviour, calibration error, filtering, participant movement, experimental task, and device-specific acquisition characteristics.

The native intake therefore refuses to infer that evidence strength from a filename or a user-supplied `sampling_rate_hz=60` argument. It verifies the rate from the sample timestamps and records the evidence origin explicitly.

## Required sample table

The benchmark table must provide one human event label per sample for the selected annotation stream. At minimum it must map to these canonical fields:

| Canonical field | Meaning |
| --- | --- |
| `participant_id` | participant identity used for leakage-safe held-out folds |
| `trial_id` | recording, stimulus, or trial identity |
| `timestamp_ms` | native sample timestamp in milliseconds |
| `x_px` | horizontal gaze coordinate in pixels |
| `y_px` | vertical gaze coordinate in pixels |
| `event_label` | manual human event label |

An optional `annotator_id` column is supported for long-format multi-annotator data. If more than one annotation stream is present, the benchmark refuses to continue until one annotator is selected explicitly.

For angular I-VT, the table must additionally provide invariant geometry within every participant/trial:

- `screen_width_px`;
- `screen_height_px`;
- `screen_width_physical`;
- `screen_height_physical`;
- `view_distance_physical`.

Physical screen dimensions and viewing distance must use the same unit.

## Evidence specification

Copy the repository template:

```text
validation/protocols/native-60hz-expert-event-template.json
```

The template deliberately contains:

```json
"dataset_status": "template"
```

GazeForge will refuse to produce an empirical benchmark report while that value remains `template`. Change it to `empirical` only after the source, license/reuse status, tracker, expert annotation protocol, and column mapping describe a real dataset.

A specification records:

- dataset name and version;
- authoritative source/provenance;
- reuse or distribution status;
- tracker/device model;
- declared native sampling rate;
- allowed sampling-rate tolerance;
- annotation origin and number of human annotators;
- source-to-canonical column mapping;
- explicit analysis-excluded labels;
- free-text methodological notes.

The specification itself receives a deterministic SHA-256 fingerprint inside the frozen report.

## Run the benchmark

Pixel-velocity I-VT example:

```bash
gazeforge native-event-benchmark \
  expert-events.csv \
  native-gp3-spec.json \
  --annotator expert-a \
  --ivt-threshold-px-s 700 \
  --n-splits 5 \
  --output validation/gp3-native-expert-a.json
```

Angular I-VT example when screen and viewing geometry are available:

```bash
gazeforge native-event-benchmark \
  expert-events.csv \
  native-gp3-spec.json \
  --annotator expert-a \
  --ivt-threshold-deg-s 45 \
  --n-splits 5 \
  --output validation/gp3-native-expert-a.json
```

The angular threshold above is only an example. GazeForge intentionally provides **no default I-VT threshold** for a new native-device benchmark. The protocol should justify and lock the threshold before final evaluation rather than silently inheriting a value tuned or motivated by a different dataset.

## Native-rate verification

Before any model is evaluated, GazeForge:

1. renames source columns using the explicit specification;
2. selects one human annotation stream if required;
3. rejects missing participant/trial identities or missing manual labels;
4. rejects duplicate participant/trial/timestamp sample keys;
5. infers the global sampling rate from timestamps;
6. infers a median sampling rate separately inside every participant/trial;
7. checks all observed rates against the declared native rate and tolerance;
8. refuses the benchmark if the data are rate-incompatible;
9. records `resampling: null` and `native_rate_verified: true` only after these checks pass.

This is intentionally stricter than merely attaching a 60 Hz metadata field to a table.

## Matched model evaluation

Once the evidence intake passes, the existing GazeForge model-comparison engine is used unchanged:

- participant-held-out `GroupKFold` splits;
- identical held-out rows for I-VT, RandomForest, and ContextMLP;
- fresh learned-model fitting inside every training fold;
- accuracy, balanced accuracy, and macro-F1;
- calibration metrics for probabilistic models;
- event-level precision, recall, F1, temporal IoU, onset error, offset error, and duration error;
- descriptive matched-fold model differences without treating folds as independent experimental replicates.

The resulting benchmark report stores the source-table fingerprint, optional source-file SHA-256, specification fingerprint, observed group rates, exclusions, label counts, comparison design, and deterministic report fingerprint.

## What the workflow can establish

A successfully frozen native benchmark can support claims about the **declared tracker/device, task domain, reference labels, and study population represented by that corpus**.

It does not automatically establish:

- generalization to other trackers;
- generalization to other 60 Hz devices;
- equivalence between manually labelled and vendor-generated events;
- superiority of learned models across all event definitions;
- validity for tasks or participant populations absent from the benchmark.

Those limits are inserted directly into the report protocol.

## Recommended first GP3 validation corpus

For the first GP3-class evidence tranche, the strongest design would include:

- multiple participants rather than repeated trials from only a few individuals;
- at least two trained/expert annotators for a substantial common subset;
- fixation, saccade, and explicit missing/noise categories, with any additional event classes defined before annotation;
- diverse static and dynamic tasks rather than one homogeneous stimulus;
- preserved raw GP3 exports alongside the manually labelled analysis table;
- documented calibration, screen geometry, viewing distance, and recording software/version;
- participant-disjoint model evaluation;
- human-human agreement reported alongside model-human performance;
- a frozen protocol and source-data fingerprint before publication claims are made.

The current implementation prepares GazeForge for that corpus without fabricating the empirical result that only real native data can provide.
