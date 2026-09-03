# VISUS source audit

GazeForge treats VISUS as a promising native-60-Hz dynamic-AOI benchmark, but an API implementation or historical download link is not sufficient evidence for a frozen benchmark claim. `audit_visus_source()` creates an explicit boundary between a locally reviewed authoritative snapshot and later human/model dynamic-AOI evaluation.

## Published benchmark facts used by the contract

The 2014 benchmark paper describes 11 video scenarios and gaze from 25 participants. Gaze was recorded with a Tobii T60 XL at 60 Hz. The videos were reported at 25 fps and 1920×1080 pixels and were displayed on a 1920×1200 screen.

The published data suite contains video stimuli, exported gaze data, and dynamic AOI annotations. AOIs were represented as axis-aligned rectangular bounding boxes, stored in ViPER-compatible XML, with boxes placed at keyframes and linear interpolation between keyframes.

These published design facts are used as consistency checks. They do **not** substitute for verification of the exact current archive, current reuse terms, coordinate conventions, participant/stimulus identity mapping, or timestamp/frame-time conventions.

## Important annotation-provenance correction

The publication describes the AOI annotation as a manual process involving **two contributors**, but it does not describe two independent human-reference annotation streams. The first contributor performed the main annotation; the second contributor supplied additional annotations and refinements to the existing annotation.

GazeForge therefore keeps two concepts separate:

- `annotation_process_contributor_count=2` records the published annotation process;
- `independent_annotation_streams_verified` records whether a real audited source copy actually contains separately recoverable independent annotation streams suitable for human-human agreement.

The second flag defaults to `false`. A human-human dynamic-AOI agreement workflow must remain blocked unless at least two independently identified AOI streams per annotated stimulus are separately manifested and the independence claim has an explicit evidence basis.

Contributor count alone is not an agreement dataset.

## Exact source manifest

Every file in an empirical source audit is represented by a `VisusSourceFileRecord` containing:

- safe relative path;
- SHA-256 digest;
- byte size;
- role: `video`, `gaze`, `aoi_annotation`, or `other`;
- explicit stimulus identity for videos, gaze, and AOI annotations;
- explicit participant identity for gaze files;
- optional participant group;
- explicit annotation-stream identity for AOI XML files.

The audit compares the complete recursive local file inventory with the manifest. Missing files, unexpected files, byte-size changes, or digest changes fail the audit rather than producing a partially verified result.

## Empirical audit gates

An empirical `VisusSourceAuditSpec` must establish all of the following before `audit_visus_source()` succeeds:

1. current dataset/source identity and a concrete source revision or snapshot identity;
2. independently reviewed reuse terms and explicit permission for analysis;
3. redistribution status kept separate from analysis permission;
4. verified stimulus mapping covering the 11 published scenarios;
5. verified participant mapping resolving 25 participant identities in the gaze manifest;
6. verified coordinate-unit evidence;
7. verified timestamp/frame-time evidence;
8. exact local file identities;
9. AOI annotation coverage for the same manifested stimuli as video and gaze data.

The bundled template remains deliberately non-executable because these facts cannot be filled safely without a real authoritative copy.

## Deterministic provenance

A successful audit produces fingerprints for the complete source manifest, the specification, and the final audit report. The report also records role counts, stimulus and participant identities, participant groups when available, published acquisition metadata, and the observed annotation-stream inventory per stimulus.

`human_human_agreement_ready` is `true` only when independent annotation streams have been explicitly verified and every annotated stimulus has at least two manifested streams. Otherwise it remains `false` even though the published annotation process involved two people.

## Protocol relationship

`validation/protocols/visus-dynamic-aoi-candidate.json` remains a candidate protocol. It now requires a successful source audit and no longer treats the published two-contributor annotation process as evidence of two independent annotators. Annotator-as-reference sensitivity is conditional on independently verified source streams.

The source-audit template is:

```text
validation/protocols/visus-source-audit-template.json
```

## Evidence status

This infrastructure does not establish that the historical VISUS distribution is currently downloadable, does not establish current reuse permission, and does not produce human-human or model-human performance metrics. Those empirical tasks remain open until a real source snapshot is independently reviewed and frozen through the evidence workflow.