# Gaze-in-the-Wild distribution availability evidence

GazeForge records **where the Gaze-in-the-Wild authors said the compressed dataset was distributed**, **whether an exact copy has actually been obtained**, and **what rights apply to that external copy** as separate questions.

The reviewed evidence record is:

```text
validation/evidence/gaze-in-wild/gaze-in-wild-distribution-availability-evidence-v1.json
```

Its immutable fingerprint is:

```text
2400c81a0897fb414285069c368a8a9d96de1d18eb185b1073cf15bb1c8bd1da
```

This is provenance/governance evidence. It is **not Frozen Evidence performance evidence**.

## First-party distribution identity

The 2020 Scientific Reports paper states that compressed data and code were publicly available from:

```text
http://www.cis.rit.edu/~rsk3900/gaze-in-wild/
```

The pinned first-author processing repository points users to the same historical project webpage for all data files. Its README separately states that the raw data exceed 14 TB, are not provided over the internet, and require contacting the authors for specific raw-data access.

Together these sources establish the historical first-party distribution identity. They do **not** establish that GazeForge currently possesses the exact compressed `ProcessData`/`LabelData` archive.

## Dated retrieval observation

During the 2026-09-05 source-resolution review, HTTPS retrieval of the historical RIT endpoint returned HTTP `502` in the review environment. GazeForge records that observation narrowly:

- retrieval did not succeed in that environment;
- it is not proof that the endpoint fails from every network;
- it is not proof that no preserved authoritative copy exists; and
- it is not exact-file identity evidence.

The current RIT Perception for Movement Lab page still lists **The Gaze-In-Wild Dataset**, but its surfaced link points to the publication record rather than exposing a direct current archive.

Searches of common research-data repository classes did not identify an authoritative first-party replacement DOI or repository during this review. That negative search result is dated evidence, not a permanent claim.

## Secondary recovery leads are quarantined

Two public GitHub observations are retained only as recovery/provenance leads.

`Morris88826/awesome-eye-data` advertises a processed collection named `GazeinTheWild` and a Google Drive folder. Its documented organization uses transformed annotation CSVs and chunked video files. GazeForge therefore does **not** treat it as the authoritative compressed `ProcessData`/`LabelData` distribution, does not inherit rights from it, and does not allow it to satisfy empirical source-audit gates.

`George614/edit_distance_gpu` contains example code referring to separately named files such as:

```text
LabellerIdx_7_PrIdx_1_TrIdx_1.mat
LabellerIdx_8_PrIdx_1_TrIdx_1.mat
```

Those filenames are useful evidence that separately named labeller files existed in at least one working copy. They do **not** verify an authoritative source, shared gaze identity, independent-stream recoverability in the exact current distribution, or eligibility for frozen human-human agreement.

## Rights remain unresolved at dataset-file level

The Scientific Reports article is CC BY 4.0, but that article licence is not promoted to the externally hosted dataset files.

The first-author processing repository is MIT licensed for its software and associated documentation, but that software licence is not promoted to the separately distributed dataset archive.

Therefore:

- dataset-file analysis-use terms remain **unresolved**;
- dataset-file redistribution terms remain **unresolved**;
- licence inference is prohibited; and
- a recovered third-party mirror cannot change those rights fields.

## Empirical gates remain closed

This evidence does not resolve:

- current exact authoritative archive acquisition;
- exact distributed participant identities;
- complete `TrIdx→task` mapping;
- timestamp-derived distributed-file cadence;
- separately recoverable independent labeller streams;
- human-human agreement;
- participant-disjoint model validation;
- cross-dataset model performance; or
- Gazepoint GP3 validity.

A future source candidate must still pass the existing exact-file source-audit, identity, rights, cadence, coordinate, and annotation-stream checks before any empirical GIW claim can be frozen.

## Reviewed sources

- Scientific Reports publication: <https://doi.org/10.1038/s41598-020-59251-5>
- Open full-text article: <https://pmc.ncbi.nlm.nih.gov/articles/PMC7018838/>
- First-author processing repository: <https://github.com/RSKothari/Gaze-in-Wild>
- Current RIT Perception for Movement Lab: <https://www.rit.edu/science/perception-movement-lab>
- Historical distribution identifier: <http://www.cis.rit.edu/~rsk3900/gaze-in-wild/>
- Secondary transformed collection lead: <https://github.com/Morris88826/awesome-eye-data>
- Secondary labeller-filename lead: <https://github.com/George614/edit_distance_gpu>
