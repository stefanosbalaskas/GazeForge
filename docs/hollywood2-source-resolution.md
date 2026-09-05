# Hollywood2EM source-resolution status

GazeForge separates **source resolution**, **empirical source evidence**, **rights review**, **source-audit readiness**, and **performance validation**. Those states are related, but they are not interchangeable.

The active machine-readable checkpoint is:

```text
validation/protocols/hollywood2-source-resolution-2026-09-05.json
```

It supersedes the preserved historical checkpoint:

```text
validation/history/source-resolution/hollywood2-source-resolution-2026-09-04.json
```

The September 4 record established the canonical GIN distribution identifier but had not retrieved an exact repository copy. The September 5 checkpoint records a materially stronger state because the canonical repository and its complete hand-labelled `ground_truth/` subset were recovered and fingerprinted directly.

## Canonical repository recovered

The authoritative dataset publication remains:

> Ioannis Agtzidis, Mikhail Startsev, and Michael Dorr. *Two hours in Hollywood: A manually annotated ground truth data set of eye movements during movie clip watching*. Journal of Eye Movement Research, 13(4), 2020. DOI: `10.16910/jemr.13.4.5`.

The publication identifies the GIN repository as the Hollywood2EM distribution location. GazeForge resolved the live Git repository to:

```text
https://gin.g-node.org/ioannis.agtzidis/hollywood2_em.git
refs/heads/master
870fa6d6209c9085260918d61433a0a2c70fd497
```

At that exact revision, the authoritative hand-labelled `ground_truth/` tree contains:

- **697 ARFF files**;
- **137,328,178 bytes**;
- **3,871,580 gaze samples**;
- **642 test files** and **55 train files**;
- **56 clips**;
- **16 filename subject tokens**.

All 697 files are ordinary Git blobs. The ordered source-identity ledger is frozen by SHA-256:

```text
51dd0883cf5b7966a4caea94fb9ac97e43bee6cf716423f26f268810041d3030
```

The immutable empirical source record is:

```text
validation/evidence/hollywood2/hollywood2-authoritative-ground-truth-evidence-v1.json
```

with evidence fingerprint:

```text
d5375b8768984ef76da02597c55b225aaff4088fd24698c0d53363e2df6b20ea
```

## Empirical annotation composition

Across all **3,871,580** samples, the expert-corrected final annotation stream contains:

| Class | Samples | Fraction |
| --- | ---: | ---: |
| Fixation | 2,414,211 | 62.357% |
| Saccade | 353,208 | 9.123% |
| Smooth pursuit | 936,913 | 24.200% |
| Noise | 167,248 | 4.320% |

These values reproduce the rounded class composition reported by the publication.

The first/student coding and expert-corrected final coding are equal on **3,580,265** samples and differ on **291,315** samples, for raw equality **0.9247555262**.

This comparison is frozen as **annotation sensitivity**, not independent human-human reliability. The expert labels are corrections of the earlier novice/student coding and therefore do not constitute an independently produced second annotation stream.

## Format and units

The authoritative files use one uniform six-column `gaze_labels` ARFF schema:

```text
time
x
y
confidence
handlabeller_1
handlabeller_final
```

Pinned author implementation material in `MikhailStartsev/deep_em_classifier` documents the shared ARFF convention as:

- `time` in **microseconds**;
- `x` and `y` in **pixels**.

The recovered files yield a median sampling rate of **500 Hz**, consistent with the Hollywood2EM publication. GazeForge therefore treats the time and coordinate units as verified at the format level for this recovered source subset.

## What remains unresolved

The stronger source state does **not** close every provenance gate.

### Dataset-specific rights

No repository `LICENSE` or `COPYING` file was present at the pinned GIN revision. GazeForge therefore keeps both:

- `analysis_use_terms_status=unresolved`;
- `raw_data_redistribution_terms_status=unresolved`.

The CC BY 4.0 license of the article is not treated as a dataset-file license, and a general description of the dataset as openly licensed is not substituted for exact repository-level terms.

### Participant identity mapping

The 16 filename subject tokens recovered from the repository are:

```text
001 002 003 004 005 006 008 010 011 012 013 014 015 017 018 019
```

They match the published observer count, but GazeForge does not promote those tokens into verified participant identities without an authoritative mapping statement. Participant-held-out validation therefore remains blocked.

### Independent human-human agreement

Hollywood2EM still does not provide a verified pair of independently produced annotation streams. Student-versus-expert comparison remains annotation sensitivity only.

### Model and cross-dataset validation

This tranche does not create:

- Hollywood2 participant-disjoint model validation;
- Lund→Hollywood2 or Hollywood2→Lund cross-dataset validation;
- canonical Frozen Evidence performance results;
- native Gazepoint GP3 evidence.

## Current reviewed state

The active source-resolution status is:

```text
canonical_repository_and_ground_truth_recovered_terms_and_participant_mapping_unresolved
```

with:

- `canonical_distribution_identifier_found=true`;
- `current_retrievable_copy_verified=true`;
- `empirical_evidence_created=true`;
- `source_audit_ready=false`;
- analysis-use terms unresolved;
- raw-data redistribution terms unresolved;
- participant identity mapping unresolved.

The source-resolution governance lock records this checkpoint identity, but the lock itself remains a **non-empirical authorization artifact**. It does not create or authorize empirical evidence; it only certifies that the active checkpoint set matches the scientifically reviewed snapshot.

## Next required actions

1. Resolve exact dataset-specific analysis-use and redistribution terms from an author-verified or institutional source.
2. Resolve the semantic mapping of the 16 filename subject tokens before participant-held-out evaluation.
3. Use the frozen authoritative source ledger for planned student-versus-expert sensitivity analyses.
4. Run Hollywood2 model validation only after the remaining provenance gates pass.
5. Run Lund↔Hollywood2 cross-dataset validation only under participant-safe, source-audited conditions.
6. Keep performance evidence separate from this source-resolution state until the Frozen Evidence gate is satisfied.
