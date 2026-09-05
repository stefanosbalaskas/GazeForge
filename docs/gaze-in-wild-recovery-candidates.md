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

## Reviewed secondary recovery leads

The secondary-lead provenance probe deliberately distinguishes two kinds of evidence that must not be collapsed into a recovered authoritative copy.

At pinned `Morris88826/awesome-eye-data` commit `4c6a58ef5be5693e08adac33e8768a3b88ddf8ac`, the repository describes itself as a collection unified under a common format and advertises processed Gaze-in-the-Wild material through an external Google Drive folder. Its documented processed layout uses chunked annotation CSV files and MP4 video clips. The pinned repository tree does not expose official-layout `ProcessData`/`LabelData` paths. GazeForge therefore classifies this lead as `external_transformed_collection_advertisement`; the external folder contents are not treated as obtained or audited by this probe, and equivalence to the original distribution remains unverified.

At pinned `George614/edit_distance_gpu` commit `01711b11556c271a7a15e566935089bb2775121b`, `levenGPU_demo.py` and `levenSequential.py` reference `LabellerIdx_7_PrIdx_1_TrIdx_1.mat` and `LabellerIdx_8_PrIdx_1_TrIdx_1.mat` through local paths. Those `.mat` files are not repository-resident at the pinned tree. GazeForge therefore classifies this lead as `local_path_reference_only`. The filenames establish a provenance lead only; they do not recover two independent annotation streams or make human-human agreement eligible.

The reviewed live-probe contract is bound to SHA-256 fingerprint `89714d8ab6dee18385f27cf609e99bd857048898aee699cc38ee3c7a195ad9dd`. The corresponding frozen secondary-lead evidence record is bound to SHA-256 fingerprint `e312079108f8b50ddedd6f361272218fc8665c880b147797aee5bb434ebc8c29`.

## Quarantine exit is a separate evidence transition

A recovery review cannot be edited into an authoritative record. Instead, `gazeforge.gaze_in_wild_quarantine_exit` creates a second, fingerprinted decision record that is allowed to refer back to the quarantined identity without rewriting it.

Before a pending quarantine-exit record can even be created, GazeForge requires all three of these identities to agree:

1. the specialized GIW recovery review and its exact recovery-tree fingerprint;
2. the generic candidate inventory used by the source-review pipeline; and
3. the non-empirical GIW source-audit template compiled from that candidate.

The specialized recovery review and generic candidate inventory must contain the **same ordered path / SHA-256 / byte manifest**. The audit template must contain the exact `Candidate inventory fingerprint: ...` note generated by the candidate-review compiler. A changed file, different candidate inventory, or different audit template invalidates the transition.

An exit decision may be `pending`, `authorized`, or `denied`. An `authorized` decision additionally requires independent affirmative evidence for:

- source authority;
- exact-copy identity;
- dataset-file rights;
- current reuse terms and their source;
- analysis-use permission; and
- reviewed redistribution status and evidence.

The authorized exit's authoritative source, source revision, and reuse-terms source must match the exact audit template. The later generic source-audit authorization must also agree with the exit's redistribution status.

`transformed_secondary_collection` and `labeller_provenance_only` candidates are deliberately **not eligible for an authorized exit**. If later evidence establishes that material is actually a different, authoritative exact copy, it must be inventoried again under the newly supported identity rather than promoting the old secondary-lead record.

Even an authorized exit remains a **review-only transition**. It does not execute the source audit and does not establish participant mapping, coordinate units, sampling cadence, independent labeller recoverability, human-human agreement, participant-disjoint model validation, cross-dataset performance, GP3 validity, Frozen Evidence performance, or any empirical metric.

## CLI workflow

The candidate CLI exposes the transition explicitly:

```text
gazeforge-source-candidate quarantine-exit \
  --recovery-review recovery.json \
  --inventory inventory.json \
  --template gaze-in-wild-audit-template.json \
  --root /path/to/candidate \
  --output quarantine-exit.json
```

After independent review, edit the exit record without changing its bound fingerprints, set the decision and evidence fields, and revalidate the complete current tree:

```text
gazeforge-source-candidate quarantine-exit-validate \
  --quarantine-exit quarantine-exit.json \
  --recovery-review recovery.json \
  --inventory inventory.json \
  --template gaze-in-wild-audit-template.json \
  --root /path/to/candidate
```

For Gaze-in-the-Wild, `authorization-apply` and `lineage` then require `--quarantine-exit`, `--recovery-review`, and `--inventory` in addition to the existing template and generic authorization inputs. The CLI revalidates the current candidate tree and complete exit binding before materializing the empirical **source-audit specification**. Materialization permits audit execution only; it is not a passed source audit.

## What must happen before empirical use

The software transition is now explicit, but the real-world evidence requirements are unchanged. A candidate can leave quarantine only after independent evidence establishes authoritative source provenance, exact-copy identity, and applicable dataset-file reuse terms. The later source-audit workflow must still establish participant/trial/task interpretation, coordinate semantics, timestamp-derived cadence, and annotation-stream provenance sufficient for the intended analysis.

Accordingly, the current recovery evidence still does **not** establish:

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

The [source audit](gaze-in-wild-source-audit.md) is the later empirical gate for an authoritative copy whose identity, interpretation, and reuse basis have actually been reviewed. Recovery-candidate quarantine and its explicit exit decision sit strictly before that source audit and cannot bypass it.
