# Gaze-in-the-Wild source-resolution status

GazeForge treats **published availability**, **authoritative processing provenance**, **repository history**, **current direct retrievability**, **exact-file identity**, and **reuse permission** as separate scientific-provenance questions. This page records the current public-source resolution status of the Gaze-in-the-Wild benchmark without turning processing-code provenance into a completed empirical source audit.

The active source-resolution checkpoint is:

```text
validation/protocols/gaze-in-wild-source-resolution-2026-09-04.json
```

Reviewed supporting evidence now also includes:

```text
validation/evidence/gaze-in-wild/gaze-in-wild-supplementary-identity-evidence-v1.json
validation/evidence/gaze-in-wild/gaze-in-wild-repository-history-evidence-v1.json
```

These are **provenance/governance evidence, not model-performance Frozen Evidence**.

## What the publication establishes

The authoritative dataset publication is:

> Rakshit Kothari, Zhizhuo Yang, Christopher Kanan, Reynold Bailey, Jeff B. Pelz, and Gabriel J. Diaz.
> *Gaze-in-wild: A dataset for studying eye and head coordination in everyday activities*.
> Scientific Reports 10, 2539 (2020). DOI: `10.1038/s41598-020-59251-5`.

The paper reports 19 participants performing up to four naturalistic tasks: indoor navigation, ball catching, visual search, and tea making. The acquisition system included 120 Hz binocular Pupil Labs eye-tracking glasses, an MPU-6050 IMU, and a ZED stereo RGB-D camera. A substantial portion of the data was hand labelled by five trained annotators.

The paper states that annotators made decisions independently. That is legitimate publication-level annotation-procedure evidence. It remains distinct from verifying, in the exact distributed files, which independent streams are separately recoverable and whether they share exactly the same underlying gaze samples.

The paper's data-availability statement identifies:

```text
http://www.cis.rit.edu/~rsk3900/gaze-in-wild/
```

as the location of compressed data and code.

## First-author processing repository is pinned

The first-author processing repository is pinned at:

```text
https://github.com/RSKothari/Gaze-in-Wild
commit 52262d44e366a53369e10ca73c5f41daf0e8f1e5
tree   c0fa1ae13c101a8d95b09370970a6012ea97a3d9
```

GazeForge binds the source-resolution record to exact Git blobs for `README.md`, `License.md`, `DataExtraction/GetParticipantInfo.m`, `DataExtraction/ReadData_function.m`, and `PlotLabels.m` rather than relying on a moving branch head.

The repository resolves two important processing ambiguities. Its README documents that Pupil Labs gaze and IMU streams were processed and upsampled to **300 Hz**, whereas the publication's **120 Hz** value describes eye-tracker acquisition. The official processing code also defines the normalized point-of-regard representation and its conversion context.

This does **not** mean that the externally hosted compressed dataset archive has been obtained or audited. `source_audit_ready` remains false and no Gaze-in-the-Wild performance or human-agreement result is frozen by these provenance tranches.

## Complete reachable repository history is now reviewed

A deterministic full-history probe now verifies **all 56 commits reachable from the pinned first-author repository HEAD**, from root commit:

```text
054c99d3b88f0ad46cbd0b7d66f4fc38718046f5
```

to the pinned head above. The reviewed probe has fingerprint:

```text
d0cc0212d77e24f07412ddb22e7743c9e9621be8d2ec73ef087b231c77893f11
```

and the immutable reviewed evidence record has fingerprint:

```text
800d84d71d1d4b1a07e3b6d07c3bb7093c679284f49db0930a9836d77da30ad3
```

The full-history audit establishes the following repository facts without expanding the claim scope:

