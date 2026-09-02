# Adapters and validation

## Gazepoint

`adapt_gazepoint_samples()` converts declared Gazepoint-style columns to the canonical schema.
It defaults to fractional screen coordinates and seconds because those are common Gazepoint export
semantics, but every relevant source column and unit can be overridden explicitly.

The adapter requires `screen_size_px` when coordinates are normalized. It never guesses the screen
resolution.

## Existing Python ecosystem tables

`adapt_processed_table()` is the bridge for eyeprocesspy, gpbiometricspy, and other preprocessed
tables. The caller supplies the participant, trial, time, x, and y columns explicitly. This avoids
coupling GazeForge to unstable upstream private column conventions.

## Leakage-safe validation

`grouped_event_cross_validate()` uses `GroupKFold` and fits a fresh event classifier in every fold.
The default grouping unit is `participant_id`.

`assert_no_group_leakage()` can additionally be applied to participant, stimulus, session, or other
grouping columns before any train/test evaluation.
