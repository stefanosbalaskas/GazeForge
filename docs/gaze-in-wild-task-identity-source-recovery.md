# Gaze-in-the-Wild task-identity source recovery

This page records a bounded negative source-recovery result for the **Gaze-in-the-Wild (GIW)** benchmark. Its purpose is to answer a narrow question: does the pinned first-author repository contain an explicit task-to-`TrIdx` mapping that is strong enough to connect distributed `PrIdx_*_TrIdx_*.mat` files to the four publication tasks without inference?

## Result

**No explicit mapping was recovered from the reviewed first-party route.**

The probe is pinned to:

- repository: `https://github.com/RSKothari/Gaze-in-Wild`;
- commit: `52262d44e366a53369e10ca73c5f41daf0e8f1e5`;
- 56 reachable commits;
- 302 unique text blobs across the reachable history;
- exact `GIWApp.mlapp` Git blob `2d560af336af637e042ea7a96f4c3736a59d2a2f`.

The MATLAB app is a nine-member container. Its reviewed UTF-8 and printable-string surfaces contain **zero task contexts**. Across the reachable text history, only one blob is task-related: `PlotLabels.m`, which contains the local path fragment `GIW_rearranged/Indoor_Walk`. The recovered task contexts contain **no nearby explicit `TrIdx = N` assignment**. The deterministic probe therefore reports `identity_plus_tridx_candidate_context_count = 0`.

The frozen evidence fingerprint is:

```text
caac3aebc99be005f8c2dcf431041e1d727b9ca07f2e4509c06d40b4f3452212
```

The discovery probe was produced by workflow run `34163709562`, artifact `10033447214`, at exact GazeForge head `a7b21c151439e03ad29e4e157024f83062186bab`.

## What this closes

This tranche closes the reviewed **pinned first-party plain-text / printable-string task-identity recovery route**. Re-running the dedicated workflow checks the same exact upstream revision and requires the source inventory, MLAPP identity, task-context counts, and fail-closed scientific boundary to remain consistent with the frozen evidence.

This is useful negative evidence: it prevents future work from repeatedly treating the MATLAB app or reachable source history as though they contained an undiscovered explicit lookup.

## What it does not establish

The result is deliberately narrower than “no mapping exists.” It does **not** exclude mappings that may exist in:

- private or author-held materials;
- deleted or unreachable Git objects;
- external project storage or archived web material;
- semantically encoded binary structures not exposed as reviewed printable strings;
- the actual distributed data contents after exact-byte acquisition.

The `Indoor_Walk` path is therefore **not** promoted into a universal `TrIdx = 1` rule. Likewise, publication label-status patterns and the Figshare LabelData filename inventory can constrain some participant/trial cells, but zero-labelled trials remain ambiguous between publication states such as *not labelled* and *discarded*. Those constraints are not a substitute for an authoritative file-to-task ledger.

## Scientific boundary

This tranche creates **no new empirical performance evidence**. The following remain false:

- universal `TrIdx` → task mapping verified;
- complete distributed-file → task mapping verified;
- participant-disjoint GIW model validation created;
- GIW human-human agreement created;
- cross-dataset validation created;
- native GP3 validity established;
- GIW quarantine exit authorized.

The next scientifically useful GIW work must therefore obtain stronger external evidence—most importantly exact distributed bytes and/or an authoritative task/file mapping—before participant-generalisation or cross-dataset performance claims can be created.

## Reproduce

The dedicated workflow runs:

```bash
python scripts/probe_gaze_in_wild_task_identity_recovery.py \
  _giw_source \
  --output gaze-in-wild-task-identity-recovery-probe-v1.json
```

It then validates the live observation against the frozen [`gaze-in-wild-task-identity-source-recovery-evidence-v1.json`](https://github.com/stefanosbalaskas/GazeForge/blob/main/validation/evidence/gaze-in-wild/gaze-in-wild-task-identity-source-recovery-evidence-v1.json) and runs adversarial tests that reject attempts to promote the negative result into a universal mapping or model-validity claim.
