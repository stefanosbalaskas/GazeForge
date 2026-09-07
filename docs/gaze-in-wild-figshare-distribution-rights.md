# Gaze-in-the-Wild Figshare distribution and rights

This evidence tranche resolves a narrower question than source-audit readiness: whether the public processed Gaze-in-the-Wild deposits can be identified precisely and whether those named deposits carry explicit reuse terms.

## Verified public deposits

The official Figshare project `74580` currently lists exactly three dataset items authored by Rakshit Kothari:

| Deposit | DOI | Files | Bytes | Frozen manifest SHA-256 | Licence |
| --- | --- | ---: | ---: | --- | --- |
| `ProcessData` | `10.6084/m9.figshare.11673645.v1` | 68 | 2,384,573,418 | `cc82a05fa64d35f76f955ebe231c27ff858d9d53de714ffa92d9d9c21828aaa8` | CC BY 4.0 |
| `LabelData` | `10.6084/m9.figshare.11673696.v1` | 50 | 28,725,824 | `65d934d3d3e2ebb04e639fc16435bf3383882340996a211159c5ccb67c71b35d` | CC BY 4.0 |
| `ProcessData_cleaned` | `10.6084/m9.figshare.11673717.v1` | 68 | 2,309,276,802 | `eda07ca38dfd6b8313b3240c169b274453586c5cdc94f44ca08d83adf19e4d3b` | CC BY 4.0 |

The evidence freezes the Figshare API metadata, including each file name, size, download identity, and supplied/computed MD5 metadata. No dataset file bytes were downloaded while creating this tranche.

The `ProcessData_cleaned` item is intentionally not treated as an original-publication copy. Its own deposited description says the improved eye/head signals were not published as part of the original Gaze-in-the-Wild publication and are offered for researchers to build upon.

## Rights boundary

Each of the three named Figshare dataset records reports **CC BY 4.0** and links to the Creative Commons 4.0 attribution terms. For these named deposits, GazeForge therefore records the deposit reuse terms as resolved and records analysis, adaptation, and redistribution as permitted by the stated deposit licence subject to its conditions, including attribution.

This is deliberately not a blanket adjudication of every possible legal or ethical obligation. Privacy, publicity, moral rights, research-ethics restrictions, or other applicable obligations are not inferred away by the metadata licence record.

The licence finding is also not inferred from the article licence or the processing repository's MIT software licence. It is bound directly to the three Figshare dataset records.

## Distribution structure learned from the official manifest

The public `ProcessData` manifest contains 68 participant/trial files and numeric `TrIdx` values 1–4. `ProcessData_cleaned` exposes the same filename set.

The manifest exposes 20 `PrIdx` values:

```text
1, 2, 3, 4, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23
```

That is intentionally **not** promoted to the 19-observer publication matrix. In particular, `PrIdx_4` occurs in the official distribution manifest but is absent from the frozen 19-observer publication matrix. The exact publication-participant ↔ distributed-file interpretation therefore remains open.

Similarly, observing numeric `TrIdx` values 1–4 does not establish a universal `TrIdx → task name` mapping. Task identity remains fail-closed until the distribution-directory or another authoritative mapping source resolves it.

## LabelData provenance advance

The official `LabelData` item contains 50 separate labeller-specific `.mat` files covering 37 participant/trial cells. Its manifest exposes labeller IDs `1, 2, 3, 5, 6`.

Five participant/trial cells have multiple separately deposited labeller files:

| PrIdx | TrIdx | Labellers |
| ---: | ---: | --- |
| 1 | 1 | 1, 2, 5, 6 |
| 1 | 2 | 1, 2, 5, 6 |
| 2 | 1 | 1, 2, 5, 6 |
| 2 | 2 | 1, 2, 5, 6 |
| 6 | 2 | 5, 6 |

This resolves the metadata-level question of whether separate labeller-specific files exist in the official deposit. It does **not** create human-human agreement evidence: the exact LabelData bytes have not yet been acquired, structurally audited, or compared.

## What remains closed

This tranche does not authorize a Gaze-in-the-Wild recovery candidate to exit quarantine. The existing quarantine-exit contract still requires an exact acquired candidate, structured exact-copy identity review, source-authority binding, and all other gate inputs.

Accordingly, all of the following remain false or unresolved here:

- exact authoritative dataset bytes acquired and verified against the frozen manifests;
- complete publication participant ↔ distributed `PrIdx` mapping;
- universal `TrIdx → task` mapping;
- content-level recovery of independent labeller streams;
- human-human agreement;
- participant-disjoint model validation;
- cross-dataset performance;
- GP3-specific validity;
- empirical evidence creation;
- quarantine-exit authorization and source-audit readiness.

The immutable reviewed evidence fingerprint is:

```text
25d4b56e1dc4888b034b5de91cb14f712aaa0e3470cde7a1246f30c3880e63c7
```

A dedicated CI workflow revalidates the frozen evidence and performs a fresh metadata-only Figshare read. The fresh public metadata must reproduce the frozen item identities, licence objects, project membership, and complete file manifests before this evidence remains green.
