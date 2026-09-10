# Hollywood2 participant-crosswalk exhaustion

GazeForge now freezes the result of a public-source search for an explicit mapping between the Hollywood2EM three-digit filename tokens and the original Hollywood-2 participant identifiers/task groups.

## Result

**No authoritative public crosswalk was recovered.**

That result does not mean the tokens are unrelated to participants. It means the available evidence is insufficient to claim what each token identifies. The values therefore remain **opaque source tokens**.

## Public surfaces reviewed

The exhaustion record binds the following evidence layers:

- the original Hollywood-2 eye-tracking distribution page, which reports 16 volunteers split into 12 active action-recognition and 4 free-viewing subjects and refers to an included README, but does not expose a public subject ledger or GIN-token mapping on the description page;
- the original academic-use licence/access surface, without bypassing registration, login, licence acceptance, or institutional access controls;
- `arXiv:1312.7570v1` and the final IEEE TPAMI article (`10.1109/TPAMI.2014.2366154`, PubMed `26352449`), whose 16-versus-19 participant-cardinality difference is already frozen separately and cannot resolve token identity;
- the 2020 Hollywood2EM paper (`10.16910/jemr.13.4.5`), which identifies 56 annotated clips viewed by 16 observers and links the canonical GIN data set, but does not provide an explicit filename-token → original-subject/task-group crosswalk;
- the already complete seven-commit canonical GIN-history audit, including all three README versions, which recovered no participant/identity mapping from repository history;
- a secondary public Hollywood2EM parser used for eye-event evaluation, which preserves Hollywood2EM paths but does not interpret the filename prefix as a participant ID or task group and is not authoritative for original participant identity.

## Numerical coincidences remain non-evidence

The canonical GIN token inventory is:

`001, 002, 003, 004, 005, 006, 008, 010, 011, 012, 013, 014, 015, 017, 018, 019`

The missing integers inside 001–019 are `007`, `009`, and `016`.

Two tempting shortcuts are prohibited:

1. **16 GIN tokens = 16 earlier/original participants.** Matching cardinality does not prove that each token is an original participant identifier.
2. **3 missing integers = the 16→19 publication delta.** The missing values are not evidence for the identities of three additional participants, nor for a task group.

Likewise, ordinal labels such as free-viewing subjects 1–4 in publication analyses are not equated with GIN tokens.

## Frozen record

The reviewed exhaustion evidence is:

`validation/evidence/hollywood2/hollywood2-participant-crosswalk-exhaustion-evidence-v1.json`

Evidence fingerprint:

`5900a3515243f92ea374a0dc5d1d80e6c95d64b1dc6fa7b4f698df85488eaafa`

The corresponding validator is fail-closed. Refingerprinting an edited record cannot promote participant identity, task-group identity, participant-disjoint validation, cross-dataset validation, Frozen Evidence, native-60-Hz/GP3 validity, rights scope, or raw-data redistribution.

## Remaining authoritative routes

There are now only three legitimate resolution routes:

1. Obtain `gaze_hollywood2.zip` through the original distribution's normal institutional terms and inspect only its README/metadata with the existing metadata-only participant-ledger intake. An original subject ledger alone still does not prove a GIN-token crosswalk.
2. Recover a public author/institutional source that explicitly maps every relevant Hollywood2EM token to an original subject identifier and task group.
3. Obtain an explicit author-supplied token ledger through a normal authorized channel and independently review it before promotion.

No login bypass, raw-data redistribution, count inference, filename-shape inference, or third-party reconstruction is an acceptable substitute.

## Current scientific boundary

Hollywood2EM validation remains **source-token-held-out**, not participant-held-out. Participant-generalization claims and Lund↔Hollywood2 cross-dataset validation that depend on verified participant semantics remain blocked until an explicit authoritative crosswalk is recovered and reviewed.
