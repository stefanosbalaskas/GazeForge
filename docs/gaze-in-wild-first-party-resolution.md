# Gaze-in-the-Wild first-party resolution request

!!! note "Status superseded for the public Figshare copy/rights gate"
    This page preserves the earlier correspondence-based resolution protocol. Later reviewed evidence directly verified the official Rakshit Kothari-authored Figshare `ProcessData` and `LabelData` deposits, their **CC BY 4.0** dataset-record terms, and all **118 original-publication files / 2,413,299,242 bytes**. The narrower roadmap item covering the official public Figshare copy and current deposit reuse terms therefore no longer requires a first-party reply. This does **not** establish byte-for-byte equivalence to the historical RIT-hosted archive, numeric `TrIdx → task` mapping, quarantine exit, raw-data retention, or device validity.

At the time this protocol was frozen, GazeForge had verified the historical first-party distribution identity and the then-current RIT listing state but had not yet acquired the later-verified official Figshare bytes or resolved the named Figshare dataset-file terms. This page records that earlier evidence-gated route and remains useful if future questions require explicit author/distributor clarification.

Current direct-deposit evidence is documented in [Gaze-in-the-Wild Figshare distribution rights](gaze-in-wild-figshare-distribution-rights.md), [Gaze-in-the-Wild exact Figshare bytes](gaze-in-wild-exact-figshare-bytes.md), and [Gaze-in-the-Wild roadmap evidence synchronization](gaze-in-wild-roadmap-sync.md).

## Historical rationale for the clarification route

The Scientific Reports data-availability statement identified a historical RIT distribution route. That publication statement alone was not treated as a dataset-file licence, and the article's CC BY 4.0 licence and processing repository's MIT licence were never transferred to the separately distributed dataset files by inference.

The later Figshare evidence resolves that narrower rights question differently: the **dataset records themselves** state CC BY 4.0. The historical RIT archive still has not been proved byte-for-byte equivalent to the verified current Figshare deposits, so correspondence remains a legitimate route if historical-archive equivalence or another unresolved first-party fact becomes necessary.

## Frozen request packet

The public request packet remains committed at:

```text
validation/requests/gaze-in-wild/gaze-in-wild-first-party-resolution-request-v1.json
```

Its immutable fingerprint is:

```text
39ae27429a6a23c2fc07125e8f500b9d8d2ceb133c59e52d7379225007a7d6db
```

It is bound to the earlier reviewed historical-distribution and current-listing evidence. Those historical identities remain immutable provenance even though later Figshare evidence supersedes the request as the route needed for the public-copy/current-rights roadmap item.

## Contact roles remain distinct

The packet records two public contact candidates with different evidence status:

- **Gabriel J. Diaz** — current RIT institutional contact and Director of the Perception for Movement Lab (`gabriel.diaz@rit.edu`).
- **Rakshit Kothari** — historical corresponding-author contact published with the Gaze-in-the-Wild article (`rsk3900@rit.edu`); current delivery/status is not inferred from the historical publication address.

A contact address, institutional domain, authorship role, or lab affiliation is not itself proof that a person can grant or clarify rights. A future reply used as scientific-governance evidence still requires explicit authority review.

## Questions preserved by the request

The frozen packet asks for nine specific clarifications:

1. a current authoritative archive or access route;
2. whether an archive is the original distribution or a canonical replacement and how identity should be checked;
3. dataset-file analysis/research-use terms;
4. redistribution/mirroring/bundling terms;
5. treatment of non-reconstructive derived metrics, model outputs, and validation reports;
6. who has authority to confirm the terms;
7. authoritative participant identities and complete `TrIdx → task` mapping, if available;
8. authoritative coordinate semantics and distributed-file cadence, if available; and
9. whether separately recoverable independent labeller streams exist and how they are identified.

Several of these questions are now partly or fully answered by later evidence, but the packet itself is not rewritten because its fingerprint is historical provenance. In particular, the complete authoritative numeric task mapping remains unresolved.

## Generate or validate the historical request

The isolated CLI remains:

```text
gazeforge-giw-first-party-resolution
```

Generate the exact packet from its committed parent evidence:

```bash
gazeforge-giw-first-party-resolution request \
  --output giw-first-party-request.json
```

Validate the committed packet:

```bash
gazeforge-giw-first-party-resolution request-validate \
  --request validation/requests/gaze-in-wild/gaze-in-wild-first-party-resolution-request-v1.json
```

## Privacy-safe response intake

GazeForge does not commit raw correspondence by default. A future reply can still be converted to a digest-bound pending review scaffold:

```bash
gazeforge-giw-first-party-resolution response-scaffold \
  --request validation/requests/gaze-in-wild/gaze-in-wild-first-party-resolution-request-v1.json \
  --correspondence /private/path/reply.eml \
  --output /review/path/giw-first-party-response.json
```

Validation requires the same local correspondence bytes:

```bash
gazeforge-giw-first-party-resolution response-validate \
  --request validation/requests/gaze-in-wild/gaze-in-wild-first-party-resolution-request-v1.json \
  --response /review/path/giw-first-party-response.json \
  --correspondence /private/path/reply.eml
```

If the local file changes, digest validation fails.

## Rights and authority review remains strict

A future correspondence-derived rights statement may be promoted only after completed human review, explicit authority review, dataset-file scope, and a recorded evidence basis. Publication language, an article licence, a software licence, an institutional email address, or a download location cannot substitute for those requirements.

For the **named Figshare deposits**, however, the later evidence does not rely on correspondence: the deposit records themselves provide the verified CC BY 4.0 terms.

## Scientific boundary remains closed

Neither this historical protocol nor the later public-copy/current-rights synchronization creates or authorizes:

- byte-for-byte equivalence to the historical RIT-hosted archive;
- recovery-quarantine exit;
- complete numeric participant/trial/task mapping;
- acquisition-hardware cadence verification;
- task-stratified model validation;
- cross-dataset performance;
- native 60 Hz or Gazepoint GP3 validity; or
- a raw-data retention claim.

The current exact participant-disjoint GIW benchmark therefore remains **task-agnostic derived-60-Hz evidence**.

## Public provenance sources

- Scientific Reports article: <https://doi.org/10.1038/s41598-020-59251-5>
- PubMed publication record: <https://pubmed.ncbi.nlm.nih.gov/32054884/>
- Current RIT Perception for Movement Lab: <https://www.rit.edu/science/perception-movement-lab>
- Historical distribution identifier: <http://www.cis.rit.edu/~rsk3900/gaze-in-wild/>
