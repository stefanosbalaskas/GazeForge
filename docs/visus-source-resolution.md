# VISUS source-resolution status

GazeForge treats locating the VISUS benchmark as a separate scientific-provenance task from validating a local copy. The repository therefore records what the public literature and current institutional indexes establish, while refusing to turn historical availability into a current source or licensing claim.

The baseline machine-readable checkpoint is `validation/protocols/visus-source-resolution-2026-09-04.json`. A dated institutional recheck is frozen separately at `validation/evidence/visus-source-recheck/visus-authoritative-source-recheck-2026-09-09.json` so it does not replace or duplicate the reviewed dashboard checkpoint. Both are **source-resolution status records, not source-audit specifications and not empirical evidence**.

## What is established

The original 2014 benchmark publication is:

> Kuno Kurzhals, Cyrill Fabian Bopp, Jochen Bässler, Felix Ebinger, and Daniel Weiskopf. *Benchmark Data for Evaluating Visualization and Analysis Techniques for Eye Tracking for Video Stimuli*. BELIV 2014. DOI: `10.1145/2669557.2669558`.

The paper describes the benchmark as publicly available and names the original distribution endpoint:

```text
http://go.visus.uni-stuttgart.de/eyetrackingBenchmark
```

It describes 11 video scenarios and 25 participants, with gaze acquired using a Tobii T60 XL at 60 Hz. The videos are 1920×1080 and normalized to 25 fps. The distributed benchmark is described as containing video stimuli, exported eye-tracking data, and dynamic AOI annotations in ViPER-compatible XML.

A 2021 Sensors paper independently reports that the VISUS dataset was downloadable from:

```text
https://www.visus.uni-stuttgart.de/publikationen/benchmark-eyetracking
```

and records an access date of 12 April 2021. This is useful historical distribution evidence; it is not proof that the same endpoint or terms remain current.

## Current resolution result

A public-source resolution pass on 2026-09-04 checked the current VISUS institutional site/indexed publication pages, the historical endpoint identifiers, the University of Stuttgart DaRUS VISUS dataverse, the ACM publication record, and general public indexing.

The current VISUS site still lists the 2014 publication on Kuno Kurzhals's institutional profile. DaRUS also contains current VISUS eye-tracking datasets. However, the search did **not locate a current authoritative distribution for this specific 2014 benchmark**, a matching DaRUS record, a separate dataset DOI, or explicit current dataset reuse terms.

Accordingly, GazeForge records:

- `current_authoritative_distribution_unresolved`;
- `current_authoritative_download_found=false`;
- `source_audit_ready=false`;
- analysis-use terms unresolved;
- raw-data redistribution terms unresolved.

Failure to locate a current distribution is not evidence that no authoritative copy exists. It means the public evidence available in this resolution pass is insufficient for GazeForge's empirical source gate.

## 2026-09-09 institutional recheck

The 2026-09-09 recheck repeated the authoritative-source search instead of treating the 2026-09-04 checkpoint as permanently current. It records the same unresolved scientific result with additional present-day evidence:

- the live Kuno Kurzhals VISUS profile still lists the 2014 benchmark publication;
- the live VISUS DaRUS dataverse reports 18 records, but exact-title, publication-DOI, and author-targeted searches in this recheck did not locate a record matching the 2014 25-participant × 11-stimulus benchmark;
- modern VISUS DaRUS datasets such as `10.18419/DARUS-4023` and `10.18419/DARUS-4141` expose explicit `CC BY 4.0` dataset licenses, but those licenses apply to those deposits only and are **not transferred backward** to the 2014 benchmark;
- a 2026 dissertation still cites the historical VISUS distribution page with an access date of 12 April 2021, so it corroborates historical access rather than current availability;
- current public code/derivative searches still recover VISUS-derived material, not an authoritative replacement for the complete benchmark.

The recheck is frozen as:

```text
validation/evidence/visus-source-recheck/visus-authoritative-source-recheck-2026-09-09.json
```

with canonical fingerprint:

```text
97bd19b892032a663b7707235504a7ba886a86d6c3caab4966fa6c5ee96a2571
```

Its strict validator additionally binds the two already-reviewed derivative evidence records to their real repository bodies:

