# VISUS canonical AOI intake

GazeForge provides a source-audit-aware canonical intake step for VISUS dynamic AOI annotations.
The purpose of this layer is to connect a reviewed AOI extraction to the exact XML files already
verified by the VISUS source audit without pretending that GazeForge has parsed an authoritative
VISUS ViPER XML distribution that is not present in the repository.

## Why this layer exists

The published VISUS benchmark describes dynamic, axis-aligned AOI boxes stored in
ViPER-compatible XML and positioned at keyframes with interpolation between them. GazeForge's
core dynamic-AOI API is timestamp based. The canonical intake therefore provides a conservative
bridge from a separately reviewed frame-indexed extraction to `DynamicAOIKeyframe` objects.

The intake deliberately does **not** guess the historical XML schema. A caller first creates a
reviewable table from the authoritative copy using a documented extraction procedure, then passes
that table together with a verified `VisusSourceAuditRun`.

## Required table fields

Each row must contain:

- `source_path`: exact relative path of the audited AOI XML file;
- `stimulus_id`: audited VISUS stimulus identity;
- `annotation_stream_id`: audited annotation-stream identity;
- `frame_index`: integer video frame index;
- `aoi_id` and `label`: track and semantic identities;
- `xmin`, `ymin`, `xmax`, `ymax`: rectangular AOI geometry.

An optional `confidence` column may be supplied; otherwise confidence is set to `1.0` for the
manual reference geometry.

## Integrity gates

`prepare_visus_canonical_aoi_intake()` revalidates the source-audit report, specification, and
exact manifest fingerprints before touching the table. It then requires every source path to be an
audited `aoi_annotation` file and checks that the table's stimulus and stream identities match the
manifest record for that file.

By default every audited AOI annotation file must appear in the extraction. Duplicate
stimulus/stream/AOI/frame identities, non-integer frame positions, invalid boxes, changing semantic
labels within one track, and non-finite values are rejected. When the audited coordinate basis is
pixels, boxes must also remain within the audited video resolution.

## Frame-to-time conversion

The caller must state whether source frames are 0-based or 1-based. The intake uses the audited
VISUS video rate and computes

```text
timestamp_ms = (frame_index - frame_index_base) * 1000 / video_frame_rate_hz
```

The frame-index convention is never inferred from filenames or model output. The exact input table,
canonical output table, source-audit identities, source AOI files, frame convention, and conversion
basis are fingerprinted in the intake report.

## Downstream use

The returned `by_stream` mapping is already organised as
`annotation_stream_id -> stimulus_id -> list[DynamicAOIKeyframe]`. A verified curated stream can be
passed directly to the VISUS model-human validator. If an authoritative source audit later proves
that separately recoverable independent annotation streams exist, two such mappings can be passed
to the guarded VISUS human-human agreement runner.

## Claim boundary

Canonical intake is provenance and schema infrastructure. It does not establish model performance,
human-human reliability, or the existence of independent annotation streams. It also does not
validate the correctness of an external raw-XML parser; that extraction procedure remains an
explicit reviewed provenance input until an authoritative VISUS copy is available for direct parser
validation.