- the complete reachable history contains 56 commits;
- the observed Git author-name forms are `RSKothari` and `rakshit`;
- `README.md` has six distinct reviewed blob versions in reachable history;
- the README begins directing users to the historical RIT project webpage for all data files from commit `31977aa3aa6e08dc34fafb6cc1bd8c29c79870ca` onward;
- `License.md` first appears at commit `76dc9cd3a276252ef1913ef1b70e4e001dd76cdf`;
- the pinned `License.md` blob is `b6f41e2ee0550feabd3938efc7d93ae24c491903` and identifies **The MIT License**;
- the pinned repository tree contains 178 tracked paths; and
- no tracked `ProcessData`/`LabelData`-like MATLAB dataset file is present at the pinned repository HEAD.

The absence of the distributed dataset files from this code repository is important: the repository is authoritative processing provenance, **not the exact compressed dataset distribution**.

## Current direct-data resolution remains incomplete

The current RIT Perception for Movement Lab page lists **The Gaze-In-Wild Dataset** under Software/Data, but the surfaced link resolves to the publication record rather than a direct data archive. The historical RIT data URL remains the distribution identifier used by the publication and first-author repository, but a current exact compressed-data copy has not yet been retrieved and fingerprinted in this project.

GazeForge therefore keeps the current direct-copy state unresolved:

- `published_distribution_identifier_found=true`;
- `official_processing_repository_verified=true`;
- `current_institutional_dataset_listing_found=true`;
- `current_direct_data_endpoint_verified=false`;
- `source_audit_ready=false`;
- `empirical_evidence_created=false`.

A failed or unavailable direct retrieval is **not** evidence that the benchmark has disappeared. It means the exact distributed copy has not yet passed GazeForge's file-identity and reuse-term gates.

## Rights scopes remain separate

The Scientific Reports article is published under CC BY 4.0. GazeForge does **not** infer from the article licence that the externally hosted gaze, imagery, annotation, or other dataset files are covered by those terms.

The first-author GitHub repository contains an MIT `License.md` whose text grants rights for the repository's **software and associated documentation files**. The complete-history audit verifies when that software licence entered the repository, but it does not promote it to the separately hosted `ProcessData`/`LabelData` archive.

Accordingly:

- article CC BY 4.0 is article-level rights evidence;
- repository MIT is software/documentation rights evidence;
- dataset-file analysis-use terms remain unresolved; and
- dataset-file raw redistribution terms remain unresolved.

Published availability is not treated as unrestricted redistribution permission.

## The 120 Hz / 300 Hz distinction is provenance-resolved

The apparent rate discrepancy is not treated as two competing descriptions of the same stage. The primary paper documents **120 Hz acquisition hardware**, while the pinned first-author repository documents processing and upsampling of gaze and IMU streams to **300 Hz**. A later event-detection catalog's 300 Hz description is therefore consistent with the processed benchmark stage.

This provenance reconciliation does not authorize a hard-coded analysis cadence. GazeForge still requires the actual cadence from timestamps in each audited distributed stream. Empirical work must preserve separately:

- 120 Hz acquisition-hardware provenance;
- 300 Hz processed-stream target provenance; and
- timestamp-inferred cadence of each exact distributed file.

No empirical runner may substitute either nominal rate for measured file cadence.

## Point-of-regard semantics are resolved at official-code level

The pinned `DataExtraction/ReadData_function.m` constructs `ProcessData.ETG.POR` from Pupil Labs normalized point-of-regard coordinates and transforms the vertical coordinate as:

```text
1 - norm_pos_y
```

for MATLAB image coordinates. The same official function stores:

```text
ETG.SceneResolution = [1920, 1080]
```

Thus `ETG.POR` is **normalized scene-camera position**, not a pixel vector. GazeForge can convert process-backed POR values to canonical pixels using the recorded scene width and height while retaining the normalized source semantics in metadata. Missing or invalid `ETG.SceneResolution` is rejected rather than guessed.

This resolves official processing-schema coordinate semantics and the 1920 × 1080 conversion basis. It does **not** claim that an exact compressed-data copy has already been checked file-by-file for those fields.

