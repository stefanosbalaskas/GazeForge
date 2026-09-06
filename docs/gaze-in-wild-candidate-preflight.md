# Gaze-in-the-Wild candidate ProcessData preflight

This governance layer screens one **explicitly selected file** inside a quarantined Gaze-in-the-Wild recovery candidate against GazeForge's ProcessData structural contract.

It exists to answer one narrow question: *does this exact reviewed file have the structure required by the ProcessData-side adapter?* A positive answer is **not** evidence that the candidate is authoritative, byte-equivalent to the historical external distribution, licensed for analysis or redistribution, complete, or empirically eligible.

## Required sequence

1. Build and validate the generic recovery-candidate review with `build_gaze_in_wild_recovery_candidate_review()`.
2. Keep every generic inventory file role `unclassified`.
3. Explicitly select one reviewed inventory path for structural screening.
4. Call `build_gaze_in_wild_candidate_processdata_screen()`.
5. The screen re-verifies the complete candidate tree, binds the selected path to its reviewed SHA-256 and byte size, and runs `preflight_gaze_in_wild_processdata()` on that exact file.
6. Persist a screen only with `write_gaze_in_wild_candidate_processdata_screen()`, which re-runs the binding checks and requires the output to remain outside the candidate tree.

## What a passing screen establishes

A passing record establishes only that:

- the recovery review was valid and still matched the complete candidate tree at screening time;
- the operator-selected path identified exactly one reviewed inventory file;
- that file's current bytes matched the reviewed SHA-256 and size;
- the file passed the ProcessData structural checks required by the current adapter; and
- the screen is reproducibly bound to the exact recovery-review and tree fingerprints.

The generic recovery inventory remains unchanged. In particular, the selected file's generic role stays `unclassified`; a passing screen does not rename or promote it to an authoritative `ProcessData` distribution member.

## Scientific and rights boundary

The screen keeps the candidate in `quarantined` status and cannot establish any of the following:

- source authority;
- original-distribution or exact-copy identity;
- dataset-file rights, analysis-use permission, or redistribution permission;
- participant, trial, task, or labeller mapping;
- coordinate-unit semantics;
- corpus-wide sampling cadence or published acquisition cadence;
- recovery of a separate `LabelData` object or independent labeller streams;
- quarantine-exit authorization;
- source-audit readiness or empirical evidence eligibility;
- human-human agreement, participant-disjoint model validation, cross-dataset performance, GP3 validity, or Frozen Evidence performance claims.

`ETG.Labels` observed inside a ProcessData object is therefore never interpreted as recovery of the independent labeller `LabelData` files.

## Relationship to quarantine exit

This screen is intentionally orthogonal to the quarantine-exit authorization contract. Structural compatibility can help reject an incompatible candidate early, but it does **not** satisfy the independent authority, exact-copy, rights, reuse-terms, or analysis-permission evidence required for an authorized quarantine exit.

The unresolved Gaze-in-the-Wild milestone therefore remains unchanged: obtain an authoritative corpus/source copy and explicit dataset-file reuse terms before any empirical source-audit gates can open.
