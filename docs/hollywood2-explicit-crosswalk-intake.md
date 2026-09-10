# Hollywood2 explicit participant-crosswalk intake

GazeForge now has a fail-closed path for the one type of evidence that can resolve the
remaining Hollywood2EM participant-identity gate: an **explicit authoritative mapping**
between the 16 canonical GIN source tokens and original Hollywood2 subject identities/task
groups.

This workflow does not infer a mapping from filenames, token counts, missing numeric values,
publication order, or third-party parsers. It is designed for a future README, ledger, author
statement, or institutional record that explicitly states the mapping.

The public-source search remains exhausted under the evidence record documented in
[`Hollywood2 participant-crosswalk exhaustion`](hollywood2-participant-crosswalk-exhaustion.md).
The intake therefore expects a source that was obtained separately through an authorized
channel, such as a legitimately obtained original archive or a direct author/institutional
record.

## Why this is a two-stage gate

A local transcription is not automatically trusted merely because it is syntactically valid.
The workflow separates:

1. **candidate intake** — bind exact local source bytes to a structured transcription and
   verify token coverage, uniqueness, and hashes while keeping participant IDs and task labels
   out of the generated candidate record;
2. **manual review** — a reviewer must verify source authority, explicitness of the mapping,
   transcription accuracy, task-group semantics, and the version/scope to which the mapping
   applies;
3. **certificate emission** — only after the exact candidate and exact review fingerprints
   agree does GazeForge return the mapping in memory and emit a non-empirical certificate.

The certificate contains fingerprints and verification booleans, not raw participant IDs or
raw task-group labels.

## Accepted authority classes

The source manifest may classify the local source as one of:

- `author_statement`;
- `institutional_record`;
- `original_distribution_metadata`.

This field is a **claim supplied at intake**, not proof. The candidate record always keeps
`source_authority_verified=false`. Authority becomes verified only through the separately
bound manual review.

Third-party repackaging, filename conventions, inferred numeric order, and count coincidence
are intentionally not accepted authority classes.

## Source manifest

The local manifest is UTF-8 JSON with record type
`hollywood2-explicit-crosswalk-source-v1`. It must bind the exact source-file SHA-256 and state
that the source was obtained through an authorized channel.

A minimal **synthetic** illustration is:

```json
{
  "record_type": "hollywood2-explicit-crosswalk-source-v1",
  "source_reference": "local-authorized-source-reference",
  "source_authority_claim": "original_distribution_metadata",
  "source_file_sha256": "<64-lowercase-hex-digest>",
  "obtained_via_authorized_channel_affirmed": true,
  "mapping_entries": [
    {
      "gin_token": "001",
      "original_subject_id": "SYNTHETIC_SUBJECT_A",
      "task_group": "SYNTHETIC_GROUP_A"
    },
    {
      "gin_token": "002",
      "original_subject_id": "SYNTHETIC_SUBJECT_B",
      "task_group": "SYNTHETIC_GROUP_B"
    }
  ]
}
```

The values above are examples only and are **not Hollywood2 evidence**.

Candidate intake can inspect an incomplete transcription for discovery purposes, but review
promotion requires exact coverage of all canonical GIN tokens:

```text
001 002 003 004 005 006 008 010 011 012 013 014 015 017 018 019
```

A reviewed mapping must also use one-to-one original subject identifiers. No meaning is
assigned to the missing numeric values `007`, `009`, or `016`.

## Candidate intake

Run:

```bash
python scripts/inspect_hollywood2_explicit_crosswalk.py candidate \
  /path/outside/repository/authoritative-ledger.txt \
  /path/outside/repository/crosswalk-manifest.json \
  --output hollywood2-crosswalk-candidate.json
```

The candidate record includes:

- exact source and manifest hashes;
- canonical GIN tokens present;
- entry and unique-subject counts;
- one-to-one/completeness booleans;
- a mapping fingerprint derived from the local transcription;
- the frozen public-crosswalk-exhaustion evidence fingerprint;
- explicit non-promotion boundaries.

It does **not** copy original subject IDs or task-group labels into the candidate JSON.

A candidate cannot establish participant identity. Even a complete candidate remains
`syntactic-candidate-manual-review-required`.

## Manual review

Create a pending review template bound to the exact candidate:

```bash
python scripts/inspect_hollywood2_explicit_crosswalk.py review-template \
  hollywood2-crosswalk-candidate.json \
  --output hollywood2-crosswalk-review.json
```

The reviewer must independently inspect the authoritative source and resolve all review fields.
An approved review requires:

- `decision="approved"`;
- a reviewer identity and timezone-aware ISO-8601 `reviewed_at` timestamp;
- `source_authority_verified=true` plus evidence;
- `mapping_explicit_in_source_verified=true` plus evidence;
- `mapping_transcription_verified=true` plus evidence;
- `task_group_semantics_verified=true` plus evidence;
- `source_version_scope_verified=true` plus evidence;
- `rights_scope_promoted=false`;
- `empirical_validation_created=false`.

After editing, recompute the review fingerprint:

```bash
python scripts/inspect_hollywood2_explicit_crosswalk.py seal-review \
  hollywood2-crosswalk-review.json \
  --output hollywood2-crosswalk-review-sealed.json
```

Re-fingerprinting is not scientific approval by itself. Approval still depends on the manual
review content and the source/manifest replay performed at certificate time.

## Certificate

Once the review is genuinely complete:

```bash
python scripts/inspect_hollywood2_explicit_crosswalk.py certificate \
  /path/outside/repository/authoritative-ledger.txt \
  /path/outside/repository/crosswalk-manifest.json \
  hollywood2-crosswalk-candidate.json \
  hollywood2-crosswalk-review-sealed.json \
  --output hollywood2-crosswalk-certificate.json
```

The certificate step re-runs candidate intake from the exact local source and manifest. It
refuses promotion if source bytes, manifest bytes, mapping transcription, candidate fingerprint,
or review binding changed.

The generated certificate can be checked independently with:

```python
from gazeforge.hollywood2_explicit_crosswalk_certificate import (
    validate_certificate_record,
)

validate_certificate_record("hollywood2-crosswalk-certificate.json")
```

A valid certificate states that the explicit mapping was reviewed. It contains no raw mapping.
The actual mapping is returned only in memory by
`require_reviewed_explicit_crosswalk(...)` for downstream code that has access to the local
source and review materials.

## What this certificate does not establish

Even a valid reviewed crosswalk certificate does **not** by itself create:

- participant-disjoint Hollywood2 model-validation results;
- Lund↔Hollywood2 leave-one-dataset-out results;
- any new empirical performance claim;
- dataset reuse or redistribution rights;
- permission to redistribute raw Hollywood2 or Hollywood2EM data;
- native 60 Hz or Gazepoint GP3 validity.

Those are separate gates and remain false in the certificate's `scientific_boundary`.

The next scientific step after a genuine mapping certificate would be to use the reviewed
in-memory mapping to construct participant-disjoint Hollywood2 folds, then run and separately
freeze the resulting empirical validation. Until a real explicit source is supplied and
reviewed, the existing source-token-held-out evidence remains source-token evidence only.

## Local-data handling

Keep the authoritative source, transcription manifest, and manual review materials outside the
repository unless their redistribution/publication rights are independently established. The
CLI's default working filenames are ignored by Git to reduce accidental commits.

The intake reads only the small source file and JSON metadata supplied to it. It does not open,
scan, or redistribute raw gaze files.
