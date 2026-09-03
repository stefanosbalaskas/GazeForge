# Gaze-in-the-Wild benchmark candidate

GazeForge treats **Gaze-in-the-Wild** (Kothari et al., 2020) as a candidate native,
human-labelled event benchmark for head-free naturalistic gaze. It is scientifically useful because
its event annotations were produced by trained human labellers rather than by tracker software.

## Evidence profile

The primary paper reports:

- 19 participants performing naturalistic tasks;
- binocular Pupil Labs eye-tracking glasses acquired at 120 Hz;
- five trained annotators;
- more than 140 minutes of hand-labelled gaze;
- fixation, saccade, pursuit, blink, and vestibulo-ocular-reflex (VOR) events;
- uncertain regions left unlabelled; and
- samples with eye-tracker confidence below 0.3 treated as unusable/unlabelled.

The paper is available at `https://doi.org/10.1038/s41598-020-59251-5`.

A public event-evaluation implementation independently documents the distributed MATLAB layout:
`LabelData` contains `T`, `Labels`, and `LbrIdx`; paired `ProcessData` files contain `ETG.POR` and
`ETG.Confidence`. Its published event-code conversion corresponds to fixation, pursuit, saccade,
blink, and VOR.

## Sampling-rate provenance

GazeForge does **not** hard-code the analysis sampling rate from a secondary benchmark table.

The primary paper describes 120 Hz acquisition hardware, while at least one secondary benchmark
summary describes a processed Gaze-in-the-Wild copy at a different cadence. Therefore
`load_gaze_in_wild_mat()` infers the actual analysis rate from consecutive `LabelData.T` timestamps
for every recording. The published 120 Hz value is retained separately as hardware provenance.

Any future resampled benchmark must retain all three concepts separately:

1. published acquisition/hardware rate;
2. inferred source-file cadence; and
3. requested derived analysis rate.

## Adapter guardrails

`load_gaze_in_wild_mat()` and `load_gaze_in_wild_directory()` deliberately enforce the following:

- `LabelData.T` must be finite and strictly increasing;
- label and gaze streams must have compatible lengths;
- filename labeller ID and `LabelData.LbrIdx` must agree when both are present;
- confidence below the configurable threshold (default 0.30) becomes tracking loss;
- participant identity is `__unresolved__` unless supplied explicitly;
- directory loading refuses mixed labellers unless one labeller is selected;
- raw point-of-regard values are retained but their coordinate unit is marked **unverified**; and
- unit-sensitive cross-dataset kinematic modelling remains blocked until that coordinate basis is
  independently audited.

Label-only loading is supported. This is useful for event-level human-human comparisons even when
paired process data are unavailable.

## What this benchmark can support

After the authoritative data copy and identity structure are audited, Gaze-in-the-Wild can support:

- native-file human-labelled event evaluation;
- labeller-to-labeller sample and event agreement;
- fixation/saccade/pursuit/blink/VOR event-level metrics;
- naturalistic head-free generalisation tests; and
- sensitivity to annotator and task context.

It does **not** by itself establish validity for Gazepoint GP3 recordings. The hardware, head-motion
conditions, coordinate representation, and sampling characteristics differ. Its role is complementary
external evidence for human-labelled low-rate/naturalistic event classification.

## Distribution policy

GazeForge does not bundle the raw corpus. The historical distribution location and current dataset
reuse terms must be verified before any automated downloader or redistributed fixture is added.
