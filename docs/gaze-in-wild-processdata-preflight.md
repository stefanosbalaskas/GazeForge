# Gaze-in-the-Wild ProcessData preflight

GazeForge now has a fail-closed structural preflight for a quarantined Gaze-in-the-Wild `ProcessData` MATLAB file. The preflight exists to answer one narrow question before a candidate is allowed anywhere near the empirical source-audit path:

> Does this exact `ProcessData` object contain the structural fields consumed by GazeForge's ProcessData-side adapter, with internally compatible shapes and timestamps?

It does **not** certify the Gaze-in-the-Wild corpus, dataset rights, annotation recovery, or empirical usability.

## First-party sample used for the frozen check

The frozen record is derived from the pinned first-author repository `RSKothari/Gaze-in-Wild` at commit `52262d44e366a53369e10ca73c5f41daf0e8f1e5`. PR #78 established that the repository's sole reachable tracked archive, `DataExtraction/all_preprocessing_steps.zip`, contains one data-bearing member named `exports/ProcessData.mat`.

The preflight rechecks that exact object rather than trusting the earlier observation:

| Property | Frozen observation |
| --- | --- |
| Archive SHA-256 | `5deef95a4d847b7b21a37c5d746212549b63217bd64159bec72992d82b575956` |
| Embedded member SHA-256 | `d633bbf0a3a9224b71e286ada10a63abe7761264eec7e8c25c94fcf0bbbafc63` |
| Embedded member bytes | 40,528,499 |
| `PrIdx` | 2 |
| `TrIdx` | 2 |
| Stored `SR` | 300 Hz |
| Timestamp count | 106,225 |
| Timestamp span | 0.0–354.0851999999941 s |
| Median-difference inferred processed rate | 299.9955942810773 Hz |
| `ETG.POR` shape | 106,225 × 2 |
| `ETG.Confidence` shape | 106,225 |
| `ETG.SceneResolution` | 1920 × 1080 |
| `ETG.Labels` present | yes, 106,225 values |
| Top-level `LabelData` present | no |

The frozen preflight record fingerprint is `d2ec4cc066302646e199b88d29e6f8c165b1ce735c61f1652b8e00b1511a75dd`.

## What the preflight verifies

`preflight_gaze_in_wild_processdata()` checks the exact file hash and byte size when expected values are supplied, then verifies:

- a top-level `ProcessData` MATLAB variable;
- positive scalar `PrIdx`, `TrIdx`, and `SR` values;
- finite, strictly increasing `ProcessData.T` values and a timestamp-derived processed rate;
- numeric `ETG.POR` with either `N × 2` or `2 × N` shape matching `T`;
- `ETG.Confidence` length matching `T`, while preserving the adapter's ability to treat non-finite confidence values as invalid samples rather than structural corruption;
- positive integer `ETG.SceneResolution` width and height;
- optional `ETG.Labels`, which must match `T` when present.

The workflow reproduces these observations from the exact pinned first-author Git revision and requires the live record to equal the committed frozen record exactly.

## Scientific boundary

The only positive scientific-governance conclusions from this tranche are:

1. this exact first-party embedded `ProcessData` object passes the structural preflight; and
2. the ProcessData fields consumed by GazeForge's coordinate adapter are structurally compatible **for this one sample**.

Everything stronger remains closed. In particular:

- `exports/ProcessData.mat` is **not** claimed byte-equivalent to the historical distributed `PrIdx_2_TrIdx_2.mat`;
- the full/canonical Gaze-in-the-Wild distribution has not been recovered;
- `ETG.Labels` is **not** treated as separately distributed `LabelData` and does not recover independent human-labeller streams;
- the stored 300 Hz value and the approximately 299.996 Hz timestamp grid describe this processed object only; neither establishes the published acquisition-hardware cadence or a corpus-wide sampling-rate distribution;
- the presence and shape of `ETG.POR` and `ETG.SceneResolution` do not independently certify the coordinate semantics of the historical distribution;
- participant/task mapping is incomplete;
- dataset-file rights, analysis permission, and redistribution permission remain unresolved;
- quarantine exit and full source-audit readiness remain false; and
- no human-agreement, model-validation, cross-dataset, GP3, or Frozen Evidence performance claim is created.

## Relationship to the full source audit

This preflight is intentionally weaker than `GazeInWildSourceAuditSpec` in `gazeforge.gaze_in_wild_audit`. The full empirical audit still requires authoritative `LabelData` and `ProcessData` manifests, exact file identities, verified reuse terms, explicit analysis-use permission, participant/task identity mapping, coordinate evidence, and the remaining source-audit invariants.

A future recovered corpus can therefore pass through this preflight while still remaining quarantined. Structural compatibility is useful evidence, but it is not authorization and it is not empirical certification.
