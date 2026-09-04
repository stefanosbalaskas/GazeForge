# VISUS source-inventory scaffold

`build_visus_source_audit_scaffold()` and the `gazeforge-visus scaffold` command help start a VISUS source audit from a local candidate dataset tree **without pretending that file names or extensions establish scientific provenance**.

The scaffold is deliberately non-empirical. It inventories exact files and produces a JSON object that can later be manually reviewed into a `VisusSourceAuditSpec`, but it does not verify that the copy is authoritative, licensed for analysis, correctly mapped, or suitable for benchmark claims.

## Command-line use

Keep the generated audit template outside the candidate source tree:

```bash
gazeforge-visus scaffold \
  /path/to/candidate-visus-copy \
  /path/to/review/visus-source-audit-template.json
```

The command recursively records each regular file's:

- relative path;
- byte size;
- SHA-256 digest.

It also computes a deterministic fingerprint over that exact inventory. The fingerprint is printed by the command and recorded in the template notes for review provenance.

## What the scaffold intentionally does not infer

Every discovered file is written as:

```json
{
  "role": "other",
  "stimulus_id": null,
  "participant_id": null,
  "annotation_stream_id": null
}
```

This remains true even when a filename ends in `.avi`, `.tsv`, or `.xml`. Extension-based guesses are not enough to establish that a file is a VISUS video, gaze recording, AOI annotation, particular stimulus, particular participant, or independent annotation stream.

The generated specification also remains:

```json
{
  "dataset_status": "template",
  "reuse_terms_verified": false,
  "analysis_use_permitted": false,
  "coordinate_unit": "unverified",
  "coordinate_unit_verified": false,
  "timestamp_basis_verified": false,
  "independent_annotation_streams_verified": false
}
```

Placeholder source/version/license fields are intentionally unresolved. `audit_visus_source()` therefore refuses the generated file until a researcher has independently reviewed and replaced the template metadata and scientific mappings.

## Manual review required before empirical audit

Before changing `dataset_status` to `empirical`, review and document at least:

1. the authoritative source and exact source revision or distribution identity;
2. current reuse terms and whether analysis use is permitted;
3. redistribution status separately from analysis permission;
4. which exact files are videos, gaze files, AOI annotations, or other assets;
5. explicit stimulus IDs for all videos/gaze/AOI files;
6. explicit participant IDs for gaze files;
7. explicit AOI annotation-stream IDs for AOI files;
8. participant and stimulus mapping evidence;
9. the coordinate unit and its evidence basis;
10. the frame-time/timestamp basis and its evidence basis;
11. whether any separately recoverable AOI streams are genuinely independent.

The historical VISUS paper reports two contributors to one AOI annotation process. That alone does not justify `independent_annotation_streams_verified=true`.

## Snapshot-safety rules

The scaffold rejects symbolic links because the exact source identity should not silently depend on targets outside the reviewed tree. It also rejects zero-byte files because the current exact audit-file contract requires positive byte sizes.

The scaffold JSON itself must be written outside the inventoried source directory. Otherwise writing the specification would change the file tree it claims to describe.

If any source file later changes, rebuilding the scaffold changes that file's SHA-256 and the deterministic inventory fingerprint. This provides a clean checkpoint before manual provenance review.

## Python API

```python
from gazeforge.visus_scaffold import (
    build_visus_source_audit_scaffold,
    write_visus_source_audit_scaffold,
)

scaffold = build_visus_source_audit_scaffold("candidate-visus")
print(scaffold.file_count)
print(scaffold.inventory_fingerprint_sha256)
write_visus_source_audit_scaffold(
    scaffold,
    "review/visus-source-audit-template.json",
)
```

Generating this scaffold does **not** complete the roadmap task to obtain and verify an authoritative VISUS copy. It only makes the subsequent source review reproducible and less error-prone.
