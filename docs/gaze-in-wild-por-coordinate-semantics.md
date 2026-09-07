# Gaze-in-the-Wild point-of-regard coordinate semantics

This note freezes one narrow provenance result for the Gaze-in-the-Wild
processing pipeline. It does **not** promote the currently quarantined
`ProcessData.mat` sample into corpus-wide evidence and does not authorize an
empirical benchmark run.

## Verified first-party preprocessing convention

The pinned first-party repository is `RSKothari/Gaze-in-Wild` at commit
`52262d44e366a53369e10ca73c5f41daf0e8f1e5`. The reviewed file is
`DataExtraction/ReadData_function.m`, Git blob
`36d81839fb9f9eadb1274b998d2a8652fb0840ca`.

That exact source establishes the following chain:

1. `ETG.POR` is assigned from Pupil gaze-export fields `norm_pos_x` and
   `norm_pos_y`.
2. The y coordinate is transformed as `1 - y` for the MATLAB image-coordinate
   convention.
3. `ETG.POR` is interpolated but not multiplied by image dimensions in the
   first-party preprocessing path.
4. `ETG.SceneResolution` is stored separately as `[1920, 1080]` pixels.
5. `ProcessData.ETG.POR` is a direct interpolation of `ETG.POR`, while
   `ProcessData.ETG.SceneResolution` separately retains the image dimensions.

Therefore the first-party `ProcessData.ETG.POR` field is treated as
**normalized scene-image coordinates**, with its y axis already flipped to the
MATLAB convention. It is not treated as pixel-valued POR.

## GazeForge canonical conversion

`load_gaze_in_wild_mat()` converts the normalized coordinates into GazeForge's
canonical pixel representation only when the corresponding `ProcessData` file
supplies `ETG.SceneResolution`:

- `x_px = por_x * scene_width_px`
- `y_px = por_y * scene_height_px`

For the reviewed first-party processing convention, the stored scene resolution
is 1920 x 1080 pixels. Existing adapter tests separately require this conversion
and reject missing or invalid scene-resolution metadata.

The immutable provenance record is
`validation/evidence/gaze-in-wild/gaze-in-wild-por-coordinate-semantics-evidence-v1.json`,
with evidence fingerprint
`5eb245979385283571d6d9a5dda9a5d74dea6c00165bbe3a2587fcfa80e9adfb`.

## What this does not establish

This evidence deliberately leaves the following unresolved:

- recovery or verification of the authoritative full distributed dataset;
- exact equivalence between any recovered copy and the published distribution;
- corpus-wide empirical POR ranges;
- participant identity or participant-to-task mapping;
- a `TrIdx`-to-task-name ledger;
- verified reuse terms, analysis permission, or redistribution permission;
- per-file sampling-rate distribution;
- human-human agreement;
- participant-disjoint model validation;
- cross-dataset validation or a new empirical performance claim.

The 1920 x 1080 scene resolution is evidence about the first-party processing
metadata convention. It is not, by itself, evidence that every unrecovered
published file has been inspected or that an arbitrary `ProcessData.mat` is an
authoritative dataset copy.

## CI binding

The dedicated coordinate-provenance workflow downloads only the exact pinned
MATLAB source file, verifies its Git blob identity, rebuilds a metadata-only
probe, and binds that probe to the immutable evidence. No Gaze-in-the-Wild gaze
samples are downloaded, embedded, or redistributed by this gate.
