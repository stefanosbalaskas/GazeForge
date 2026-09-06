# Gaze-in-the-Wild historical-tree recovery

This checkpoint closes a specific provenance gap in the Gaze-in-the-Wild audit. The earlier
first-author repository-history evidence enumerated all 56 commits reachable from the pinned
repository head, but its distributed-data path check was limited to the pinned head tree. This
tranche inspects every reachable commit tree, visible refs/releases, the README endpoint history,
and the one tracked ZIP archive.

## Reachable Git history

At first-author repository commit
`52262d44e366a53369e10ca73c5f41daf0e8f1e5`, the audit covers all 56 reachable commits.
Across those trees there are no directly tracked `.mat` paths, no
`PrIdx_<P>_TrIdx_<T>.mat` or `PrIdx_<P>_TrIdx_<T>_Lbr_<N>.mat` paths, and no
`LabellerIdx_*` MAT paths. The public repository exposes no GitHub releases or tags and only the
`master` branch. Historical README revisions that provide an actual dataset location point to the
same RIT project page already frozen in the distribution-availability evidence.

Those statements apply only to objects reachable from the pinned Git history and currently visible
public refs/releases. They do not rule out deleted Git objects, historical web-hosted files,
private storage, author-held copies, or other external archives.

## Embedded first-party `ProcessData` object

The tree audit found one tracked archive,
`DataExtraction/all_preprocessing_steps.zip`, introduced by the first author in commit
`b625bd2b38d60c5f20da4704ed41dbe9ef63a78c` with the subject
`added isolated preprocessing code`. The archive itself is pinned by Git blob
`284a64bcf52e686a19a09ff65d83f2328251eb71` and SHA-256
`5deef95a4d847b7b21a37c5d746212549b63217bd64159bec72992d82b575956`.

Inside that code bundle, `exports/ProcessData.mat` is a real data-bearing MATLAB `ProcessData`
struct. Its SHA-256 is
`d633bbf0a3a9224b71e286ada10a63abe7761264eec7e8c25c94fcf0bbbafc63`.
The bounded structural audit identifies:

| Property | Frozen observation |
| --- | --- |
| Participant index | `PrIdx = 2` |
| Trial index | `TrIdx = 2` |
| Stored sampling rate | `SR = 300` |
| Timestamp count | `106,225` |
| `ETG.POR` | `106,225 × 2` |
| `ETG.Labels` | `106,225` |
| `ETG.Confidence` | `106,225` |
| `IMU.HeadVector` | `106,225 × 3` |
| `ZED.FrameNo` | `106,225` |
| `GIW.GIWvector` | `106,225 × 3` |
| Depth-present flag | `0` |

The raw local `Path2Data` value is deliberately not retained. Only its SHA-256 digest is frozen.

This is stronger first-party schema provenance than code alone: GazeForge now has an exact,
recoverable, first-party GIW `ProcessData` sample with participant/trial identity and multimodal
structure. It is **not**, however, promoted to the historical distributed
`PrIdx_2_TrIdx_2.mat` file. The archive context and generic member name do not establish byte
equivalence to that external distribution.

## Boundaries that remain closed

The ZIP contains no separate `LabelData` member and therefore does not recover the independently
distributed labeller streams. `ETG.Labels` inside the embedded `ProcessData` object is not a
substitute for that evidence. Likewise, the sample's stored `SR = 300` is a property of this
processed object and is not promoted to the acquisition-hardware cadence reported by the
publication.

The following remain false:

- full authoritative/canonical GIW distribution recovered;
- exact original-distribution equivalence verified;
- dataset-file rights resolved;
- analysis use permitted;
- redistribution authorized;
- complete participant and trial-to-task mapping verified;
- coordinate semantics verified;
- independent labeller recoverability verified;
- quarantine exit or source-audit readiness authorized;
- empirical evidence eligibility.

Accordingly, this tranche creates **provenance evidence only**. It does not authorize human-human
agreement, participant-disjoint model validation, cross-dataset performance claims, GP3 validity
claims, or Frozen Evidence performance claims.
