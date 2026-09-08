# Gaze-in-the-Wild exact ProcessData structure

GazeForge has a reviewed structural/provenance record for the **68 exact original-publication `ProcessData` files** in the official Gaze-in-the-Wild Figshare deposit. This gate is narrower than model validation: it establishes exact-file structure, processed timestamp-grid rates, recording-token pairing with distributed `LabelData`, and the applicability of already-reviewed first-party point-of-regard semantics to the exact distributed `ProcessData` structure.

## Exact source scope

The reviewed source is Figshare project `74580`:

- `ProcessData`: article `11673645`, DOI `10.6084/m9.figshare.11673645.v1`;
- `LabelData`: article `11673696`, DOI `10.6084/m9.figshare.11673696.v1`;
- `ProcessData_cleaned`: article `11673717`, deliberately excluded because it is not the original-publication distribution.

The 68 `ProcessData` files are bound to the previously reviewed exact-byte evidence and a dedicated SHA-256 ledger. Raw MAT files are streamed one at a time, verified, inspected, and deleted immediately; the repository and workflow artifact contain only JSON evidence/summary material.

## Structural result

All 68 exact original `ProcessData` files passed the reviewed gate:

- frozen Figshare size and MD5 match;
- previously reviewed SHA-256 identity matches;
- filename `PrIdx` / `TrIdx` agrees with the internal MATLAB fields;
- `ProcessData.T` is strictly increasing;
- `ETG.POR` is structurally compatible with the adapter and has `N×2` shape;
- `ETG.Confidence` and structural `ETG.Labels` match the timestamp count;
- `ETG.SceneResolution` is `1920×1080` in every file;
- no top-level `LabelData` object is embedded in a `ProcessData` file.

The exact distribution contains **68 recording tokens across 20 participant indices**.

## Processed timestamp-grid rate

Every exact file stores `ProcessData.SR = 300`. Independently, the median inverse delta of the strictly increasing `ProcessData.T` grid yields:

| Quantity | Hz |
| --- | ---: |
| Minimum | 299.98859845584474 |
| Median | 299.9948438624359 |
| Maximum | 299.9976557817862 |

These values describe the **processed `ProcessData.T` timestamp grid**. They are not promoted to the eye-tracker acquisition-hardware cadence. GazeForge continues to keep published acquisition provenance and processed-stream timing provenance separate.

The complete 68-file processed-rate ledger is frozen in:

`validation/evidence/gaze-in-wild/gaze-in-wild-processdata-processed-rate-ledger-v1.json`

## LabelData ↔ ProcessData pairing

The 50 distributed `LabelData` files represent **37 unique `PrIdx`/`TrIdx` recording tokens across 16 participants** and labeller indices `1, 2, 3, 5, 6`.

Every one of those 37 labelled recording tokens has an exact matching `ProcessData` recording token. The distribution also contains 31 `ProcessData` recording tokens without separately distributed `LabelData`.

This establishes that **task-agnostic participant-disjoint input partitioning is structurally available** for the labelled subset. It does **not** create a participant-disjoint model-validation result.

## Point-of-regard semantics

The structural result is bound to the previously reviewed first-party POR provenance evidence. At pinned first-party commit `52262d44e366a53369e10ca73c5f41daf0e8f1e5`, `ReadData_function.m` shows that `ETG.POR` derives from Pupil `norm_pos_x` / `norm_pos_y`, with the y coordinate transformed as `1-y` for MATLAB image convention, while scene resolution is retained separately.

Because all 68 exact original `ProcessData` files contain the reviewed POR/resolution structure, the first-party **normalized scene-image POR semantics** can be bound to the exact distribution. GazeForge's canonical conversion remains explicit:

- `x_px = por_x × scene_width_px`
- `y_px = por_y × scene_height_px`

This does not claim that corpus-wide observed POR value ranges have been empirically audited. That remains a separate boundary.

## What this does not establish

This evidence does not establish or authorize:

- acquisition-hardware cadence from the processed ~300 Hz grid;
- a universal `TrIdx → publication task` mapping;
- exact file-to-publication-task assignment;
- task-stratified model validation;
- participant-disjoint GazeForge model validation;
- cross-dataset validation;
- GP3 or native 60 Hz validity;
- corpus-wide observed POR-range validation;
- quarantine exit;
- any new model-performance claim.

The publication-level participant/task matrix is separately reviewed, but `TrIdx` remains a distribution-native acquisition/processing token rather than a universal task name. No task labels are inferred here.

## Reproducibility identities

Reviewed evidence:

- exact ProcessData structure evidence: `cffcc8a10d176cc5eb8c15c080cf450e3e1b1404ced00ea8907cdd4ee3c3517f`;
- exact ProcessData SHA-256 ledger: `85f131389315a1185e3a8973629c8e5ee3417bb73704de8054366e508af0a2e2`;
- ProcessData SHA-256 manifest: `162bf688fbd0bfdaf79a11d423f3689abd31bea9a4e8423bc03020ebd598354d`;
- processed-rate ledger: `1bd6643bd0c75faec9d070f74fb719f9178caa2da7e90bcbe356a0dbc5f38905`;
- stable per-file structure manifest: `d82c3db448d71676240dabc66452fa7ef3c030f8390e3b0bb0fa56b30392e7fb`;
- stable reviewed corpus-structure fingerprint: `86c4c94742ada7eceee3d44ef9c1c11a81621acd533bbb4e28aef3f6e3976443`;
- parent exact-byte evidence: `dbf277d698266fe53e337a15fc342e9af1835460d2bcc69c3992635de8fa0a00`;
- parent POR semantics evidence: `5eb245979385283571d6d9a5dda9a5d74dea6c00165bbe3a2587fcfa80e9adfb`.

Discovery run `34199996646` / job `101976365230` produced artifact `10045524274`, ZIP SHA-256 `e51138b34c6e7c4ddcc8fa3ffd825884485019bf05270072d6abee97990f638e`, and discovery probe fingerprint `bbd7b0498f4d3b48e435bb0a79efd72d794e59e38fa31ccc73c2577bb95dd66b`.

The dedicated reproduction workflow additionally validates a fresh 68-file probe against the stable per-file structure manifest and the frozen 68-row rate ledger, so retry-count transport noise cannot substitute for scientific identity.
