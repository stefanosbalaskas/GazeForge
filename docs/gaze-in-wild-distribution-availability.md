# Gaze-in-the-Wild distribution availability evidence

GazeForge records **where the Gaze-in-the-Wild authors said the compressed dataset was distributed**, **whether an exact copy has actually been obtained**, and **what rights apply to that external copy** as separate questions.

The historical distribution review is frozen at:

```text
validation/evidence/gaze-in-wild/gaze-in-wild-distribution-availability-evidence-v1.json
```

with immutable fingerprint:

```text
2400c81a0897fb414285069c368a8a9d96de1d18eb185b1073cf15bb1c8bd1da
```

A second evidence layer freezes the current first-party listing state without rewriting that earlier record:

```text
validation/evidence/gaze-in-wild/gaze-in-wild-current-first-party-listing-evidence-v1.json
```

with immutable fingerprint:

```text
c2b9a19f43276e6bde08794f87212e4c2016a9e0ab3183dc4f8b69d310c02916
```

The second record is cryptographically bound to the first fingerprint. Both are provenance/governance evidence. Neither is **Frozen Evidence performance evidence**.

## First-party distribution identity

The 2020 Scientific Reports paper states that compressed data and code were publicly available from:

```text
http://www.cis.rit.edu/~rsk3900/gaze-in-wild/
```

The pinned first-author processing repository points users to the same historical project webpage for all data files. Its README separately states that the raw data exceed 14 TB, are not provided over the internet, and require contacting the authors for specific raw-data access.

Together these sources establish the historical first-party distribution identity. They do **not** establish that GazeForge currently possesses the exact compressed `ProcessData`/`LabelData` archive.

## Current first-party listing state

The current RIT Perception for Movement Lab page still contains a **Software/Data** entry named **The Gaze-In-Wild Dataset**. The live listing probe resolves that exact entry to:

```text
https://pubmed.ncbi.nlm.nih.gov/32054884/
```

That is the publication record, not a verified direct dataset archive. The reviewed live listing-state fingerprint is:

```text
b7fcf78719cb23ce7133fe3fb51a757c561c5b25797f40de4a2e00b8e1c4f839
```

The workflow treats this first-party listing state as review-sensitive. If RIT changes the link to a new target—especially a first-party archive candidate—the workflow fails closed and requires human evidence review. It never automatically promotes a new target to an authoritative exact copy or to dataset-file rights.

The RIT page's general website copyright notice is likewise not interpreted as a licence for the external dataset files.

## Historical endpoint transport observations are non-gating

During the 2026-09-05 source-resolution review, an interactive HTTPS retrieval of the historical RIT endpoint returned HTTP `502`. A subsequent GitHub Actions probe on 2026-09-06 encountered a TLS certificate-chain verification failure at that host. A bounded read-only fallback with certificate verification explicitly disabled then observed HTTP `404`.

These different results demonstrate why the historical endpoint status is recorded as a **transport diagnostic rather than a scientific evidence gate**:

- neither `404` nor `502` proves global unavailability;
- a TLS-unverified fallback does not authenticate the server or source;
- neither status identifies an exact compressed dataset copy;
- an endpoint response does not establish dataset-file reuse rights; and
- transport variation is excluded from the stable first-party listing-state fingerprint.

The full GitHub Actions observation that supported the dated review is separately fingerprinted as:

```text
a1660d1c70916b8af605f23c64518b4a50fdf59a649fd2fff460965474bae1e6
```

Future transport diagnostics may differ without changing the reviewed first-party listing identity. Any such difference remains non-promotional.

## Secondary recovery leads are quarantined

Two public GitHub observations are retained only as recovery/provenance leads.

`Morris88826/awesome-eye-data` advertises a processed collection named `GazeinTheWild` and a Google Drive folder. Its documented organization uses transformed annotation CSVs and chunked video files. GazeForge therefore does **not** treat it as the authoritative compressed `ProcessData`/`LabelData` distribution, does not inherit rights from it, and does not allow it to satisfy empirical source-audit gates.

`George614/edit_distance_gpu` contains example code referring to separately named files such as:

```text
LabellerIdx_7_PrIdx_1_TrIdx_1.mat
LabellerIdx_8_PrIdx_1_TrIdx_1.mat
```

Those filenames are useful evidence that separately named labeller files existed in at least one working copy. They do **not** verify an authoritative source, shared gaze identity, independent-stream recoverability in the exact current distribution, or eligibility for frozen human-human agreement.

## Rights remain unresolved at dataset-file level

The Scientific Reports article is CC BY 4.0, but that article licence is not promoted to the externally hosted dataset files.

The first-author processing repository is MIT licensed for its software and associated documentation, but that software licence is not promoted to the separately distributed dataset archive.

The current RIT listing adds no dataset-file analysis or redistribution terms. Therefore:

- dataset-file analysis-use terms remain **unresolved**;
- dataset-file redistribution terms remain **unresolved**;
- analysis use is not yet authorized by this evidence;
- redistribution is not yet authorized by this evidence;
- licence inference is prohibited; and
- a recovered third-party mirror cannot change those rights fields.

## Relationship to recovery-quarantine exit

The current first-party listing evidence is intentionally insufficient to satisfy the recovery-quarantine exit introduced by PR #74. It does not bind the listing to an exact local candidate copy and does not verify dataset-file rights, reuse terms, analysis permission, or redistribution status for that copy.

Accordingly, this evidence keeps all of the following false:

```text
current_listing_is_source_authority_for_an_exact_local_copy
exact_copy_identity_verified
dataset_file_rights_resolved
reuse_terms_verified_for_dataset_files
analysis_use_permitted
redistribution_status_resolved
quarantine_exit_authorizable_from_this_evidence
```

A future authoritative archive or explicit first-party reuse statement must be separately reviewed and cryptographically bound to the exact candidate before any quarantine-exit decision can change.

## Empirical gates remain closed

This evidence does not resolve:

- current exact authoritative archive acquisition;
- original-distribution equivalence for any recovered copy;
- exact distributed participant identities;
- complete `TrIdx→task` mapping;
- timestamp-derived distributed-file cadence;
- separately recoverable independent labeller streams;
- human-human agreement;
- participant-disjoint model validation;
- cross-dataset model performance; or
- Gazepoint GP3 validity.

A future source candidate must still pass the existing exact-file source-audit, identity, rights, cadence, coordinate, annotation-stream, and recovery-quarantine-exit checks before any empirical GIW claim can be frozen.

## Reviewed sources

- Scientific Reports publication: <https://doi.org/10.1038/s41598-020-59251-5>
- Open full-text article: <https://pmc.ncbi.nlm.nih.gov/articles/PMC7018838/>
- First-author processing repository: <https://github.com/RSKothari/Gaze-in-Wild>
- Current RIT Perception for Movement Lab: <https://www.rit.edu/science/perception-movement-lab>
- Current RIT listing target: <https://pubmed.ncbi.nlm.nih.gov/32054884/>
- Historical distribution identifier: <http://www.cis.rit.edu/~rsk3900/gaze-in-wild/>
- Secondary transformed collection lead: <https://github.com/Morris88826/awesome-eye-data>
- Secondary labeller-filename lead: <https://github.com/George614/edit_distance_gpu>