- public partial dynamic-AOI evidence: `80e008228e39c2b17bae99a526e2a0157c2c850ebe803c5a370abe9167efde14` (3 participants × 1 stimulus);
- public event-extension evidence: `2f12bd83d71786bfae7101dec6515c49c5ff4e696df8675b3955300e5e5e6dfd` (2 additional complete Tobii exports, with stimulus identity still not file-bound).

Neither derivative is promoted to the full VISUS source. The strict layer rejects even correctly refingerprinted attempts to claim full-corpus recovery, a matching DaRUS record, a separate dataset DOI, an explicit current benchmark license, transfer of modern DaRUS licenses, derivative source authority, independent annotation streams, source-audit authorization, human-human agreement, model-human validation, Frozen Evidence eligibility, or raw-source redistribution.

The 2026-09-09 result therefore **does not satisfy** the roadmap item “Obtain/verify an authoritative current VISUS copy and reuse/distribution terms.” That item remains open.

## Validate the checkpoint

The baseline checkpoint has a dedicated JSON-only validator:

```bash
gazeforge-visus-source-resolution \
  validation/protocols/visus-source-resolution-2026-09-04.json
```

The validator checks the record type, benchmark identity, ISO check date, current-source/audit/empirical flags, publication DOI, rights fields, annotation-independence gate, explicit claim limits, and a deterministic canonical SHA-256 fingerprint. The same generic validator also applies to the 2026-09-09 recheck file, while `gazeforge.visus_authoritative_source_recheck.validate_visus_authoritative_source_recheck` adds the frozen current-search and derivative-binding contract.

The current unresolved status is fail-closed: it cannot simultaneously claim that a current authoritative download was found, that the source is audit-ready, that empirical evidence was created, that analysis or redistribution rights are resolved, or that independent human annotation streams are verified.

This validation is still **not** a source audit. It verifies the internal integrity and conservative semantics of the source-resolution record only.

## Copyright is not treated as a dataset license

The ACM paper contains its publication copyright/permissions notice. GazeForge does **not** reinterpret that notice as a license covering the benchmark's raw video, gaze, or AOI files. Similarly, the paper's description of the dataset as publicly available establishes historical availability, not unrestricted redistribution.

Analysis-use permission and raw-file redistribution remain separate evidence fields and must be established explicitly for the exact copy used in an empirical run.

## Annotation independence remains unverified

The paper reports that dynamic AOI annotation was performed manually by two contributors to improve annotation quality. It further explains that the first contributor performed the main annotation and the second made additional annotations and refinements.

That workflow is not evidence of two independently produced annotation streams. GazeForge therefore keeps:

- `independent_annotation_streams_verified=false`;
- `human_human_agreement_ready=false`.

Only an authoritative obtained copy that contains separately recoverable streams, together with evidence that they were produced independently, can open the human-human agreement gate.

## What must happen next

The next empirical step is not another model run. It is source acquisition and rights verification:

1. obtain the benchmark from a current VISUS/author-verified institutional source, or receive an author-verified copy;
2. document current analysis-use and raw-data redistribution terms separately;
3. inventory and hash every file in the exact obtained copy;
4. review stimulus/participant/AOI-stream identities from those files;
5. determine whether independent annotation streams actually exist;
6. only then execute the canonical human-AOI intake, documented model prediction intake, externally supplied evaluation grid, and Frozen Evidence workflow.

Until those steps are complete, the existing VISUS software remains validated infrastructure with empirical execution pending.

## Public sources used for the resolution checkpoints

- Original BELIV publication: <https://doi.org/10.1145/2669557.2669558>
- 2021 Sensors evaluation/data-availability statement: <https://doi.org/10.3390/s21124143>
- Current Kuno Kurzhals VISUS profile: <https://www.visus.uni-stuttgart.de/en/team/Kurzhals/>
- Current VISUS DaRUS dataverse: <https://darus.uni-stuttgart.de/dataverse/visus>
- Modern DaRUS license examples used only to document non-transferability: `10.18419/DARUS-4023` and `10.18419/DARUS-4141`

These references document the resolution decision. They do not replace the exact-file source audit required for empirical evidence.
