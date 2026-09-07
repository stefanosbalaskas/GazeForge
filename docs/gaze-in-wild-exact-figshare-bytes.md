# Gaze-in-the-Wild exact Figshare bytes

## Status

The exact original-publication Figshare distribution bytes are now verified for the two deposits used by the Gaze-in-the-Wild publication chain:

- **ProcessData** — 68 files, 2,384,573,418 bytes, DOI `10.6084/m9.figshare.11673645.v1`;
- **LabelData** — 50 files, 28,725,824 bytes, DOI `10.6084/m9.figshare.11673696.v1`.

Together this is **118 files / 2,413,299,242 bytes**.

The discovery verification completed in workflow run `34164582679`, job `101872991996`, on exact head `39ec2546065250c1aee29631a0ad5abe0366541e`. Before byte acquisition, fresh public Figshare metadata matched the already-reviewed stable metadata fingerprint `2fc9b441f90dae01e1ef41918d61924458f7cd0e0556021db3daa3a6732251f4`.

Each file was streamed individually, checked against the frozen file size and MD5, hashed with SHA-256, inspected as a MATLAB container, and deleted immediately. All 118 files matched on the first download attempt. No raw MAT file was retained or uploaded as a workflow artifact.

## Frozen identities

The reviewed exact-byte evidence fingerprint is:

`dbf277d698266fe53e337a15fc342e9af1835460d2bcc69c3992635de8fa0a00`

The discovery probe fingerprint is:

`96645a517bb5aec84aec1920683625c9a5ca47f609afd8fd9725fb9b77f8bb3d`

The workflow artifact ZIP SHA-256 is:

`123f705f79aa5de261d73a8b1347646a681c3a45dca509933c9aa72d2bc96798`

A transport-independent content/schema identity is also frozen. It excludes download-attempt metadata but includes every file's Figshare ID, filename, byte count, MD5, SHA-256, MATLAB schema, and raw-retention flag:

`8d36884daf76e26ded3d31c32bd334bf8f358b49efdb7accbb20c6c569abdda0`

The corresponding deposit-level stable identities are:

- ProcessData: `7e48396fcfe30e2170708c9d5910caea785ceff1dd06b0455e5715a01e52d3ea`;
- LabelData: `9ffbbab106bbd6f5a6ac8d7dd1e666ab70f3df486a1057b4ff690c82fae2a1ec`.

## Container observations

All 68 ProcessData files are MATLAB Level-5-compatible and expose a 1×1 `ProcessData` struct plus a MATLAB `__function_workspace__` payload. Thirteen exact top-level container-schema variants occur because the workspace byte-array length varies.

All 50 LabelData files are MATLAB Level-5-compatible and expose one 1×1 `LabelData` struct. Their top-level container schema is identical across all 50 files.

## Deliberate exclusion

`ProcessData_cleaned` (Figshare article `11673717`, DOI `10.6084/m9.figshare.11673717.v1`) was **not downloaded**. Its publisher description states that it was not published as part of the original publication, so it remains excluded from the original-publication source contract.

## What this closes

This tranche closes the previous uncertainty over whether the current official Figshare ProcessData and LabelData downloads match the frozen official distribution manifests at the byte level.

The repository validator binds the reviewed result to the earlier rights/provenance evidence, the fresh-metadata identity, exact workflow/run/job/head, discovery artifact digest, and the stable content/schema identities. The dedicated workflow can regenerate the full 118-file acquisition and must reproduce those stable identities.

## What this does not close

Exact distribution bytes do not establish semantic task identity or model validity. The following remain fail-closed:

- no universal `TrIdx` → task-name mapping;
- no complete per-file task mapping;
- no human–human agreement result;
- no participant-disjoint model validation;
- no cross-dataset performance result;
- no native Gazepoint GP3 validity claim;
- no quarantine exit;
- no new empirical performance claim.

These boundaries are enforced by the reviewed evidence validator and adversarial tests.
