# Hollywood2 authoritative ground-truth evidence

GazeForge now carries a frozen evidence record for the canonical Hollywood2EM hand-labelled ground-truth repository. This is **real empirical source evidence**, not a source-resolution scaffold.

## Canonical source

The live source probe resolves the repository published by Agtzidis, Startsev, and Dorr:

- repository: `https://gin.g-node.org/ioannis.agtzidis/hollywood2_em.git`
- default ref: `refs/heads/master`
- pinned commit: `870fa6d6209c9085260918d61433a0a2c70fd497`
- commit message: `Added sp_tool smoothed files`
- README Git blob: `c8b7d126295e5f52a7748533952f044228423bf8`
- README SHA-256: `97f839bda127674b5de1eb5d8c3b1d2c82d65e7c6c1708c2e9f9711170ada383`

The repository contains 6,234 ordinary Git blobs and 6,218 ARFF files. The authoritative `ground_truth/` tree contains 697 ARFF files; no Git-annex indirection is required at the pinned revision.

## Ground-truth coverage

The pinned ground-truth subset contains:

- **697 files** and **137,328,178 bytes**;
- **3,871,580 gaze samples**;
- **56 clips**: 50 test clips and 6 training clips;
- **16 file-level subject tokens**;
- **642 test files** and **55 training files**;
- one uniform ARFF schema across all 697 files.

The ordered 697-entry source identity ledger is regenerated from the pinned repository and bound by SHA-256:

`51dd0883cf5b7966a4caea94fb9ac97e43bee6cf716423f26f268810041d3030`

Every ledger entry contains its repository path, byte length, Git blob SHA-1, SHA-256, row count, split, clip identifier, file subject token, schema signature, and observed timing rate. Raw source bytes are not committed to GazeForge.

## Schema and units

All 697 files use relation `gaze_labels` and the same six attributes:

`time`, `x`, `y`, `confidence`, `handlabeller_1`, `handlabeller_final`.

The pinned author implementation `MikhailStartsev/deep_em_classifier@9a345a37aab47ac6780ce0d4b5798cc15291c75b` documents the shared ARFF convention as time in **microseconds** and x/y gaze coordinates in **pixels**. Under that convention the authoritative Hollywood2 files yield a median per-file sampling rate of **500.0 Hz**; the observed range is approximately 499.7501–500.0 Hz, consistent with the published 500 Hz acquisition rate.

## Final annotation composition

Across all 3,871,580 samples, `handlabeller_final` contains:

| Label | Samples | Fraction |
| --- | ---: | ---: |
| Fixation | 2,414,211 | 62.357% |
| Saccade | 353,208 | 9.123% |
| Smooth pursuit | 936,913 | 24.200% |
| Noise | 167,248 | 4.320% |

These counts reproduce the publication's rounded 62.4% fixation, 9.1% saccade, and 24.2% pursuit composition.

## Student-to-expert-corrected sensitivity

`handlabeller_1` is the first novice/student coding pass and `handlabeller_final` is the subsequently expert-corrected result. Across all samples:

- equal labels: **3,580,265**;
- changed labels: **291,315**;
- raw equality fraction: **0.9247555262**.

This is frozen as **annotation sensitivity**. It is **not independent human-human reliability**, because the second coder corrected the first coding rather than producing an independent annotation stream.

## Rights and remaining boundaries

The canonical repository contains no LICENSE/COPYING file at the pinned revision. The article's CC BY license is not treated as the dataset license, and a separate description of the dataset as openly licensed is not substituted for exact repository-level terms. Dataset-specific analysis-use and redistribution terms therefore remain unresolved.

The 16 filename subject tokens match the published observer count, but GazeForge does not yet promote those tokens to verified participant identities. Consequently participant-held-out Hollywood2 modelling remains gated. The evidence also does not create independent human-human agreement, model validation, Lund↔Hollywood2 cross-dataset validation, recovery of the original Hollywood2 video corpus, or canonical Frozen Evidence.

## Reproducibility

The committed evidence record is:

`validation/evidence/hollywood2/hollywood2-authoritative-ground-truth-evidence-v1.json`

Evidence fingerprint:

`d5375b8768984ef76da02597c55b225aaff4088fd24698c0d53363e2df6b20ea`

The dedicated live workflow reclones the canonical GIN repository, recomputes every ground-truth file identity and aggregate metric, regenerates the 697-entry ledger fingerprint, and binds the result to the immutable evidence contract.
