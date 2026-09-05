# Hollywood2 authoritative ground-truth evidence

GazeForge carries frozen evidence for the canonical Hollywood2EM hand-labelled ground-truth repository. This is **real empirical source evidence**, not a source-resolution scaffold.

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

## Author declaration and underlying rights context

A separately frozen provenance record verifies that Ioannis Agtzidis's 2020 TUM dissertation states that the data presented in the relevant chapter were made publicly available with an open-source licence and explicitly points to the Hollywood2EM GIN repository. That declaration materially supports provenance, but it does not name an exact licence identifier or reproduce licence text.

The original Mathe–Sminchisescu Hollywood-2 eye-movement distribution is a distinct rights layer. Its institutional licence grants academic use subject to its stated restrictions and does not establish that the later hand-labelled GIN annotation repository inherits the same redistribution terms. GazeForge therefore keeps original-source rights and annotation-repository rights separate.

## Complete reachable GIN history audit

A dedicated live workflow now audits **all seven commits reachable from the pinned canonical GIN HEAD**, rather than checking only the current tree. The history begins with commit `1e80c3e0c1527fd4fdf6a2bc880a7c43c861eed0` (`Labelled EM added`, 2019-04-10) and reaches the pinned 2020 commit above. All seven observed commits are authored by Ioannis Agtzidis.

The complete reachable history establishes the following negative and structural evidence:

- no `LICENSE`, `COPYING`, or equivalent licence-named file occurs in any reachable revision;
- the three distinct historical `README.md` blobs contain no licence/licence keyword evidence and no participant/subject/observer/identity mapping statement recovered by the reviewed probe;
- the canonical `ground_truth/` directory first appears in commit `357bafd1decbea23eb2fe7cfd0fa1420c25d955c`, whose subject is `Moved files to correct directory`;
- all **697** current ground-truth paths first appear in that move commit;
- from that commit through HEAD, the ground-truth path inventory has one version and the set of **16 three-digit filename tokens** has one version;
- the stable ground-truth path inventory is fingerprinted as `0a8e49b3ae814bee212176557cc71c0d5658cdcf56d16f1c75b15c0566ee989d`.

This history result strengthens the provenance boundary but does not change its semantics. Persistent filename prefixes demonstrate stable repository syntax; they do **not** prove that the prefixes are original participant identifiers or identify active/free-viewing group membership. Likewise, failure to recover licence text from Git history does not negate the separate author open-source declaration; it means the exact repository-level licence identifier/text and redistribution scope remain unrecovered.

Frozen history evidence:

`validation/evidence/hollywood2/hollywood2-gin-history-evidence-v1.json`

History evidence fingerprint:

`c7d2f477a66feca3676482ffdabff2b0778196db99e48b86104fe86d0f5bfae1`

## Derived 60 Hz source-token-held-out validation

GazeForge now also carries a reviewed model-validation result derived from the same pinned 500 Hz hand-labelled source. The benchmark is downsampled to **60 Hz** using the existing label-purity-aware resampling contract. With minimum label purity `0.75`, the 697 source files produce **465,013** derived rows before ambiguity exclusion and **450,649** analysis rows after excluding **14,364** ambiguous windows.

The split unit is the stable three-digit canonical filename prefix. The 16 prefixes are divided into four matched GroupKFold folds, with four source tokens held out in each fold. They remain **opaque source tokens only**. The result must therefore be described as **source-token-held-out**, never participant-held-out or participant-generalization evidence.

A reproducibility review compared the successful pre-merge empirical execution (workflow `33955703630`, head `5180d4e38a2f5929161b7baee6af18c5e9b43c4d`, artifact `9966618539`) with the exact PR #66 merge-SHA execution (workflow `33956874927`, head `e0e47c47e0a2e42a4520bd14a126b23fc3b05644`, artifact `9966993646`). Source identity, preparation, held-out token assignment, predictions-derived performance summaries, and all substantive results were the same. The byte-level reports differed only in last-bit RandomForest calibration-ECE arithmetic at approximately `1e-17`, so neither uncanonicalized report was frozen directly.

For publication, GazeForge therefore applies a narrow deterministic numeric contract: **finite floating-point values inside the report `metrics` object are rounded to 15 decimal places before the publication fingerprint is computed**. Non-finite metric floats are rejected. Benchmark metadata, model configuration, protocol settings, source identities, rights state, and scientific claim boundaries are not rounded or rewritten. Under that rule the two independently generated reports become byte-identical.

The reviewed canonical full aggregate report has fingerprint:

`a7a6219d6ffcb1fc6622110887a95f2c9d0646fea6e22d0ada941fe07b90586a`

and deterministic canonical report-file SHA-256:

`a5e22948105321dc97dcffc66926c32a6c93c797722b879e38fd3c6860dde34e`.

