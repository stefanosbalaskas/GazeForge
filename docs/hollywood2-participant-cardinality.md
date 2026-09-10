# Hollywood2 participant cardinality audit

Hollywood2 participant identity must not be reconstructed from the three-digit Hollywood2EM filename prefixes. A reviewed publication-lineage audit now shows why count-based inference is especially unsafe.

## Reviewed cardinality surfaces

Three authoritative/repository-bound surfaces are relevant:

1. The already frozen original-distribution evidence records **16 volunteers**, split into **12 active action-recognition subjects** and **4 free-viewing subjects**. Its public archive route remains login-gated and no authoritative subject-ID ledger has been recovered into GazeForge.
2. Stefan Mathe and Cristian Sminchisescu's author-posted arXiv v1 (`arXiv:1312.7570v1`, submitted 2013-12-29) likewise describes **497,107 frames viewed by 16 subjects** and, in its human-subject section, the same **12 active + 4 free-viewing** design.
3. The final 2015 IEEE TPAMI article (`doi:10.1109/TPAMI.2014.2366154`, PubMed `26352449`) describes **497,107 frames viewed by 19 subjects** and broadens the stated experimental scope to visual action recognition, scene-context recognition, and free-viewing.

This is treated as an unresolved **publication/data-version cardinality drift**. It is not automatically interpreted as a simple addition of exactly three identifiable participants to the earlier 16-subject distribution, because the exact version relationship and participant identities have not been recovered.

## Why the GIN numbering is not a shortcut

The pinned Hollywood2EM hand-labelled ground-truth repository contains 16 stable three-digit filename tokens:

`001, 002, 003, 004, 005, 006, 008, 010, 011, 012, 013, 014, 015, 017, 018, 019`

Within the numeric range 001–019, the absent values are `007`, `009`, and `016`.

Two coincidences therefore exist:

- 16 GIN tokens matches the 16-subject earlier/original source surface;
- three missing integers matches the numeric difference between 16 and the final article's 19-subject description.

Neither coincidence is mapping evidence. In particular, GazeForge must not infer that `007`, `009`, and `016` are the three participants added between source/publication versions, that those values define a task group, or that the remaining 16 tokens are verified original participant IDs.

## Frozen evidence

The reviewed record is:

`validation/evidence/hollywood2/hollywood2-participant-cardinality-evidence-v1.json`

Evidence fingerprint:

`c27b11f9d38d29aa09f0971a1a8189d5e82e444bde4f10dd585ce153c683ca10`

The validator rejects refingerprinted attempts to promote count coincidence, numeric-hole coincidence, automatic 16→19 reconciliation, participant mapping, participant-disjoint validation, rights, cross-dataset evidence, Frozen Evidence, or native-60-Hz/GP3 validity.

## What remains required

Participant-level Hollywood2 claims remain blocked until all relevant identity layers are resolved with authoritative evidence:

- a legitimately obtained original archive README or participant ledger establishing the source participant identifiers and task-group membership;
- an explicit authoritative source linking Hollywood2EM GIN filename tokens to those original subject identifiers and task groups;
- version-aware reconciliation of the 16-subject and 19-subject publication/data surfaces.

Until then, Hollywood2EM evaluation remains **source-token-held-out**, not participant-held-out or participant-generalization evidence.

The reviewed search for an explicit public mapping is frozen separately in [Hollywood2 participant-crosswalk exhaustion](hollywood2-participant-crosswalk-exhaustion.md).
