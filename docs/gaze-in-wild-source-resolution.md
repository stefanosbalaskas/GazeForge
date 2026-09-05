# Gaze-in-the-Wild source-resolution status

GazeForge treats **published availability**, **authoritative processing provenance**, **current direct retrievability**, **exact-file identity**, and **reuse permission** as separate scientific-provenance questions. This page records the current public-source resolution status of the Gaze-in-the-Wild benchmark without turning source-code provenance into a completed empirical source audit.

The machine-readable checkpoint is:

```text
validation/protocols/gaze-in-wild-source-resolution-2026-09-04.json
```

It is a **source-resolution status record, not empirical evidence**.

## What the publication establishes

The authoritative dataset publication is:

> Rakshit Kothari, Zhizhuo Yang, Christopher Kanan, Reynold Bailey, Jeff B. Pelz, and Gabriel J. Diaz.
> *Gaze-in-wild: A dataset for studying eye and head coordination in everyday activities*.
> Scientific Reports 10, 2539 (2020). DOI: `10.1038/s41598-020-59251-5`.

The paper reports data from 19 participants performing up to four naturalistic tasks: indoor navigation, ball catching, object search, and tea making. The acquisition system included 120 Hz binocular Pupil Labs eye-tracking glasses, an MPU-6050 IMU, and a ZED stereo RGB-D camera. A substantial portion of the data was hand labelled by five trained annotators.

The paper explicitly states that the annotators made decisions independently. That is legitimate published evidence about the annotation procedure. It is still distinct from verifying, in the exact distributed files, which independent streams are separately recoverable and whether they share exactly the same underlying gaze samples.

The paper's data-availability statement identifies:

```text
http://www.cis.rit.edu/~rsk3900/gaze-in-wild/
```

as the location of compressed data and code.

## First-author processing repository now pinned

A first-author repository has now been verified and pinned:

```text
https://github.com/RSKothari/Gaze-in-Wild
commit 52262d44e366a53369e10ca73c5f41daf0e8f1e5
```

This repository is authoritative for the processing code and documentation used to build and maintain the dataset. GazeForge binds the source-resolution record to exact Git blobs for `README.md`, `License.md`, `DataExtraction/GetParticipantInfo.m`, and `DataExtraction/ReadData_function.m` rather than relying on a moving branch head.

The repository materially resolves two earlier ambiguities. First, its README documents that the Pupil Labs gaze and IMU streams were processed and upsampled to **300 Hz**, while the publication's **120 Hz** value describes the eye-tracker acquisition hardware. Second, the official processing function defines the point-of-regard coordinate representation used in `ProcessData`.

This does **not** mean the external compressed dataset archive has been obtained or audited. `source_audit_ready` therefore remains false and no Gaze-in-the-Wild performance or human-agreement result is frozen by this tranche.

## Current direct-data resolution remains incomplete

The current RIT Perception for Movement Lab page lists **The Gaze-In-Wild Dataset** under Software/Data, but the surfaced link resolves to the publication record rather than a direct data archive. The historical RIT data URL remains the identifier used by the publication and the first-author repository, but a current exact compressed-data copy has not yet been retrieved and fingerprinted in this project.

GazeForge therefore records:

```text
authoritative_processing_repository_verified_direct_dataset_copy_unverified
```

with:

- `published_distribution_identifier_found=true`;
- `official_processing_repository_verified=true`;
- `current_institutional_dataset_listing_found=true`;
- `current_direct_data_endpoint_verified=false`;
- `source_audit_ready=false`;
- `empirical_evidence_created=false`.

A failed or unavailable direct retrieval is **not** evidence that the benchmark has disappeared. It means the exact distributed copy has not yet passed GazeForge's file-identity and reuse-term gates.

## Rights scopes remain separate

The Scientific Reports article is published under CC BY 4.0. GazeForge does **not** infer from the article license that the externally hosted gaze, imagery, annotation, or other dataset files are covered by the same terms.

The first-author GitHub repository contains an **MIT** `License.md`. Its text licenses the repository's “Software” and associated documentation. GazeForge records that software licence but does not silently promote it to the separately hosted compressed dataset archive. The exact dataset-file analysis and redistribution terms remain unresolved.

Accordingly:

- article CC BY 4.0 is article-level rights evidence;
- repository MIT is software/documentation rights evidence;
- dataset-file analysis-use terms remain unresolved; and
- dataset-file raw redistribution terms remain unresolved.

Published availability is not treated as unrestricted redistribution permission.

## The 120 Hz / 300 Hz distinction is now provenance-resolved

The apparent rate discrepancy is no longer treated as two competing descriptions of the same stage. The primary paper documents **120 Hz acquisition hardware**, while the pinned first-author repository documents processing and upsampling of gaze and IMU streams to **300 Hz**. A later event-detection catalog's 300 Hz description is therefore consistent with the processed benchmark stage.

