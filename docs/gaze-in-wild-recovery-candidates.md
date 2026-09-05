# Gaze-in-the-Wild recovery candidate quarantine

GazeForge treats a **recovered Gaze-in-the-Wild candidate** as an object that may be fingerprinted and reviewed but **must not be interpreted as an authoritative empirical source merely because its filenames, directory structure, or MATLAB contents look plausible**.

This layer exists for the gap between discovering a possible copy and establishing the much stronger source-audit requirements needed for empirical use.

## What the quarantine records

`gazeforge.gaze_in_wild_recovery` can inventory a local candidate tree and record:

- every relative file path;
- exact byte size and SHA-256 identity for every file;
- extension counts;
- an exact tree fingerprint;
- a canonical review-record fingerprint;
- an explicit candidate kind; and
- a human-supplied provenance source and provenance note.

Every file role is forced to `unclassified`. A filename such as `PrIdx_1_TrIdx_1.mat` or `LabellerIdx_7_PrIdx_1_TrIdx_1.mat` is therefore retained as an identity-bearing path only. It is **not** promoted to a participant, trial, labeller, task, cadence, coordinate-system, annotation-stream, or rights claim.

## Supported candidate kinds

The review layer accepts only these deliberately non-authoritative states:

```text
unknown_recovered_copy
candidate_original_layout_unverified
transformed_secondary_collection
labeller_provenance_only
```

None means “authoritative dataset copy.” None changes the dataset-file rights state.

## Interpretation policy

A valid quarantine record requires all of the following:

```text
all_file_roles_are_unclassified = true
filename_identity_inference_permitted = false
matlab_schema_inference_permitted = false
license_inference_permitted = false
candidate_can_materialize_empirical_audit_spec = false
```

The validator fails closed if a record attempts to promote any of those fields, even when the modified record is re-fingerprinted.

Similarly, the scientific boundary remains closed for source authority, original-distribution identity, dataset-file rights, analysis permission, redistribution permission, participant/task mapping, coordinate units, sampling cadence, independently recoverable labeller streams, source-audit readiness, empirical-evidence eligibility, human-human agreement, participant-disjoint model validation, cross-dataset performance, GP3 validity, and Frozen Evidence performance claims.

## Candidate-tree integrity

The inventory rejects empty trees and symlinks. Files are sorted by safe relative path and hashed by content. `verify_gaze_in_wild_recovery_candidate_tree()` later re-inventories the local tree and requires exact equality with the reviewed manifest, so a changed, added, removed, or renamed file invalidates the reviewed identity.

A JSON review written by `write_gaze_in_wild_recovery_candidate_review()` must be stored **outside** the candidate tree. This prevents the review artifact from changing the very tree it fingerprints.

## Example review workflow

The following example demonstrates the quarantine boundary; it does not imply that GazeForge ships or has certified a Gaze-in-the-Wild dataset copy.

```python
from gazeforge.gaze_in_wild_recovery import (
    build_gaze_in_wild_recovery_candidate_review,
    validate_gaze_in_wild_recovery_candidate_review,
    verify_gaze_in_wild_recovery_candidate_tree,
    write_gaze_in_wild_recovery_candidate_review,
)

record = build_gaze_in_wild_recovery_candidate_review(
    "/local/path/to/unverified-candidate",
    candidate_kind="candidate_original_layout_unverified",
    provenance_source="secondary recovery lead",
    provenance_note="Unverified candidate retained for identity review only.",
)

validate_gaze_in_wild_recovery_candidate_review(record)
verify_gaze_in_wild_recovery_candidate_tree(
    "/local/path/to/unverified-candidate",
    record,
)
write_gaze_in_wild_recovery_candidate_review(
    record,
    "/separate/review/gaze-in-wild-candidate-review.json",
    candidate_root="/local/path/to/unverified-candidate",
)
```

The resulting record is a **quarantine identity**, not an empirical evidence artifact.

## What must happen before empirical use

A candidate can leave quarantine only through a separate, independently reviewed evidence transition. That later work would need authoritative source provenance and exact-copy identity, dataset-file analysis/reuse terms, participant/trial/task interpretation, coordinate semantics, timestamp-derived cadence, and annotation-stream provenance sufficient for the intended analysis.

Only after those requirements are established should a distinct source-audit specification be created and executed. The quarantine record itself is deliberately unable to manufacture that specification or satisfy an empirical gate.

Accordingly, this tranche does **not** create:

- an exact authoritative `ProcessData`/`LabelData` acquisition;
- dataset-file analysis or redistribution rights;
- exact participant or task mapping;
- a verified distributed-file sampling cadence;
- independently recoverable human-labeller streams;
- human-human agreement evidence;
- participant-held-out Gaze-in-the-Wild model validation;
- cross-dataset performance evidence; or
- Gazepoint GP3 validity.

## Relationship to the existing provenance layers

The [distribution availability evidence](gaze-in-wild-distribution-availability.md) establishes the historical first-party distribution identity while recording that an exact current compressed copy has not been obtained. It also quarantines secondary recovery leads and keeps dataset-file rights unresolved.

The [source audit](gaze-in-wild-source-audit.md) is the later empirical gate for an authoritative copy whose identity, interpretation, and reuse basis have actually been reviewed. Recovery-candidate quarantine sits strictly between those two stages and cannot bypass either one.
