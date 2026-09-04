# VISUS public partial 60 Hz evidence

GazeForge includes a **narrow, real-data VISUS-derived evidence record** recovered from a public University of Stuttgart VISUS-supervised software repository. This tranche is intentionally separate from the canonical VISUS source-audit and Frozen Evidence workflows.

## What was recovered

The public repository `Maurice189/eye-slitscan` is pinned at commit
`a8ea2402936122f9e5c98152460bd16a4ba97740`. Its README identifies the project as a bachelor thesis at VISUS, University of Stuttgart, supervised by Kuno Kurzhals.

At that exact commit, GazeForge recovered and hash-verified four files without vendoring their bytes:

- `01-car pursuit.xml`, a 625-frame dynamic-AOI annotation for `01-car pursuit.avi`;
- `P1A-01-car pursuit.tsv`;
- `P2B-01-car pursuit.tsv`;
- `P9B-01-car pursuit.tsv`.

The naming convention matches the original VISUS benchmark convention of participant/group/stimulus exports. The AOI XML contains a 1920×1080, 25 fps stimulus with two dynamic AOIs: **Red Car** across frames 1–625 and **White Car** across frames 553–590.

Every source file is bound to both its upstream Git blob SHA-1 and a SHA-256 content digest. The raw source bytes are **not committed to GazeForge**.

## Observed sampling contract

All three Tobii recordings are internally coherent 60 Hz exports:

| Participant | Samples | Median interval | Inferred rate | Both-eye valid |
| --- | ---: | ---: | ---: | ---: |
| P1A | 1,499 | 16,625 µs | 60.1504 Hz | 93.73% |
| P2B | 1,499 | 16,625 µs | 60.1504 Hz | 96.40% |
| P9B | 1,500 | 16,625 µs | 60.1504 Hz | 96.60% |
| **Total** | **4,498** | — | **60.1504 Hz** | **95.58%** |

The probe follows the pinned upstream Tobii parser and AOI-mapping semantics: mapped fixation points use media coordinates, fixation events are deduplicated by fixation index, and AOI membership uses the active ViPER bounding box with half-open pixel bounds.

## Dynamic-AOI results

Across the three recordings:

- **185 fixation events** were recovered;
- **166 fixation events** intersected at least one dynamic AOI;
- fixation-event AOI-hit fraction: **89.73%**;
- total fixation duration: **75,039 ms**;
- fixation duration associated with at least one dynamic AOI: **70,179 ms**;
- duration AOI-hit fraction: **93.52%**;
- **3,679 / 4,498 samples** intersected at least one dynamic AOI (**81.79%**).

Participant-level fixation results are:

| Participant | Fixations | AOI-hit fixations | Event hit fraction | AOI-hit fixation duration |
| --- | ---: | ---: | ---: | ---: |
| P1A | 77 | 67 | 87.01% | 22,280 ms |
| P2B | 51 | 48 | 94.12% | 23,903 ms |
| P9B | 57 | 51 | 89.47% | 23,996 ms |

The Red Car dominates AOI membership, as expected for the `car pursuit` stimulus. White Car is active only late in the stimulus and can spatially overlap Red Car, so AOI-specific counts are not mutually exclusive.

## Reproducibility

The isolated workflow `.github/workflows/visus-public-partial-probe.yml` downloads the four exact commit-addressed upstream files and recomputes each Git blob identity before analysis. The first successful probe was workflow run `33924318147`, head `6d6a80aa5ea9b0ae6ad1878786ecf5346ad7196b`, with deterministic probe fingerprint
`b1a301151ffae7efefdfccce647f509ec2b7ffe911b88b4979834ca526d1d4b1`.

The committed evidence record is:

`validation/evidence/visus-public-partial/visus-public-partial-evidence-v1.json`

It is validated by `gazeforge.visus_public_partial`. The v1 fingerprint is immutable; a corrected or expanded corpus must use a new evidence version.

## Claim boundary

This evidence is deliberately narrow.

- It covers exactly **3 public Tobii recordings × 1 VISUS stimulus**.
- It does **not** resolve or replace the full original **25 participants × 11 stimuli** VISUS benchmark.
- The original dataset license remains unresolved; GazeForge records an analysis-use basis but does not assert unrestricted redistribution.
- GazeForge does **not** redistribute the source TSV/XML bytes.
- It does **not** establish human-human agreement.
- It does **not** constitute model validation.
- It does **not** pass or weaken the canonical VISUS Frozen Evidence gate.
- It is **Tobii 60 Hz evidence**, not native Gazepoint GP3 evidence.

The existing full VISUS source audit therefore remains fail-closed and unchanged.
