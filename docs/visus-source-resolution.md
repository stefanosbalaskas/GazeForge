# VISUS source-resolution status

GazeForge treats locating the VISUS benchmark as a separate scientific-provenance task from validating a local copy. The repository therefore records what the public literature and current institutional indexes establish, while refusing to turn historical availability into a current source or licensing claim.

The machine-readable checkpoint is `validation/protocols/visus-source-resolution-2026-09-04.json`. It is a **source-resolution status record, not a source-audit specification and not empirical evidence**.

## What is established

The original 2014 benchmark publication is:

> Kuno Kurzhals, Cyrill Fabian Bopp, Jochen Bässler, Felix Ebinger, and Daniel Weiskopf. *Benchmark Data for Evaluating Visualization and Analysis Techniques for Eye Tracking for Video Stimuli*. BELIV 2014. DOI: `10.1145/2669557.2669558`.

The paper describes the benchmark as publicly available and names the original distribution endpoint:

```text
http://go.visus.uni-stuttgart.de/eyetrackingBenchmark
```

It describes 11 video scenarios and 25 participants, with gaze acquired using a Tobii T60 XL at 60 Hz. The videos are 1920×1080 and normalized to 25 fps. The distributed benchmark is described as containing video stimuli, exported eye-tracking data, and dynamic AOI annotations in ViPER-compatible XML.

A 2021 Sensors paper independently reports that the VISUS dataset was downloadable from:

```text
https://www.visus.uni-stuttgart.de/publikationen/benchmark-eyetracking
```

and records an access date of 12 April 2021. This is useful historical distribution evidence; it is not proof that the same endpoint or terms remain current.

## Current resolution result

A public-source resolution pass on 2026-09-04 checked the current VISUS institutional site/indexed publication pages, the historical endpoint identifiers, the University of Stuttgart DaRUS VISUS dataverse, the ACM publication record, and general public indexing.

The current VISUS site still lists the 2014 publication on Kuno Kurzhals's institutional profile. DaRUS also contains current VISUS eye-tracking datasets. However, the search did **not locate a current authoritative distribution for this specific 2014 benchmark**, a matching DaRUS record, a separate dataset DOI, or explicit current dataset reuse terms.

Accordingly, GazeForge records:

- `current_authoritative_distribution_unresolved`;
- `current_authoritative_download_found=false`;
- `source_audit_ready=false`;
- analysis-use terms unresolved;
- raw-data redistribution terms unresolved.

Failure to locate a current distribution is not evidence that no authoritative copy exists. It means the public evidence available in this resolution pass is insufficient for GazeForge's empirical source gate.

## Copyright is not treated as a dataset license

The ACM paper contains its publication copyright/permissions notice. GazeForge does **not** reinterpret that notice as a license covering the benchmark's raw video, gaze, or AOI files. Similarly, the paper's description of the dataset as publicly available establishes historical availability, not unrestricted redistribution.

Analysis-use permission and raw-file redistribution remain separate evidence fields and must be established explicitly for the exact copy used in an empirical run.

## Annotation independence remains unverified

The paper reports that dynamic AOI annotation was performed manually by two contributors to improve annotation quality. It further explains that the first contributor performed the main annotation and the second made additional annotations and refinements.

That workflow is not evidence of two independently produced annotation streams. GazeForge therefore keeps:

- `independent_annotation_streams_verified=false`;
- `human_human_agreement_ready=false`.

Only an authoritative obtained copy that contains separately recoverable streams, together with evidence that they were produced independently, can open the human-human agreement gate.

## What must happen next

The next empirical step is not another model run. It is source acquisition and rights verification:

1. obtain the benchmark from a current VISUS/author-verified institutional source, or receive an author-verified copy;
2. document current analysis-use and raw-data redistribution terms separately;
3. inventory and hash every file in the exact obtained copy;
4. review stimulus/participant/AOI-stream identities from those files;
5. determine whether independent annotation streams actually exist;
6. only then execute the canonical human-AOI intake, documented model prediction intake, externally supplied evaluation grid, and Frozen Evidence workflow.

Until those steps are complete, the existing VISUS software remains validated infrastructure with empirical execution pending.

## Public sources used for this resolution checkpoint

- Original BELIV publication: <https://doi.org/10.1145/2669557.2669558>
- 2021 Sensors evaluation/data-availability statement: <https://doi.org/10.3390/s21124143>
- Current Kuno Kurzhals VISUS profile: <https://www.visus.uni-stuttgart.de/en/team/Kurzhals/>
- Current VISUS DaRUS dataverse: <https://darus.uni-stuttgart.de/dataverse/visus>

These references document the resolution decision. They do not replace the exact-file source audit required for empirical evidence.