The committed Frozen Evidence projection is:

`validation/evidence/hollywood2/hollywood2-source-token-60hz-frozen-summary-v1.json`

with fingerprint:

`e1f1c030f843e118ebd65520dfab8e872efb4ea3e1d520299a993b0ca00ddabf`.

That frozen projection also binds the reviewed pre-merge and exact-merge workflow/artifact identities and their original uncanonicalized report fingerprints. The public Frozen Evidence page renders its model summary directly from this fingerprint-validated JSON rather than from hand-transcribed performance values.

The reviewed result shows the same kind of model trade-off that motivates GazeForge's multi-level evaluation: ContextMLP is strongest on the principal sample-level classification metrics and has the best mean matched-event IoU and boundary-error profile in this benchmark, whereas transparent I-VT retains the highest mean event F1 because of substantially higher event precision. RandomForest is intermediate on sample-level classification but weaker on event F1. These are benchmark-specific source-token-held-out findings, not a universal AI-superiority claim.

The dedicated source-token workflow first attempts a fresh checkout of the pinned canonical GIN source. When source bytes are successfully acquired, the workflow reruns the complete 60 Hz benchmark and fails unless the canonical full-report fingerprint, deterministic report-file SHA-256, benchmark/model metadata, model summary, source-token fold assignment, analysis-label counts, and key preparation counts exactly match the committed frozen projection. A reachable source with the wrong commit identity, a dirty tracked tree, or any live-report mismatch remains a hard failure.

GitHub-hosted runners can also be rejected by the upstream GIN service before any source bytes are read. If **every bounded attempt to the canonical GIN hostname returns HTTP 403**, the workflow records that as source unavailability rather than silently converting it into either a scientific success or a model-validation failure. The blocking fallback then re-downloads the two already reviewed aggregate artifacts from workflows `33955703630` and `33956874927`, verifies their bound artifact ZIP digests, original report-file SHA-256 values, and original report fingerprints, and re-canonicalizes both reports under the exact current code. Certification succeeds only if both independently source-verified reports again become byte-identical at the frozen canonical fingerprint and canonical file SHA-256. This fallback is explicitly **artifact replay, not a fresh empirical source rerun**; it does not create a new source-availability, source-identity, or participant-generalization claim.

## Rights and remaining boundaries

The annotation repository's exact licence identifier/text and raw-annotation redistribution scope remain unresolved. The article's CC BY licence is not treated as the dataset licence, and the original Hollywood-2 institutional licence is not automatically inherited by the later GIN annotation repository.

The 16 filename tokens match the published Hollywood-2 eye-tracking participant count, and the original public dataset is documented elsewhere as carrying unique subject IDs within task groups. However, no authoritative GIN-token → original-subject-ID mapping has been recovered. GazeForge therefore does not promote the filename tokens to verified participant identities or infer active/free-viewing group membership.

Consequently participant-held-out Hollywood2 modelling remains gated. The frozen source-token result also does not create independent human-human agreement, Lund↔Hollywood2 cross-dataset validation, recovery of the complete original video/gaze archive, exact annotation-repository licence resolution, redistribution permission, or native Gazepoint GP3 validity.

## Reproducibility

The authoritative ground-truth evidence record is:

`validation/evidence/hollywood2/hollywood2-authoritative-ground-truth-evidence-v1.json`

Ground-truth evidence fingerprint:

`d5375b8768984ef76da02597c55b225aaff4088fd24698c0d53363e2df6b20ea`

The canonical live-source workflow reclones the GIN repository, recomputes every ground-truth file identity and aggregate metric, regenerates the 697-entry ledger fingerprint, and binds the result to the immutable ground-truth evidence contract.

The complete-history workflow independently reclones the same pinned repository, enumerates every reachable commit, rechecks historical licence/README evidence and ground-truth path/token history, and binds the live result to the immutable history evidence contract. Persistent upstream unavailability remains fail-closed rather than being converted into a successful source result.

The source-token validation workflow has two distinct certification paths. Its preferred path reclones the pinned repository, derives the 60 Hz analysis rows, reruns all four matched source-token folds, validates the aggregate-only claim boundary, applies the metrics-only 15-decimal canonicalization contract, and binds the regenerated aggregate report to the frozen source-token summary. If the canonical GIN endpoint instead returns HTTP 403 on every bounded canonical attempt before acquisition, the workflow cannot claim a fresh rerun; it replays and cryptographically revalidates both previously reviewed source-verified aggregate artifacts under the current publication code. This replay path is permitted only for the explicit upstream-availability condition and does not replace the independent live-source and complete-history evidence probes, which remain fail-closed. Raw source rows, filenames, and predictions are not committed to GazeForge in either source-token path.