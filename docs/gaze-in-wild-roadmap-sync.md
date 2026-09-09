# Gaze-in-the-Wild roadmap evidence synchronization

This checkpoint synchronizes two stale roadmap entries with empirical evidence that is already frozen in the repository. It does **not** rerun the underlying science and does not widen any Gaze-in-the-Wild claim.

## Scoped items now supported

| Roadmap item | Evidence-backed status | Scope boundary |
| --- | --- | --- |
| Per-file sampling-rate distribution | **Satisfied, with corrected wording** | 68 distributed `ProcessData` files; rate inferred from each file's strictly increasing processed `T` timestamp grid. This is a **processed-stream timestamp-grid rate**, not acquisition-hardware cadence. |
| Labeller-to-labeller sample/event agreement | **Satisfied, with corrected wording** | Six labeller pairs across the five distributed recordings that actually contain multi-labeller overlap. This is **overlap-subset HHA**, not full-distribution HHA. |

The synchronization evidence is frozen at:

`validation/evidence/gaze-in-wild/gaze-in-wild-roadmap-evidence-sync-v1.json`

Evidence fingerprint:

```text
c0dc3182f7fa89d325e0be2406d6d1aaf6541ebb2e90c21f49ade23398909571
```

## ProcessData processed timestamp-grid rate ledger

The upstream rate ledger is:

`validation/evidence/gaze-in-wild/gaze-in-wild-processdata-processed-rate-ledger-v1.json`

Fingerprint:

```text
1bd6643bd0c75faec9d070f74fb719f9178caa2da7e90bcbe356a0dbc5f38905
```

It contains **68 exact distributed ProcessData file identities**. For every file it records the stored `ProcessData.SR` processing-rate field and the rate inferred as the median inverse delta of the strictly increasing `ProcessData.T` processed timestamp grid. The stored field is 300 Hz and the timestamp-inferred processed rates are correspondingly near 300 Hz.

This evidence is deliberately narrower than an acquisition-cadence statement. It does **not** verify the hardware acquisition rate, native 60 Hz evidence, or Gazepoint GP3 validity.

The dedicated validator `validate_gaze_in_wild_processed_rate_ledger()` now re-hashes the complete frozen ledger, enforces the 68-file scope and exact semantics, checks every row structurally, and refuses acquisition-cadence or GP3 promotion.

## Distributed-overlap human-human agreement

The upstream HHA evidence is:

`validation/evidence/gaze-in-wild/gaze-in-wild-distributed-overlap-human-human-agreement-evidence-v1.json`

Fingerprint:

```text
7e6d6180b01417d7be2e07483cc0c7e0feb86a1d08be6b8aeba03f48fdb27f02
```

It freezes sample-level and event-level agreement for the **five recordings with distributed multi-labeller overlap**, covering six labeller pairs. The existing HHA validator independently checks the exact recording set, pair coverage, sample metrics, event metrics, bidirectional event symmetry, source binding, and scientific boundaries.

The synchronization checkpoint therefore marks the roadmap requirement complete only under the explicit wording **"distributed multi-labeller overlap subset"**. It does not create a full-distribution human-human agreement claim.

## Roadmap wording frozen by the validator

The accepted scoped statements are:

> Freeze the 68-file Gaze-in-the-Wild ProcessData processed timestamp-grid rate distribution; this is not acquisition-hardware cadence.

> Freeze Gaze-in-the-Wild labeller-to-labeller sample-level and event-level agreement on the distributed multi-labeller overlap subset (five recordings); no full-distribution HHA claim.

Any broader replacement fails validation.

## Still open

This synchronization does **not** satisfy or authorize:

- authoritative complete numeric `TrIdx` → publication-task mapping;
- `TrIdx 4 → Tea_Making` by elimination;
- task-stratified human-human agreement or model validation;
- naturalistic-task sensitivity claims;
- acquisition-hardware cadence verification;
- native 60 Hz or Gazepoint GP3 validity;
- cross-dataset validation;
- quarantine exit;
- new empirical model-performance claims.

The participant-disjoint task-agnostic GIW benchmark and its event-class sensitivity remain valid frozen evidence, but the combined roadmap item that also asks for **task sensitivity** must remain open until the authoritative numeric task-mapping gate is resolved.