## Publication-level participant set is now verified; distributed-file mapping is not

Supplementary Table 1 now provides a verified publication-level 19-person set:

```text
1, 2, 3, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23
```

The four published task columns are also verified as **Indoor navigation**, **Ball catching**, **Visual search**, and **Tea making**. Processing indices `4`, `5`, `7`, and `21` are outside that published 19-person table.

This materially improves the provenance state, but it does not prove that a distributed file named with a particular `PrIdx` is the exact publication-table person without auditing the actual distribution. Nor does it establish a complete global `TrIdx→task` mapping. `PlotLabels.m` contains `TrIdx=1` / `Indoor_Walk` context, but that is not promoted to a complete mapping for all tasks and files.

A further reason to avoid demographic joins is the preserved participant-18 age discrepancy: Supplementary Table 1 gives age `34`, whereas pinned processing metadata gives `45`. Age is therefore explicitly unsuitable as an identity key.

Before participant-disjoint validation, an exact audited distribution must still establish:

1. the mapping from each distributed participant/file identity to the verified publication person number;
2. the complete mapping from distributed trial identities to task semantics;
3. the one-to-one pairing between each `LabelData` stream and its `ProcessData` source; and
4. the participant/task/labeller identity of every empirical stream used in a split.

## Independent annotation is published, but file-level recoverability still needs verification

The paper reports five trained annotators and states that each labeller made decisions independently. The official repository also documents that `LabelData` may contain multiple labellers. This supports the dataset as a strong candidate for human-human agreement analysis.

Frozen agreement nevertheless remains blocked until an exact authoritative copy verifies:

1. independently labelled streams are separately recoverable;
2. participant/task/labeller identities are unambiguous;
3. overlapping streams refer to the same `ProcessData` source;
4. timestamps and underlying gaze samples are identical before labels are compared; and
5. every file is bound to the audited source manifest.

Human disagreement, once measured on those verified streams, is a reference-variability result — not an error-free ground-truth ceiling.

## What must happen next

The next empirical actions are:

1. obtain and SHA-256 fingerprint an exact current or preserved authoritative compressed-data copy;
2. verify dataset-file analysis-use and raw-data redistribution terms separately from article and repository-software licences;
3. inventory all `LabelData` and `ProcessData` files;
4. bind distributed participant identities to the already verified publication-level 19-person set and resolve complete task mapping;
5. verify label-to-process pairing and confirm POR/scene-resolution fields against the pinned official processing schema;
6. infer every audited stream's actual cadence from timestamps;
7. verify separately recoverable overlapping independent labeller streams and freeze human-human agreement; and
8. only then run participant-disjoint model validation with naturalistic-task and event-class sensitivity.

Until those gates pass, Gaze-in-the-Wild remains **validated provenance/audit infrastructure with empirical execution pending**.

Gaze-in-the-Wild is complementary naturalistic head-mounted evidence. It is **not Gazepoint GP3** validation and must not be used as a substitute for a native 60 Hz/GP3-class expert-labelled corpus.

## Public sources used for these checkpoints

- Scientific Reports dataset publication: <https://doi.org/10.1038/s41598-020-59251-5>
- Open full-text publication copy: <https://pmc.ncbi.nlm.nih.gov/articles/PMC7018838/>
- First-author processing repository: <https://github.com/RSKothari/Gaze-in-Wild>
- Current RIT Perception for Movement Lab: <https://www.rit.edu/science/perception-movement-lab>
- Event-detection evaluation replication repository: <https://github.com/r-zemblys/EM-event-detection-evaluation>
- Practical guide listing open-access mobile eye-tracking data: <https://pmc.ncbi.nlm.nih.gov/articles/PMC11525247/>
- Published RIT distribution identifier: <http://www.cis.rit.edu/~rsk3900/gaze-in-wild/>

These sources document provenance decisions. They do not replace an exact-file source audit.
