# Hollywood2 participant-ledger intake

GazeForge provides a **metadata-only, fail-closed intake** for an original Hollywood-2 eye-movement archive that the caller has legitimately obtained and is authorized to inspect. The intake exists to recover authoritative participant/task-group metadata without importing the restricted raw gaze corpus into the repository.

## Why this gate exists

The public original-distribution metadata states that Hollywood-2 eye movements were collected from **16 volunteers**, split into **12 active** and **4 free-viewing** subjects. Separate dissertation evidence reports that the distributed dataset lists unique subject IDs within task groups. The currently reviewed public download route is login-gated, however, so GazeForge has not recovered the authoritative archive README/subject ledger itself.

The canonical Hollywood2EM annotation repository independently exposes **16 stable three-digit filename tokens**. That numerical match is not participant mapping evidence. Until an authoritative crosswalk is recovered and reviewed, those values remain opaque source tokens.

A separate publication-lineage audit also establishes that the author-posted 2013 arXiv v1 describes 16 subjects, whereas the final 2015 TPAMI article describes 19 subjects and a broader task scope including scene-context recognition. GazeForge treats this as unresolved version/cardinality drift rather than automatically reconciling the cohorts. See [Hollywood2 participant cardinality audit](hollywood2-participant-cardinality.md).

## Safety and rights contract

The intake never downloads the archive. The caller must provide a local file named `gaze_hollywood2.zip` and explicitly affirm that the local copy was obtained under terms that authorize inspection.

Before reading metadata, the intake rejects:

- unsafe absolute, traversal, drive-letter, or backslash ZIP paths;
- duplicate member names;
- symbolic-link members;
- encrypted members;
- archives or metadata surfaces exceeding bounded size/count guardrails.

Only small text-like members whose filenames indicate README, participant, subject, observer, metadata, licence/license, documentation, or information content are opened. Archive members are **never extracted to disk**, and non-metadata/raw gaze members are not opened.

The output contains archive/member hashes, sizes, and conservative marker booleans/counts. It does not copy README text or subject IDs into the report.

## Local use

```bash
python scripts/inspect_hollywood2_participant_ledger.py \
  gaze_hollywood2.zip \
  --confirm-authorized-local-copy \
  --output hollywood2-ledger-intake.json
```

Both the raw archive and the generated local intake report are git-ignored. Do not override those guards to commit source bytes or locally derived participant metadata.

## What a positive metadata marker means

Detection of phrases such as “unique subject IDs”, active/free-viewing group language, or subject-ID-like lines is a **discovery signal only**. It does not automatically establish any of the following:

- that recovered identifiers have been accepted as reviewed authoritative evidence;
- that a complete subject→task-group ledger has been recovered;
- that a GIN filename token maps to an original subject ID;
- that a GIN token identifies the active or free-viewing condition;
- that participant-disjoint Hollywood2 model validation is now valid.

Any such promotion requires manual review of authoritative metadata and an explicit, separately validated crosswalk.

## Frozen governance contract

The intake contract is frozen at:

`validation/governance/hollywood2-participant-ledger-intake-v1.json`

Protocol fingerprint:

`b47cc0acea2ded577d140d38ca97ad71ce414d82a41b2675e5cac6fc2dc9135b`

The contract fixes the current state as **ready for authorized local archive metadata inspection**, not participant mapping resolved. It explicitly keeps analysis authorization, redistribution permission, participant mapping, participant-disjoint validation, cross-dataset validation, Frozen Evidence promotion, and native-60-Hz/GP3 validity false.

## Success criterion

This gate can advance only when a legitimately obtained original archive yields authoritative README/ledger metadata that explicitly resolves the original subject identifiers and task-group membership. Even then, a separate authoritative link is still required before any original subject ID can be equated with a Hollywood2EM GIN token. The 16-versus-19 publication-lineage ambiguity must also be reconciled before participant-generalization claims are made.
