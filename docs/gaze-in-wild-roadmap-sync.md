# Gaze-in-the-Wild roadmap evidence synchronization

This checkpoint synchronizes three roadmap entries with evidence that is already frozen in the repository. It does **not** rerun the underlying science and does not widen any Gaze-in-the-Wild claim.

Version 2 extends the earlier rate/HHA synchronization with a narrowly scoped completion for the official public Figshare `ProcessData` + `LabelData` copy and its current deposit reuse terms. The v1 evidence remains immutable historical provenance.

## Scoped items now supported

| Roadmap item | Evidence-backed status | Scope boundary |
| --- | --- | --- |
| Per-file sampling-rate distribution | **Satisfied, with corrected wording** | 68 distributed `ProcessData` files; rate inferred from each file's strictly increasing processed `T` timestamp grid. This is a **processed-stream timestamp-grid rate**, not acquisition-hardware cadence. |
| Labeller-to-labeller sample/event agreement | **Satisfied, with corrected wording** | Six labeller pairs across the five distributed recordings that actually contain multi-labeller overlap. This is **overlap-subset HHA**, not full-distribution HHA. |
| Official public GIW copy + current reuse terms | **Satisfied, narrowly** | The Rakshit Kothari-authored Figshare `ProcessData` and `LabelData` original-publication deposits are identified, their CC BY 4.0 deposit terms are verified, and all 118 files were byte-verified against the frozen manifests. This does **not** establish byte-for-byte equivalence to the historical RIT-hosted archive. |

## Frozen synchronization identities

The original v1 synchronization remains frozen at:

`validation/evidence/gaze-in-wild/gaze-in-wild-roadmap-evidence-sync-v1.json`

with fingerprint:

```text
c0dc3182f7fa89d325e0be2406d6d1aaf6541ebb2e90c21f49ade23398909571
```

The v2 synchronization is frozen at:

`validation/evidence/gaze-in-wild/gaze-in-wild-roadmap-evidence-sync-v2.json`

with fingerprint:

```text
8baf35fc97e59fa691a32e3e3d190e431bd1214a851d38f1877dce6d448fa215
```

The v2 validator revalidates v1 rather than replacing its scientific meaning.

## ProcessData processed timestamp-grid rate ledger

The upstream rate ledger is:

`validation/evidence/gaze-in-wild/gaze-in-wild-processdata-processed-rate-ledger-v1.json`

Fingerprint:

```text
1bd6643bd0c75faec9d070f74fb719f9178caa2da7e90bcbe356a0dbc5f38905
```

It contains **68 exact distributed ProcessData file identities**. For every file it records the stored `ProcessData.SR` processing-rate field and the rate inferred as the median inverse delta of the strictly increasing `ProcessData.T` processed timestamp grid. The stored field is 300 Hz and the timestamp-inferred processed rates are correspondingly near 300 Hz.

This evidence is deliberately narrower than an acquisition-cadence statement. It does **not** verify the hardware acquisition rate, native 60 Hz evidence, or Gazepoint GP3 validity.

## Distributed-overlap human-human agreement

The upstream HHA evidence is:

`validation/evidence/gaze-in-wild/gaze-in-wild-distributed-overlap-human-human-agreement-evidence-v1.json`

Fingerprint:

```text
7e6d6180b01417d7be2e07483cc0c7e0feb86a1d08be6b8aeba03f48fdb27f02
```

It freezes sample-level and event-level agreement for the **five recordings with distributed multi-labeller overlap**, covering six labeller pairs. This is an overlap-subset result, not a full-distribution HHA claim.

## Official Figshare copy and rights chain

The distribution-rights evidence is:

`validation/evidence/gaze-in-wild/gaze-in-wild-figshare-distribution-rights-evidence-v1.json`

Fingerprint:

```text
25d4b56e1dc4888b034b5de91cb14f712aaa0e3470cde7a1246f30c3880e63c7
```

It binds Figshare project `74580` and the named Rakshit Kothari-authored deposits directly to their dataset-record licence, **CC BY 4.0**. The relevant original-publication deposits are:

- `ProcessData`: DOI `10.6084/m9.figshare.11673645.v1`;
- `LabelData`: DOI `10.6084/m9.figshare.11673696.v1`.

The exact-byte evidence is:

`validation/evidence/gaze-in-wild/gaze-in-wild-figshare-exact-bytes-evidence-v1.json`

Fingerprint:

```text
dbf277d698266fe53e337a15fc342e9af1835460d2bcc69c3992635de8fa0a00
```

It verifies **118 files / 2,413,299,242 bytes** across `ProcessData` and `LabelData`, with transport-independent stable exact-byte identity:

```text
8d36884daf76e26ded3d31c32bd334bf8f358b49efdb7accbb20c6c569abdda0
```

Every downloaded MAT file was deleted after verification. Raw dataset bytes were not retained. `ProcessData_cleaned` was not downloaded and remains excluded because its own deposit description identifies it as outside the original publication data.

This is sufficient to close the **official public Figshare copy/current deposit-rights** roadmap item. It is deliberately not restated as proof that the current Figshare bytes are byte-for-byte identical to the historical RIT-hosted archive.

## Roadmap wording frozen by the validators

The accepted scoped statements are:

> Freeze the 68-file Gaze-in-the-Wild ProcessData processed timestamp-grid rate distribution; this is not acquisition-hardware cadence.

> Freeze Gaze-in-the-Wild labeller-to-labeller sample-level and event-level agreement on the distributed multi-labeller overlap subset (five recordings); no full-distribution HHA claim.

> Obtain/audit the official Gaze-in-the-Wild Figshare ProcessData + LabelData original-publication bytes and current deposit reuse terms (CC BY 4.0); raw MAT not retained.

A broader replacement—such as claiming historical RIT archive equivalence, quarantine exit, or complete task identity—fails validation.

## Still open

This synchronization does **not** satisfy or authorize:

- byte-for-byte equivalence to the historical RIT-hosted archive;
- authoritative complete numeric `TrIdx` → publication-task mapping;
- `TrIdx 4 → Tea_Making` by elimination;
- task-stratified human-human agreement or model validation;
- naturalistic-task sensitivity claims;
- acquisition-hardware cadence verification;
- native 60 Hz or Gazepoint GP3 validity;
- cross-dataset validation;
- quarantine exit;
- raw MAT retention; or
- new empirical model-performance claims.

The participant-disjoint task-agnostic GIW benchmark and its event-class sensitivity remain valid frozen evidence. The combined roadmap item that also asks for **naturalistic-task sensitivity** remains open until the authoritative numeric task-mapping gate is resolved.
