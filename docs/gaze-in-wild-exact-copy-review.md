# Gaze-in-the-Wild exact-copy review

GazeForge keeps recovered Gaze-in-the-Wild (GIW) copies quarantined until source authority, current dataset-file terms, and exact-copy identity are independently reviewed. The exact-copy review layer is the structured identity step between the [first-party readiness handoff](gaze-in-wild-first-party-readiness.md) and the existing recovery-quarantine exit gate.

## What this layer proves

A positive exact-copy decision proves one narrow proposition:

> The live-reverified recovery candidate has the same complete relative-path, byte-size, and SHA-256 manifest as a separate local reference tree whose provenance binding was independently reviewed.

The comparison covers **every regular file in both trees**. Matching filenames, a compatible MATLAB schema, a matching selected `ProcessData` file, equal file counts, or similar scientific structure are not sufficient on their own.

The reference tree must be physically separate and non-nested relative to the candidate. Symlinks and zero-byte files are already rejected by the shared exact inventory primitive. A local reference-provenance artifact is represented in the record by SHA-256 only; its contents and any private archive location are not serialized.

## Preconditions

`build_gaze_in_wild_exact_copy_review()` accepts only a validated first-party readiness record whose status is:

```text
ready_for_independent_exact_copy_review
```

It then live-reverifies the candidate recovery tree and ProcessData screen, requires the readiness record to bind those exact identities, builds a complete candidate inventory, and compares it with the independently supplied reference inventory.

A blocked readiness record cannot enter this layer.

## Two independent conditions

Exact-copy identity is true only when both conditions hold:

1. **Complete manifest equality** — all relative paths, byte sizes, and SHA-256 digests match.
2. **Reviewed reference binding** — a human reviewer confirms that the separate local reference tree is the copy linked to the previously reviewed source/provenance evidence.

`review_gaze_in_wild_exact_copy_record()` derives the result deterministically. A human cannot override a manifest mismatch by setting the reference-binding decision to true.

Possible decisions are:

- `pending_review`
- `verified_against_reviewed_reference_manifest`
- `not_verified`

## Fresh live verification

A serialized positive record is not sufficient for downstream use. `verify_gaze_in_wild_exact_copy_review()` re-inventories both current trees, re-hashes the local provenance artifact, rechecks the readiness lineage, and only then returns an ephemeral freshly validated object.

Changes to the candidate tree, reference tree, provenance artifact, recovery record, candidate screen, or readiness record therefore invalidate the downstream binding.

## Quarantine-exit handoff

`bind_verified_exact_copy_review_to_quarantine_exit()` can copy the exact-copy result into an existing **pending** `GazeInWildQuarantineExitAuthorization` only when the structured review:

- is positive;
- has been freshly live-revalidated; and
- binds the same recovery record, recovery tree, and candidate inventory.

The returned quarantine-exit record remains `decision="pending"`. Source authority, rights, analysis-use permission, redistribution terms, and the final quarantine-exit decision remain separate manual controls in the existing gate.

### Structured binding is mandatory at final exit validation

The pending handoff is not a reusable proof token. If a reviewer later promotes the quarantine-exit decision to `authorized`, `validate_gaze_in_wild_quarantine_exit_authorization()` must be given the exact-copy review record plus the live readiness record, candidate screen, separate reference tree, and reference-provenance artifact. The validator reruns `verify_gaze_in_wild_exact_copy_review()` and requires the resulting review fingerprint to match the canonical fingerprint carried by `exact_copy_identity_evidence`.

An authorized quarantine exit therefore cannot be validated from a free-text statement such as “candidate manifest matched authoritative copy identity,” nor from a copied SHA-256 string without the live comparison inputs. Candidate-tree, recovery-record, inventory, and audit-template validation alone are insufficient once `exact_copy_identity_verified=True`.

The JSON-only source-candidate CLI propagates the same live proof contract through `quarantine-exit-validate`, `authorization-apply`, and `lineage`. For a promoted exact-copy identity these commands accept `--exact-copy-review`, `--readiness-record`, `--candidate-screen`, `--reference-root`, and `--reference-provenance`; omitting the required live inputs causes the validator to fail closed rather than treating the stored fingerprint as reusable proof.

The validated state remains ephemeral and is not serialized. Reloading or editing an authorized exit record requires the complete structured exact-copy verification again before `require_authorized_gaze_in_wild_quarantine_exit()` will allow the downstream source-audit authorization boundary to use it.

## Claims that remain prohibited

Even after a positive exact-copy review, this layer does **not** establish or create:

- historical-original distribution equivalence;
- quarantine-exit authorization;
- source-audit readiness or execution;
- participant/task mapping;
- coordinate semantics;
- authoritative sampling cadence;
- separate `LabelData` recovery or independent-labeller recoverability;
- human-human agreement;
- participant-disjoint model validation;
- cross-dataset performance;
- GP3 validity; or
- Frozen Evidence performance claims.

A positive record therefore means **byte-manifest identity to one reviewed reference copy**, not that the complete GIW empirical benchmark has been scientifically authorized or validated.
