# VISUS public 60 Hz event-extension evidence

GazeForge contains a second, narrowly scoped empirical VISUS-derived evidence tranche built from two complete Tobii exports that are publicly present in the VISUS-supervised [`Maurice189/eye-slitscan`](https://github.com/Maurice189/eye-slitscan) repository.

This evidence is deliberately separate from the [VISUS public partial 60 Hz AOI evidence](visus-public-partial-evidence.md) and from the canonical [VISUS Frozen Evidence gate](visus-frozen-evidence-gate.md). It expands real participant-level 60 Hz event coverage; it does **not** resolve the full VISUS benchmark.

## Frozen source identity

The source repository is pinned to commit:

`a8ea2402936122f9e5c98152460bd16a4ba97740`

Two complete Tobii exports are treated as empirical data:

| Participant | Upstream path | Bytes | Git blob SHA-1 | SHA-256 |
| --- | --- | ---: | --- | --- |
| P5B | `core/importer/eye-tracker-output/test/Tobii_exports/01-OK.tsv` | 263,072 | `fd2371fd6f44de8a188e52439a0fea6b2054f975` | `df9ee65adb3a9872121f5ae3204842b0ab2efe107682151a287168f526b2c4b6` |
| P3A | `core/importer/eye-tracker-output/test/Tobii_exports/02-OK.tsv` | 256,538 | `e39b0c0d2c50c22dec76b93581a4ca2bce784546` | `619da12969d04b774b9456b1b50e8cba6b21c04df33e2e90ef1c798a511d2bbc` |

The upstream C++ unit test is also pinned as provenance-only source material:

- path: `core/importer/eye-tracker-output/test/test.cc`
- Git blob SHA-1: `d5f681eb4cc7b90c6078dc1fb7ceeccb4cc03c41`
- SHA-256: `999ab4c53e0817a65fc12bb9c143e19490059bb71bab5c6a03a2533cc9e5d1ee`

That test explicitly loads `01-OK.tsv` and `02-OK.tsv` as valid Tobii exports and asserts known timestamps, fixation indices, fixation durations, and mapped coordinates. This establishes that the two files were intentional valid-input fixtures upstream rather than unreferenced loose files.

Three LibreOffice lockfiles in the same source directory are retained **only as provenance**, never as empirical observations. They identify historical files named `P2B-03-dialog.tsv`, `P4B-03-dialog.tsv`, and `P6A-03-dialog.tsv`, all opened by Maurice Koch on 21 May 2017. The underlying three TSV files are not present in the Git history recovered so far.

## Empirical results

Both complete exports contain 1920×1080 media coordinates and sample intervals with a median positive microsecond delta of 16,625 µs, corresponding to approximately 60.1504 Hz.

| Metric | P5B | P3A | Aggregate |
| --- | ---: | ---: | ---: |
| Samples | 1,145 | 1,145 | **2,290** |
| Both-eye-valid samples | 1,136 | 1,136 | **2,272** |
| Both-eye-valid fraction | 0.9921 | 0.9921 | **0.9921** |
| Inferred sampling rate | 60.1504 Hz | 60.1504 Hz | **60.1504 Hz** |
| Fixation events | 62 | 43 | **105** |
| Fixations with on-screen mapped point | 62 | 42 | **104** |
| On-screen fixation fraction | 1.0000 | 0.9767 | **0.9905** |
| Movie span | 19.063 s | 19.069 s | — |

The Tobii export settings recovered from both source headers are identical: `Eye = Average`, `Validity = Normal`, `Fixation filter = Tobii fixation filter`, `Velocity threshold = 35`, and `Distance threshold = 35`.

### Fixation-duration interpretation

The exported fixation-duration values sum to 39,614 ms across both recordings, whereas the two `MovieStart`→`MovieEnd` spans sum to 38,132 ms. This is not interpreted as 39,614 ms of fixation time confined to the video segments. Tobii fixation durations can extend across segment boundaries; GazeForge therefore freezes these values as exported event metadata and explicitly records that they are **not clipped to the movie boundaries**.

## `03-dialog` is a strong inference, not resolved identity

The two source files are named `01-OK.tsv` and `02-OK.tsv`; they do not themselves contain a VISUS stimulus filename. Consequently GazeForge does not promote the stimulus identity to resolved status.

The candidate `03-dialog` assignment is nevertheless strongly supported by converging evidence:

1. both complete movie segments are approximately 19 s long (19.063 s and 19.069 s);
2. the original VISUS benchmark describes the Dialog stimulus as 19 s;
3. the same upstream directory contains three historical lockfiles explicitly named for `03-dialog` recordings;
4. Osnabrück University's WACV 2017 converted-dataset page independently lists Kurzhals stimulus K3 as **Dialog**.

The immutable evidence record therefore uses:

`identity_status = strongly-inferred-not-file-bound`

and requires:

`stimulus_identity_resolved = false`

No Dialog AOI annotation stream has been recovered for these two exports, so this tranche contains event/QC evidence rather than dynamic-AOI performance evidence.

## Analysis-use boundary

The current Osnabrück University WACV 2017 dataset page states that the converted datasets are provided for research purposes, asks users to cite the conversion work and original dataset, and lists the Kurzhals dataset as an 11-video converted collection:

<https://www.ikw.uni-osnabrueck.de/en/research_groups/computer_vision/research/interactive_3d_modelling/multimedia_container/wacv17.html>

This supports an analysis-use basis. It does **not** by itself establish a dataset-specific unrestricted redistribution license for the original VISUS bytes. GazeForge therefore stores hashes, provenance, and derived metrics but does not vendor the upstream TSV files.

## Reproducibility

The live workflow runs:

```text
python scripts/visus_public_event_extension_probe.py
```

It re-downloads the exact pinned files, independently reconstructs each Git blob SHA-1, checks byte sizes, computes SHA-256 identities, parses the Tobii exports, validates the upstream unit-test assertions and lockfile provenance, recomputes participant/event metrics, and produces a deterministic JSON probe.

Frozen probe identity:

- workflow run: `33928088952`
- probe head: `9308c79dc3f6ef9d42383e85ec2abc6bad0b783d`
- probe fingerprint: `47316bcb77e3cf1a92fdb95df84cf401c31fdafd6fc6affce3b9f6405f92312e`
- artifact: `9957528541`
- artifact ZIP SHA-256: `cc9f139c9c7b27649fefd8a302801707bbe6dc6140f49fafd3525971a02f437d`

Immutable evidence fingerprint:

`2f12bd83d71786bfae7101dec6515c49c5ff4e696df8675b3955300e5e5e6dfd`

The committed validator also binds a newly generated live probe back to this frozen evidence contract. Any drift in source identities, participant metrics, provenance, or scientific boundaries fails closed.

## What this evidence does not establish

This tranche does **not** establish any of the following:

- exact file-bound `03-dialog` stimulus identity for P5B or P3A;
- Dialog AOI annotations or AOI-hit metrics;
- the complete original 25-participant × 11-stimulus VISUS corpus;
- a resolved unrestricted redistribution license;
- independent human-human annotation agreement;
- model-human validation;
- native Gazepoint GP3 evidence;
- canonical VISUS Frozen Evidence.

Those requirements remain open and are intentionally protected by the validator.
