# Gaze-in-the-Wild task-mapping corroboration

GazeForge keeps **publication task identity**, **first-party extraction structure**, **secondary numeric corroboration**, and **authoritative distributed file-to-task mapping** as separate evidence layers. The reviewed exact Gaze-in-the-Wild participant-disjoint benchmark therefore remains task-agnostic until a first-party or otherwise authoritative source explicitly verifies the distributed `TrIdx` → publication-task mapping.

## Current evidence ladder

| Evidence question | Current status |
| --- | --- |
| Are the four publication tasks known? | **Yes** — indoor navigation, ball catching, visual search, tea making |
| Does first-party RIT code preserve task-separated GIW extraction directories? | **Yes** |
| Does that first-party code read `PrIdx` and `TrIdx` from each task directory's `ProcessData` and use them to address raw recordings? | **Yes** |
| Are `TrIdx` 1–3 numerically corroborated by an independent downstream study? | **Yes** — ACE-DNV |
| Does a reviewed first-party source explicitly publish the complete numeric `TrIdx` → task lookup? | **No** |
| Is `TrIdx 4 → Tea_Making` authorized? | **No** — it is not inferred by elimination |
| Is task-stratified GIW validation authorized? | **No** |

## First-party PerForm Lab / RIT structural evidence

A public Rochester Institute of Technology repository, `PerForm-Lab-RIT/Pupil-Labs-Core-RITnet-Plugins`, contains `ritnet/Ellseg_v2/dataset_generation/ExtractedGIW.py`. The script's in-file metadata identifies `@author: rakshit` and describes itself as extracting data from the **Gaze-in-the-Wild project**.

The reviewed source explicitly defines:

```text
['Indoor_Walk', 'Ball_Catch', 'Visual_Search', 'Tea_Making']
```

and, for each task directory, addresses:

```text
extracted_data/<task>/ProcessData_cleaned
```

It then loads each `ProcessData`, reads `PrIdx` and `TrIdx`, and uses those identities to address the raw recording tree at:

```text
<path_data>/<PrIdx>/<TrIdx>/Gaze
```

This is **first-party structural corroboration** that the GIW processing code maintained task-separated extracted data while retaining participant/trial identities. It is materially stronger provenance than a secondary replication source.

The source is pinned to:

- repository: `PerForm-Lab-RIT/Pupil-Labs-Core-RITnet-Plugins`
- commit: `ebec5d1db118e39de60a14160f09ee33cd7f3b5d`
- tree: `67af6104f7d52c969be7737b04fa349be6a2ec4f`
- file blob: `ae51e50eb9f3d224417d1fd24253052196480870`
- path: `ritnet/Ellseg_v2/dataset_generation/ExtractedGIW.py`

Frozen GazeForge evidence:

`validation/evidence/gaze-in-wild/gaze-in-wild-perform-lab-task-structure-corroboration-evidence-v1.json`

Evidence fingerprint:

```text
2352b5969285c4d3d182035570b3a3b76461fa683e50d69cf4ff0e2f6a827aec
```

### Why the first-party evidence still does not close the numeric mapping gate

The reviewed script iterates the four named task directories and reads `TrIdx` from the `ProcessData` files inside each directory, but it does **not** itself enumerate a numeric lookup such as `1 → Indoor_Walk` or `4 → Tea_Making`. The code therefore verifies structure and identity linkage, not the complete distributed numeric mapping.

GazeForge deliberately does not turn list order, task-directory order, or the remaining unmatched publication task into a numeric mapping rule.

## Secondary ACE-DNV numeric corroboration

The 2024 ACE-DNV study by Nejad et al. uses Gaze-in-the-Wild and explicitly describes the four activities as indoor walking, throwing/catching a ball, visual search, and making tea. Its public analysis repository contains participant/trial selection files that explicitly name three trial indices:

| `TrIdx` | ACE-DNV task label | Publication-normalized candidate | Observed participants in reviewed ACE-DNV files |
| ---: | --- | --- | --- |
| 1 | `Indoor_Walk` | `indoor_navigation` | 1, 2, 3, 6, 8, 10, 12, 17, 18, 22 |
| 2 | `Ball_Catch` | `ball_catching` | 1, 2, 3, 6, 12, 16, 17 |
| 3 | `Visual_Search` | `visual_search` | 8, 12, 19 |
| 4 | **unresolved** | **unresolved** | no explicit task-4 label in the reviewed ACE-DNV selection files |

The ACE-DNV evidence is pinned to repository commit `3142eb4457087743664d96994e952ed784741d1f` and tree `e52618478ba53f945b32f8056df297cf61c85f93`. Exact reviewed file/blob identities are frozen in:

`validation/evidence/gaze-in-wild/gaze-in-wild-ace-dnv-task-mapping-corroboration-evidence-v1.json`

Evidence fingerprint:

```text
e16aa3eea5c354ae0c6cb159cb3bdcaede19dfa535fdf23798f9fae3d35154b5
```

Paper DOI: `10.3758/s13428-024-02358-8`.

## Scientific boundary

The combined first-party structural evidence plus ACE-DNV numeric corroboration substantially narrows the open problem, but it does **not** authorize:

- a complete or authoritative `TrIdx` → publication-task mapping;
- `TrIdx 4 → Tea_Making` by elimination;
- task labels in the frozen exact participant-disjoint performance report;
- task-stratified Gaze-in-the-Wild validation;
- new empirical-performance claims;
- cross-dataset claims;
- native-60-Hz or Gazepoint GP3 validity;
- acquisition-hardware cadence claims;
- quarantine exit.

The next mapping gate is now narrower: recover a first-party distribution manifest, source file, task table, or equivalent authoritative record that explicitly binds the distributed numeric trial identities to publication tasks, including trial 4.