This provenance reconciliation does not authorize a hard-coded analysis cadence. GazeForge still requires the actual analysis cadence from timestamps in each audited `LabelData` stream. The empirical source audit must therefore preserve all three ideas separately:

- 120 Hz acquisition-hardware provenance;
- 300 Hz processed-stream target provenance; and
- timestamp-inferred cadence of each exact distributed label stream.

No empirical runner may substitute either nominal rate for the measured file cadence.

## Point-of-regard semantics are now resolved at the official-code level

The pinned `DataExtraction/ReadData_function.m` provides an authoritative construction of `ProcessData.ETG.POR`. It assigns Pupil Labs normalized point-of-regard coordinates from `norm_pos_x` and `norm_pos_y`, then transforms the vertical coordinate as:

```text
1 - norm_pos_y
```

for MATLAB image coordinates. The same official function stores:

```text
ETG.SceneResolution = [1920, 1080]
```

Thus `ETG.POR` is **normalized scene-camera position**, not a pixel vector. GazeForge now converts process-backed POR values into canonical `x_px`/`y_px` using the recorded scene width and height, while retaining the normalized source semantics in metadata. Missing or invalid `ETG.SceneResolution` is rejected rather than guessed.

This resolves the processing-schema coordinate semantics and the 1920 × 1080 pixel-conversion basis. It does **not** claim that an exact current compressed-data copy has already been checked file-by-file for those fields. That verification remains part of the empirical source audit.

## Participant/trial metadata is authoritative but does not yet identify the published subset

The pinned `GetParticipantInfo.m` establishes numeric `PrIdx` and `TrIdx` acquisition identities and contains participant metadata through index 23. The publication, however, reports 19 participants. GazeForge therefore refuses to infer that every acquisition-metadata entry belongs to the published benchmark or that trial numbers map to the four named tasks in publication order.

Before participant-disjoint validation, an authoritative exact distribution or supplementary mapping must establish:

1. the exact 19-participant included set;
2. the mapping from distributed `PrIdx`/recording identity to participant;
3. the mapping from `TrIdx` to the four task semantics; and
4. the one-to-one pairing between each `LabelData` stream and its `ProcessData` source.

This prevents an apparently plausible filename convention from being promoted to an unverified scientific identity mapping.

## Independent annotation is published, but file-level recoverability still needs verification

The paper reports five trained annotators and states that each labeller made decisions independently. The official repository also documents that `LabelData` may contain multiple labellers. This supports the dataset as a strong candidate for human-human agreement analysis.

Frozen agreement nevertheless remains blocked until an exact authoritative copy verifies:

1. the independently labelled streams are separately recoverable;
2. participant/task/labeller identities are unambiguous;
3. overlapping streams refer to the same `ProcessData` source;
4. timestamps and underlying gaze samples are identical before labels are compared; and
5. every file is bound to the audited source manifest.

Human disagreement, once measured on those verified streams, is a reference-variability result — not an error-free ground-truth ceiling.

## What must happen next

The next empirical actions are:

1. obtain an exact current compressed-data copy from the published RIT distribution or an author-verified institutional source;
2. verify dataset-file analysis-use and raw-data redistribution terms separately from the article and repository-software licences;
3. inventory and SHA-256 fingerprint all `LabelData` and `ProcessData` files;
4. resolve the exact 19-participant included set and task mapping;
5. verify label-to-process pairing and confirm POR/scene-resolution fields against the pinned official processing schema;
6. infer every audited label stream's actual cadence from timestamps;
7. verify independently recoverable overlapping labeller streams and freeze human-human agreement; and
8. run participant-disjoint model validation with naturalistic-task and event-class sensitivity.

Until those gates pass, the Gaze-in-the-Wild software remains **validated audit/analysis infrastructure with empirical execution pending**.

Gaze-in-the-Wild is complementary naturalistic head-mounted evidence. It is **not Gazepoint GP3** validation and must not be used as a substitute for a native 60 Hz/GP3-class expert-labelled corpus.

## Public sources used for this checkpoint

- Scientific Reports dataset publication: <https://doi.org/10.1038/s41598-020-59251-5>
- Open full-text publication copy: <https://pmc.ncbi.nlm.nih.gov/articles/PMC7018838/>
- First-author processing repository: <https://github.com/RSKothari/Gaze-in-Wild>
- Current RIT Perception for Movement Lab: <https://www.rit.edu/science/perception-movement-lab>
- Event-detection evaluation replication repository: <https://github.com/r-zemblys/EM-event-detection-evaluation>
- Practical guide listing open-access mobile eye-tracking data: <https://pmc.ncbi.nlm.nih.gov/articles/PMC11525247/>
- Published RIT distribution identifier: <http://www.cis.rit.edu/~rsk3900/gaze-in-wild/>

These sources document the resolution decision. They do not replace an exact-file source audit.
