# Gaze-in-the-Wild explicit task-mapping intake

GazeForge currently **does not have an authoritative complete mapping** from the numeric `TrIdx` values in the distributed Gaze-in-the-Wild `ProcessData` files to the four publication task labels. The reviewed public-source search remains frozen as unresolved by `gaze-in-wild-authoritative-task-mapping-exhaustion-evidence-v1` (fingerprint `c0e8e0da36d329d6445dace1a56646b89c9df5f4f406761311d588eddaf36aa7`).

This intake exists so that a future explicit author, first-party repository, original-distribution, or publication-supplement record can be reviewed without weakening that boundary.

## What this mechanism does

The workflow has four local phases:

1. **Candidate** — hash the exact source and a local transcription manifest, validate the syntax, canonical `TrIdx` domain, publication-task vocabulary, one-to-one structure, and current exhaustion-evidence binding.
2. **Review template** — create a pending record bound to the exact candidate fingerprint.
3. **Sealed review** — after a human reviewer fills the evidence fields, recompute the review fingerprint.
4. **Certificate** — replay the exact source and manifest and emit a non-empirical certificate only when every review gate passes.

The source and transcription manifest remain local. The candidate and certificate contain hashes, counts, canonical ledgers, and boundary flags, but **not the raw `TrIdx → task` pairing**.

## Admissible source classes

A manifest may declare only one of these syntactic authority classes:

- `author_statement`
- `first_party_repository_record`
- `original_distribution_metadata`
- `publication_supplement`

Passing this syntactic allow-list is **not** authority verification. The reviewer must separately establish why the exact source is authoritative and record that evidence in the review.

Secondary repackaging, inferred directory order, publication task order, and a count match are not admissible substitutes for an explicit lookup.

## Required mapping structure

The canonical trial-index domain is exactly `1, 2, 3, 4`. The canonical publication-task vocabulary is exactly:

- `Indoor_Walk`
- `Ball_Catch`
- `Visual_Search`
- `Tea_Making`

A candidate may be partial so that newly found evidence can be inspected safely. **A partial candidate cannot be approved.** Promotion requires exactly four unique `TrIdx` values and exactly four unique canonical task labels.

The local manifest must use record type `gaze-in-wild-explicit-task-mapping-source-v1`, bind the exact source-file SHA-256, affirm that the source was obtained through an authorized channel, and contain `mapping_entries` with `trial_index` and `task_label` fields copied from the source.

## The `TrIdx 4` anti-inference gate

The existing evidence base contains secondary-only corroboration for part of the numeric mapping but does not authoritatively resolve the complete lookup. In particular, **`TrIdx 4 → Tea_Making` must not be filled by elimination** merely because three other task labels appear elsewhere.

An approved review therefore requires both:

- `tridx4_explicit_in_source_verified=true`, with resolved evidence showing that the authoritative source explicitly states the `TrIdx 4` pairing; and
- `no_elimination_or_order_inference_used_verified=true`, with evidence that neither publication order nor directory order nor elimination supplied any pairing.

A complete-looking transcription still fails closed if either assertion is absent.

## CLI

Use the local helper only after you possess a legitimate candidate source:

```bash
python scripts/inspect_gaze_in_wild_explicit_task_mapping.py candidate SOURCE MANIFEST \
  --output gaze-in-wild-task-mapping-candidate.json

python scripts/inspect_gaze_in_wild_explicit_task_mapping.py review-template \
  gaze-in-wild-task-mapping-candidate.json \
  --output gaze-in-wild-task-mapping-review.json
```

Edit the review manually. An approval must include a timezone-aware review timestamp, reviewer identity, resolved evidence text for every gate, and explicit `true` values for authority, mapping explicitness, transcription, publication-task semantics, source-version scope, direct `TrIdx 4` evidence, and the no-inference rule. Rights, empirical-validation, and quarantine-exit promotion flags must remain `false`.

Then seal and validate it:

```bash
python scripts/inspect_gaze_in_wild_explicit_task_mapping.py seal-review \
  gaze-in-wild-task-mapping-review.json \
  --output gaze-in-wild-task-mapping-review-sealed.json

python scripts/inspect_gaze_in_wild_explicit_task_mapping.py certificate \
  SOURCE MANIFEST \
  gaze-in-wild-task-mapping-candidate.json \
  gaze-in-wild-task-mapping-review-sealed.json \
  --output gaze-in-wild-task-mapping-certificate.json
```

## What a certificate does not establish

Even a genuinely reviewed mapping certificate creates **no empirical result** by itself. It does not claim task-stratified performance, participant-disjoint performance, cross-dataset validity, native 60 Hz validity, Gazepoint GP3 validity, acquisition-hardware cadence, quarantine exit, dataset rights, or raw-data retention rights.

Once an authoritative mapping is actually recovered and reviewed, a separate empirical tranche must consume the reviewed mapping and rerun the relevant Gaze-in-the-Wild validation before any task-stratified scientific claim is promoted.

Until such source evidence exists, Issue #1's authoritative `TrIdx → publication-task` mapping gate remains open.
