# Gaze-in-the-Wild roadmap evidence synchronization

This checkpoint synchronizes roadmap entries with evidence that is already frozen in the
repository. It does **not** rerun the underlying science and does not widen any
Gaze-in-the-Wild claim.

Version 2 extended the earlier rate/HHA synchronization with a narrowly scoped
completion for the official public Figshare `ProcessData` + `LabelData` copy and its
current deposit reuse terms. Version 3 separates the already-reviewed
**task-agnostic participant-disjoint derived-60-Hz validation and event-class
sensitivity** from the still-blocked **naturalistic-task sensitivity** component.
The v1 and v2 records remain immutable historical provenance.

## Scoped items now supported

| Roadmap item | Evidence-backed status | Scope boundary |
| --- | --- | --- |
| Per-file sampling-rate distribution | **Satisfied, with corrected wording** | 68 distributed `ProcessData` files; rate inferred from each file's strictly increasing processed `T` timestamp grid. This is a **processed-stream timestamp-grid rate**, not acquisition-hardware cadence. |
| Labeller-to-labeller sample/event agreement | **Satisfied, with corrected wording** | Six labeller pairs across the five distributed recordings that actually contain multi-labeller overlap. This is **overlap-subset HHA**, not full-distribution HHA. |
| Official public GIW copy + current reuse terms | **Satisfied, narrowly** | The Rakshit Kothari-authored Figshare `ProcessData` and `LabelData` original-publication deposits are identified, their CC BY 4.0 deposit terms are verified, and all 118 files were byte-verified against the frozen manifests. This does **not** establish byte-for-byte equivalence to the historical RIT-hosted archive. |
| Participant-disjoint task-agnostic model validation | **Satisfied** | 12 participants, 18 recordings, five participant-disjoint folds, 157,850 matched OOF analysis rows per model on a **derived 60-Hz** grid. No task mapping was used. |
| Event-class sensitivity | **Satisfied** | Frozen sample/event class results are available for blink, fixation, pursuit, saccade, and VOR. Pursuit remains an explicit failure case. |
| Naturalistic-task sensitivity | **Open** | `task_fold_metrics` and `task_summary` each contain zero rows. Task sensitivity remains blocked until authoritative distributed file → publication-task mapping is verified. |

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

The v3 synchronization is frozen at:

`validation/evidence/gaze-in-wild/gaze-in-wild-roadmap-evidence-sync-v3.json`

with fingerprint:

```text
426ad10551a52a4b1cae9df9ae422336b591188466051235b5b38c8e808f7aa2
```

The v3 validator revalidates v2 and the reviewed exact participant-disjoint model
evidence rather than replacing either scientific meaning.

## ProcessData processed timestamp-grid rate ledger

The upstream rate ledger is:

`validation/evidence/gaze-in-wild/gaze-in-wild-processdata-processed-rate-ledger-v1.json`

Fingerprint:

```text
1bd6643bd0c75faec9d070f74fb719f9178caa2da7e90bcbe356a0dbc5f38905
```

It contains **68 exact distributed ProcessData file identities**. For every file it
records the stored `ProcessData.SR` processing-rate field and the rate inferred as the
median inverse delta of the strictly increasing `ProcessData.T` processed timestamp
grid. The stored field is 300 Hz and the timestamp-inferred processed rates are
correspondingly near 300 Hz.

This evidence is deliberately narrower than an acquisition-cadence statement. It does
**not** verify the hardware acquisition rate, native 60 Hz evidence, or Gazepoint GP3
validity.

## Distributed-overlap human-human agreement

The upstream HHA evidence is:

`validation/evidence/gaze-in-wild/gaze-in-wild-distributed-overlap-human-human-agreement-evidence-v1.json`

Fingerprint:

```text
7e6d6180b01417d7be2e07483cc0c7e0feb86a1d08be6b8aeba03f48fdb27f02
```

It freezes sample-level and event-level agreement for the **five recordings with
distributed multi-labeller overlap**, covering six labeller pairs. This is an
overlap-subset result, not a full-distribution HHA claim.

## Official Figshare copy and rights chain

The distribution-rights evidence is:

`validation/evidence/gaze-in-wild/gaze-in-wild-figshare-distribution-rights-evidence-v1.json`

Fingerprint:

```text
25d4b56e1dc4888b034b5de91cb14f712aaa0e3470cde7a1246f30c3880e63c7
```

