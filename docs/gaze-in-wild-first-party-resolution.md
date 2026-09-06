# Gaze-in-the-Wild first-party resolution request

GazeForge has verified the historical first-party distribution identity and the current RIT listing state, but it has **not** obtained an exact authoritative `ProcessData` / `LabelData` archive and has **not** resolved the reuse terms that apply to the dataset files themselves.

This page documents the next evidence-gated step: a deterministic first-party clarification request and a privacy-safe response-review workflow.

## Why a first-party clarification is still needed

The published Scientific Reports data-availability statement says the compressed data and code were publicly available from the historical RIT project page. The earlier arXiv version likewise expressed an intention to make the dataset and related resources public. Those statements are important distribution provenance, but GazeForge does **not** reinterpret the word **public** as a dataset-file licence.

The article's CC BY 4.0 licence applies to the article. The processing repository's MIT licence applies to that repository's software and associated documentation. Neither has been promoted to the separately distributed dataset files.

The current RIT Perception for Movement Lab page still lists **The Gaze-In-Wild Dataset**, but the current listing resolves to the PubMed publication record rather than a verified direct archive. The exact current archive and dataset-file terms therefore remain unresolved.

## Frozen request packet

The public request packet is committed at:

```text
validation/requests/gaze-in-wild/gaze-in-wild-first-party-resolution-request-v1.json
```

Its immutable fingerprint is:

```text
39ae27429a6a23c2fc07125e8f500b9d8d2ceb133c59e52d7379225007a7d6db
```

The request is bound to three previously reviewed identities:

```text
historical distribution evidence:
2400c81a0897fb414285069c368a8a9d96de1d18eb185b1073cf15bb1c8bd1da

current first-party listing evidence:
e8257820f6cbfc9688e3771fd976c6afcb6b5ced93e385a009d10038a23bdcd5

current listing-state fingerprint:
b7fcf78719cb23ce7133fe3fb51a757c561c5b25797f40de4a2e00b8e1c4f839
```

Changing either parent evidence record invalidates request validation.

## Contact roles are kept distinct

The packet records two public contact candidates with different evidence status:

- **Gabriel J. Diaz** — current RIT institutional contact and Director of the Perception for Movement Lab (`gabriel.diaz@rit.edu`).
- **Rakshit Kothari** — historical corresponding-author contact published with the Gaze-in-the-Wild article (`rsk3900@rit.edu`); current delivery/status is not inferred from the historical publication address.

A contact address, institutional domain, authorship role, or lab affiliation is **not** itself proof that the person has authority to grant dataset-file rights. Any reply that purports to resolve rights must receive a separate human authority review.

## What the request asks

The packet asks for nine specific clarifications rather than a generic download request:

1. the current authoritative location or access route for the compressed distribution;
2. whether a supplied archive is the original public distribution or a canonical replacement, and how identity can be checked;
3. explicit dataset-file analysis/research-use terms;
4. explicit redistribution/mirroring/bundling terms;
5. permission for non-reconstructive derived metrics, model outputs, and validation reports;
6. who currently has authority to confirm or grant the terms;
7. authoritative participant identities and complete `TrIdx→task` mapping, if available;
8. authoritative coordinate semantics and distributed-file cadence, if available; and
9. whether separately recoverable independent labeller streams exist for the same gaze samples, and how they are identified.

The request itself grants nothing. It creates no source-audit authorization, quarantine exit, empirical result, or licence inference.

## Generate or validate the request

The isolated CLI is:

```text
gazeforge-giw-first-party-resolution
```

Generate the exact packet from the two committed parent evidence records:

```bash
gazeforge-giw-first-party-resolution request \
  --output giw-first-party-request.json
```

Validate the committed packet:

```bash
gazeforge-giw-first-party-resolution request-validate \
  --request validation/requests/gaze-in-wild/gaze-in-wild-first-party-resolution-request-v1.json
```

The defaults point to the two reviewed GIW evidence records in `validation/evidence/gaze-in-wild/`.

## Privacy-safe response intake

GazeForge does **not** commit raw correspondence by default. Given a local message file, create a pending structured scaffold:

```bash
gazeforge-giw-first-party-resolution response-scaffold \
  --request validation/requests/gaze-in-wild/gaze-in-wild-first-party-resolution-request-v1.json \
  --correspondence /private/path/reply.eml \
  --output /review/path/giw-first-party-response.json
```

The generated record stores the correspondence SHA-256, not the message text. To validate an edited review later, the same local correspondence file is required:

```bash
gazeforge-giw-first-party-resolution response-validate \
  --request validation/requests/gaze-in-wild/gaze-in-wild-first-party-resolution-request-v1.json \
  --response /review/path/giw-first-party-response.json \
  --correspondence /private/path/reply.eml
```

If the local file changes by even one byte, digest validation fails.

## Rights review is deliberately strict

A structured response may record `analysis_use_status`, `redistribution_status`, or `derived_outputs_status` as resolved only when all of the following are true:

- the correspondence has received completed human review;
- first-party authority has been independently marked **verified** with an evidence basis;
- the statement explicitly covers the **dataset files themselves**;
- the rights basis is an explicit first-party statement or formal dataset terms; and
- the reuse-terms source and evidence basis are recorded.

A publication statement that the data are publicly available is not an allowed resolved-rights basis. An article licence, software-repository licence, RIT email address, or download location cannot substitute for explicit dataset-file scope and authority review.

## Archive location is not exact-copy verification

A reply may provide an apparently authoritative archive location. The response record can preserve that fact after review, but `exact_copy_identity_verified` remains forced to `false` in correspondence evidence.

Exact identity is a separate technical claim. A recovered archive must enter the existing recovery/candidate pipeline, receive a complete path/hash/byte manifest, pass the recovery-quarantine exit, and then pass the source audit. Correspondence cannot bypass those checks.

## Scientific boundary remains closed

This protocol does not create or authorize:

- an exact authoritative GIW copy;
- original-distribution equivalence;
- source-audit execution;
- recovery-quarantine exit;
- participant/task mapping verification;
- coordinate or cadence verification;
- independent labeller recoverability;
- human-human agreement;
- participant-disjoint model validation;
- cross-dataset model performance;
- Gazepoint GP3 validity; or
- Gaze-in-the-Wild Frozen Evidence performance claims.

A future reviewed first-party reply can become **input evidence** for the relevant rights/source-authority decisions. It is not itself the final source audit.

## Public provenance sources

- Scientific Reports article: <https://doi.org/10.1038/s41598-020-59251-5>
- PubMed publication record: <https://pubmed.ncbi.nlm.nih.gov/32054884/>
- Current RIT Perception for Movement Lab: <https://www.rit.edu/science/perception-movement-lab>
- Gabriel J. Diaz RIT directory: <https://www.rit.edu/science/directory/gjdgis-gabriel-diaz>
- Historical distribution identifier: <http://www.cis.rit.edu/~rsk3900/gaze-in-wild/>
