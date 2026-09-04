# Hollywood2EM source audit

GazeForge treats **source identity** as a separate scientific gate from parsing. The Hollywood2EM
adapter can read an ARFF file without proving that the local copy is the authoritative snapshot,
that observer identities are mapped correctly, that `x`/`y` are in comparable units, or that the
current reuse terms permit the intended analysis. Frozen cross-dataset evidence should therefore
use an audited source manifest rather than a bare loader call.

## Current source-resolution checkpoint

A dated public-source resolution pass is recorded in
[`hollywood2-source-resolution.md`](hollywood2-source-resolution.md) and in the machine-readable
checkpoint `validation/protocols/hollywood2-source-resolution-2026-09-04.json`.

That checkpoint establishes the canonical GIN distribution identifier from the authoritative
publication and later replication material, but it does **not** claim that an exact current copy has
been retrieved, fingerprinted, or licensed for the intended analysis. Repository-level analysis-use
and redistribution terms, participant/trial mapping, and coordinate units therefore remain blocked
until an exact obtained copy is reviewed. The article's CC BY 4.0 license is not silently promoted
to the dataset files.

## What the audit certifies

`Hollywood2SourceAuditSpec` binds each expected ARFF file to:

- a safe relative path;
- SHA-256 digest and byte size;
- an explicit participant identity;
- an explicit trial identity;
- a pinned source revision;
- the source of the reviewed reuse terms;
- analysis-use permission, recorded separately from redistribution permission;
- the evidence used to verify the coordinate unit; and
- the evidence used to verify the participant mapping.

The empirical audit then requires an **exact ARFF inventory match**, re-hashes every file, checks the
native sampling rate, loads both `handlabeller_1` and `handlabeller_final`, and verifies that the two
annotation streams refer to exactly the same participant/trial/timestamp/gaze samples. Only after
all gates pass does it stamp the returned `GazeFrame` with a deterministic source-audit report
fingerprint.

This is a provenance artifact, not a performance result. It does not calculate model accuracy and it
does not turn analysis permission into permission to redistribute the raw dataset.

## Non-executable template

The repository contains:

```text
validation/protocols/hollywood2-source-audit-template.json
```

It intentionally has `dataset_status: "template"`, an empty file inventory, and unverified reuse,
coordinate, and participant-mapping fields. `audit_hollywood2_source()` refuses to certify data from
that template. Replace the placeholders only after auditing an authoritative local dataset copy.

A completed file entry has this shape:

```json
{
  "path": "test/example.arff",
  "sha256": "<64 hex characters>",
  "bytes": 123456,
  "participant_id": "P01",
  "trial_id": "movie-001"
}
```

Paths are interpreted relative to `ground_truth/` when that directory exists. Absolute paths,
parent traversal, duplicate paths, unresolved observer identifiers, and duplicate
participant/trial identities are rejected.

## Python workflow

```python
from gazeforge.hollywood2_audit import (
    audit_hollywood2_source,
    load_audited_hollywood2_directory,
    load_hollywood2_source_audit_spec,
)

spec = load_hollywood2_source_audit_spec("hollywood2-source-audit.json")
audit = audit_hollywood2_source("/path/to/hollywood2_em", spec)

expert = load_audited_hollywood2_directory(
    "/path/to/hollywood2_em",
    spec,
    annotator="expert",
)
```

The resulting metadata includes the source-audit report fingerprint, specification fingerprint,
source-manifest fingerprint, pinned revision, reuse status, coordinate-verification basis, and
participant-mapping basis. These are the identities that should accompany future frozen
Hollywood2EM sensitivity and Lund↔Hollywood2 cross-dataset reports.

## Scientific boundary

Passing this audit would close **infrastructure** for authoritative-copy verification. It would not
mean that GazeForge currently possesses or redistributes Hollywood2EM, and the bundled template is
not evidence that the external dataset has been audited. The open empirical roadmap remains:

1. obtain and independently verify the authoritative current data copy and reuse terms;
2. populate and review the exact file/identity manifest;
3. run this audit and freeze its fingerprinted provenance report;
4. freeze student-vs-expert annotation sensitivity separately; and
5. only then run and review Lund↔Hollywood2 leave-one-dataset-out modelling.

Any 60 Hz Hollywood2EM result remains **derived from native 500 Hz recordings**, not native 60 Hz or
GP3-specific validation.
