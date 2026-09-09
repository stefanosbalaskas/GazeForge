# Gaze-in-the-Wild task-mapping corroboration

GazeForge keeps **authoritative task identity** separate from secondary corroboration. The reviewed exact Gaze-in-the-Wild participant-disjoint benchmark remains task-agnostic until a first-party or otherwise authoritative source verifies the distributed `TrIdx` → publication-task mapping.

## Secondary ACE-DNV evidence

The 2024 ACE-DNV study by Nejad et al. uses the Gaze-in-the-Wild dataset and explicitly describes the four activities as indoor walking, throwing/catching a ball, visual search, and making tea. Its public analysis repository contains participant/trial selection files that explicitly name three trial indices:

| `TrIdx` | ACE-DNV task label | Publication-normalized candidate | Observed participants in reviewed ACE-DNV files |
| ---: | --- | --- | --- |
| 1 | `Indoor_Walk` | `indoor_navigation` | 1, 2, 3, 6, 8, 10, 12, 17, 18, 22 |
| 2 | `Ball_Catch` | `ball_catching` | 1, 2, 3, 6, 12, 16, 17 |
| 3 | `Visual_Search` | `visual_search` | 8, 12, 19 |
| 4 | **unresolved** | **unresolved** | no explicit task-4 label in the reviewed ACE-DNV selection files |

The evidence is pinned to ACE-DNV repository commit `3142eb4457087743664d96994e952ed784741d1f` and tree `e52618478ba53f945b32f8056df297cf61c85f93`. Exact reviewed file/blob identities are frozen in:

`validation/evidence/gaze-in-wild/gaze-in-wild-ace-dnv-task-mapping-corroboration-evidence-v1.json`

Evidence fingerprint:

```text
e16aa3eea5c354ae0c6cb159cb3bdcaede19dfa535fdf23798f9fae3d35154b5
```

Paper DOI: `10.3758/s13428-024-02358-8`.

## Why this does not close the mapping gate

ACE-DNV is a **secondary methodological study**, not the first-party Gaze-in-the-Wild distribution or an authoritative mapping specification. Its code is strong independent corroboration for `TrIdx` 1–3, but GazeForge does not convert that corroboration into authoritative task identity.

In particular, `TrIdx 4 → Tea_Making` is **not inferred by elimination**. The fact that the publication names four tasks while the reviewed ACE-DNV selection files explicitly name only three is insufficient to promote a fourth mapping under the fail-closed evidence policy.

Accordingly, this tranche does **not** authorize:

- a complete `TrIdx` → publication-task mapping;
- task labels in the frozen exact participant-disjoint performance report;
- task-stratified Gaze-in-the-Wild validation;
- new empirical-performance claims;
- cross-dataset claims;
- native-60-Hz or Gazepoint GP3 validity;
- acquisition-hardware cadence claims;
- quarantine exit.

The next mapping gate remains recovery of a first-party/authoritative source that explicitly binds distributed trial indices to publication tasks, including trial 4.
