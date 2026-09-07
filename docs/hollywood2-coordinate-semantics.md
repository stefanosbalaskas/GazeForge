# Hollywood2EM coordinate semantics

GazeForge treats coordinate-unit provenance as a separate scientific gate from source identity, participant identity, reuse rights, and cross-dataset modelling. This page records the evidence supporting the narrow conclusion that the pinned Hollywood2EM ground-truth ARFF `x`/`y` fields use **pixel coordinates**.

## Verified conclusion

For the canonical Hollywood2EM GIN source at commit
`870fa6d6209c9085260918d61433a0a2c70fd497`, the ARFF gaze coordinates are verified as **pixels**.

The immutable combined evidence record is:

`validation/evidence/hollywood2/hollywood2-coordinate-semantics-evidence-v1.json`

Evidence fingerprint:

`f08f6f01b6f4eac422572e8e13d7dff794101769ad56691a93464c7032515806`

This conclusion is intentionally narrower than a cross-dataset-validity claim.

## Evidence chain

Three independently checkable bindings support the coordinate-unit conclusion.

### 1. Exact author implementation convention

The eye-movement-classification implementation maintained by the Hollywood2EM authors is pinned to commit:

`MikhailStartsev/deep_em_classifier@9a345a37aab47ac6780ce0d4b5798cc15291c75b`

Its reviewed README Git blob is:

`112f5f2a235f059ac2394db3180956474e644c06`

That exact implementation documents the ARFF input convention as:

- `time` in microseconds;
- `x` and `y` as on-screen or stimulus-relative coordinates in pixels;
- geometry metadata keys `width_px`, `height_px`, `width_mm`, `height_mm`, and `distance_mm` for conversion between pixels and visual angle.

The coordinate workflow retrieves that exact README, checks its Git blob identity, and fails if the reviewed unit/metadata convention is no longer present.

### 2. Pinned GIN headers match the author convention

A metadata-only probe inspected every pinned Hollywood2EM ground-truth ARFF header and stopped at the first `@data` marker. It did not read or embed gaze rows and did not emit source filenames.

Reviewed exact-head run:

- workflow: `34064095480`
- reviewed head: `b8be8017d0eddcd6946ba212b2f2335094a365f8`
- artifact: `9998400863`
- artifact ZIP SHA-256: `e8cd5f26a178b079a9600f8b90d054ff85334622df7bd43438cf74a7ac64a40d`
- live-probe fingerprint: `d3ed5f9bc005ec435c34df1aa8fb0cb30599d49dff4835085f00114d43e185bd`

The reviewed probe found:

- 697 ARFF files;
- 697/697 with the required gaze schema `time, x, y, confidence, handlabeller_1, handlabeller_final`;
- 697/697 with all five author-convention geometry keys;
- 697 occurrences each of `width_px`, `height_px`, `width_mm`, `height_mm`, and `distance_mm`;
- 24 distinct geometry metadata signatures covering all 697 files;
- `distance_mm = 600` in every reviewed geometry signature;
- pixel/`px` vocabulary in all 697 headers;
- no degree/visual-angle wording in the headers themselves.

The header-only probe deliberately reports `coordinate_unit_verified=false`. It supplies direct source corroboration; the combined evidence validator is the layer that joins the pinned source headers to the independently pinned author convention.

### 3. Existing authoritative Hollywood2EM evidence

The previously frozen authoritative ground-truth evidence is bound by fingerprint:

`d5375b8768984ef76da02597c55b225aaff4088fd24698c0d53363e2df6b20ea`

That record independently binds the same canonical GIN commit and author implementation and records the ARFF coordinate source unit as pixels. The new coordinate record therefore does not replace earlier evidence; it adds a dedicated, header-level corroboration and a fail-closed fresh-live validator.

## What this does not establish

Verifying `x`/`y` as pixels does **not** establish any of the following:

- participant identity or filename-token-to-participant mapping;
- participant-disjoint Hollywood2EM generalisation;
- exact annotation-repository licence text or identifier;
- new permission for analysis or redistribution;
- correctness of a particular pixel-to-visual-angle conversion in a downstream analysis;
- comparability with Lund2013 or another dataset without an explicit geometry-normalisation protocol;
- a Lund↔Hollywood2 leave-one-dataset-out result;
- native GP3/60 Hz validity;
- any new empirical performance claim.

Accordingly, `pixel_to_visual_angle_conversion_verified`, `participant_identity_mapping_verified`, `participant_disjoint_validation_created`, `cross_dataset_validation_created`, and `unit_sensitive_cross_dataset_modelling_executed` remain false in the coordinate evidence record.

## Annotation sensitivity remains a separate result

The authoritative Hollywood2EM ground-truth evidence also contains a frozen first/student-to-expert-corrected label comparison across 3,871,580 samples: 3,580,265 unchanged and 291,315 changed, for raw equality `0.9247555261676111`.

That comparison is **annotation sensitivity from a sequential correction process**, not independent human-human reliability. Coordinate verification does not change that interpretation.