It binds Figshare project `74580` and the named Rakshit Kothari-authored deposits
directly to their dataset-record licence, **CC BY 4.0**. The relevant
original-publication deposits are:

- `ProcessData`: DOI `10.6084/m9.figshare.11673645.v1`;
- `LabelData`: DOI `10.6084/m9.figshare.11673696.v1`.

The exact-byte evidence is:

`validation/evidence/gaze-in-wild/gaze-in-wild-figshare-exact-bytes-evidence-v1.json`

Fingerprint:

```text
dbf277d698266fe53e337a15fc342e9af1835460d2bcc69c3992635de8fa0a00
```

It verifies **118 files / 2,413,299,242 bytes** across `ProcessData` and `LabelData`,
with transport-independent stable exact-byte identity:

```text
8d36884daf76e26ded3d31c32bd334bf8f358b49efdb7accbb20c6c569abdda0
```

Every downloaded MAT file was deleted after verification. Raw dataset bytes were not
retained. `ProcessData_cleaned` was not downloaded and remains excluded because its
own deposit description identifies it as outside the original publication data.

This is sufficient to close the **official public Figshare copy/current
deposit-rights** roadmap item. It is deliberately not restated as proof that the
current Figshare bytes are byte-for-byte identical to the historical RIT-hosted
archive.

## Participant-disjoint task-agnostic model evidence

The reviewed participant-disjoint evidence is:

`validation/evidence/gaze-in-wild/gaze-in-wild-exact-participant-disjoint-model-validation-evidence-v1.json`

Fingerprint:

```text
b2fe85ec7e5d5cd425c0cd2593742bab835686c3f560d8a6c06e9c6d67dc547a
```

Its frozen scope is:

- **12 participants**, **18 recordings**, and **5 participant-disjoint folds**;
- **157,850** retained analysis rows per model with identical OOF rows;
- a **derived 60-Hz analysis grid**, not native 60 Hz or GP3 validation;
- `task_mapping_used = false`;
- `task_stratified_validation_created = false`;
- `task_fold_metrics = 0 rows`;
- `task_summary = 0 rows`;
- event-class sensitivity is present.

The cross-run reproducibility signature is:

```text
f8c8d27ddbb1fe065a15df18d53c9fa84544315ef57cf2783554b236839ff286
```

Floating benchmark outputs are compared under the frozen eight-decimal canonicalization
policy; source/split/count/class/convergence/scientific-boundary identities remain
exact.

### Pursuit remains a required visible failure case

The v3 validator does not permit roadmap synchronization to hide the weak pursuit
result. Frozen pursuit support is **5,696 samples** and **327 reference events**.

- I-VT: sample F1 `0`; event F1 `0`; no predicted pursuit events.
- RandomForest: sample F1 `0.0768712070`; event F1 `0.0085836910`.
- ContextMLP: sample F1 `0.0547112462`; event F1 `0.0029585799`.

Accordingly, aggregate learned-model performance must not be presented as uniformly
strong event recognition.

## Roadmap wording frozen by the validators

The accepted scoped statements are:

> Freeze the 68-file Gaze-in-the-Wild ProcessData processed timestamp-grid rate
> distribution; this is not acquisition-hardware cadence.

> Freeze Gaze-in-the-Wild labeller-to-labeller sample-level and event-level agreement
> on the distributed multi-labeller overlap subset (five recordings); no
> full-distribution HHA claim.

> Obtain/audit the official Gaze-in-the-Wild Figshare ProcessData + LabelData
> original-publication bytes and current deposit reuse terms (CC BY 4.0); raw MAT not
> retained.

> Run participant-disjoint Gaze-in-the-Wild task-agnostic derived-60-Hz model
> validation and report event-class sensitivity.

The still-open companion statement is:

> Report Gaze-in-the-Wild naturalistic-task sensitivity only after authoritative
> distributed ProcessData-file → publication-task mapping is verified.

A broader replacement—such as claiming task sensitivity, historical RIT archive
equivalence, quarantine exit, native 60-Hz validity, or GP3 validity—fails validation.

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

The task-agnostic participant-disjoint derived-60-Hz benchmark and event-class
sensitivity are complete frozen evidence. The **naturalistic-task sensitivity** roadmap
component remains open until the authoritative file-to-task mapping gate is resolved.
