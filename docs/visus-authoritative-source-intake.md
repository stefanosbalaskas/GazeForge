# VISUS authoritative source and rights intake

The VISUS source scaffold can fingerprint a local candidate tree, but a tree fingerprint alone does not establish that the copy is authoritative or that its reuse terms permit analysis. The authoritative-source intake adds a separate fail-closed gate between **candidate recovery** and the existing detailed `VisusSourceAuditSpec` review.

This mechanism does **not** claim that an authoritative current VISUS copy has already been recovered. It exists so that a legitimately obtained future copy can be reviewed without turning filenames, a download location, a modern DaRUS licence, or a researcher assertion into empirical authority by accident.

## Four exact bindings

A candidate binds:

1. the exact source artifact bytes by SHA-256;
2. the exact extracted local tree by the existing VISUS scaffold inventory fingerprint;
3. the exact rights-evidence file by SHA-256;
4. a closed-schema source manifest naming the source reference, source revision, authority class, rights-evidence reference, and authorized-channel affirmation.

The source artifact, rights evidence, manifest, and generated review records must remain outside the inventoried source tree. The source artifact, rights evidence, and manifest must also be distinct files. The repository `.gitignore` protects the standard `visus-source-authority-*.json` working-record names; source and rights evidence should remain local and should not be committed.

Allowed authority classes are deliberately narrow:

- `author_hosted_distribution`;
- `institutional_repository`;
- `original_distribution_copy`.

A third-party repack, filename similarity, derivative dataset, or modern unrelated DaRUS record cannot pass the authority-class gate.

## Candidate stage: no promotion

Create a candidate with:

```bash
python scripts/inspect_visus_authoritative_source.py candidate \
  /path/to/extracted-visus \
  /path/to/original-source-artifact \
  /path/to/rights-evidence \
  visus-source-authority-manifest.json \
  --output visus-source-authority-candidate.json
```

The candidate records hashes, source identifiers, inventory size, and the published 25-participant / 11-stimulus expectations. It does **not** infer file roles, participants, stimuli, rights, or empirical readiness.

All review flags remain false. Re-fingerprinting an altered candidate does not permit promotion because the candidate and nested sections use closed schemas and fixed non-promoting boundaries.

## Manual authority and rights review

Generate a review template:

```bash
python scripts/inspect_visus_authoritative_source.py review-template \
  visus-source-authority-candidate.json \
  --output visus-source-authority-review.json
```

An approved review must independently establish all of the following:

- the source is authoritative;
- the reviewed source identity is the current authoritative distribution identity for the claimed revision;
- the exact source artifact matches that authoritative distribution;
- the extracted tree matches the source artifact;
- the rights evidence is authoritative for this source/revision;
- analysis use is explicitly permitted;
- redistribution status is explicitly classified as `permitted`, `prohibited`, or `not_stated`;
- the rights scope is limited to the reviewed source rather than transferred from a paper, software repository, derivative dataset, or unrelated modern deposit.

The reviewer must supply resolved evidence text for every promoted authority/right gate and a timezone-aware review timestamp. After editing, seal the review fingerprint:

```bash
python scripts/inspect_visus_authoritative_source.py seal-review \
  visus-source-authority-review.json \
  --output visus-source-authority-review-sealed.json
```

## Certificate stage

The certificate command replays the exact local tree, source artifact, rights evidence, and manifest before accepting the review:

```bash
python scripts/inspect_visus_authoritative_source.py certificate \
  /path/to/extracted-visus \
  /path/to/original-source-artifact \
  /path/to/rights-evidence \
  visus-source-authority-manifest.json \
  visus-source-authority-candidate.json \
  visus-source-authority-review-sealed.json \
  --output visus-source-authority-certificate.json
```

A valid certificate may establish only that the exact candidate has passed **source-authority and analysis-rights review** and may proceed to the detailed VISUS source-audit stage. It carries the reviewed redistribution status but **never authorizes a redistribution action by itself**, even when the reviewed terms say redistribution is permitted.

The certificate does not copy raw rights text. It stores the rights-evidence hash/reference and reviewed licence-or-terms identifier.

## Binding the certificate to a detailed source audit

A reviewed certificate is now replayed against the detailed `VisusSourceAuditSpec` before the installed empirical VISUS CLI may proceed. The binding requires exact agreement on:

- source reference and source revision;
- licence/terms identifier and rights-evidence reference;
- analysis-use permission and redistribution classification;
- published 25-participant and 11-stimulus boundaries;
- file count;
- the exact neutral source-tree fingerprint originally produced by the scaffold.

The neutral inventory comparison deliberately discards the later scientific role assignments and reconstructs the original `role="other"` scaffold fingerprint. That means later video/gaze/AOI classification cannot silently create a new source identity.

The bound audit adds the reviewed `source_authority_certificate_fingerprint_sha256` to its report and recomputes the source-audit report fingerprint. Because all downstream VISUS intake and validation reports already bind the source-audit report fingerprint, they transitively inherit the reviewed authority identity without treating the certificate as scientific validation.

## Empirical CLI and Frozen Evidence

The installed `gazeforge-visus` command requires the reviewed certificate for every empirical creation command:

```bash
gazeforge-visus suite \
  /path/to/extracted-visus \
  visus-source-audit.json \
  human-aoi.csv \
  model-predictions.csv \
  timestamp-grids.json \
  /path/to/output \
  --authority-certificate visus-source-authority-certificate.json \
  --extraction-basis "reviewed extraction from audited AOI XML" \
  --human-frame-index-base 1 \
  --model-name detector \
  --model-version 1.0 \
  --prediction-basis "reviewed detector output" \
  --prediction-coordinate-unit pixels \
  --prediction-frame-index-base 1 \
  --reference-stream-id annotator_a \
  --timestamp-grid-basis "reviewed external video-frame grid" \
  --max-interpolation-gap-ms 100
```

The same certificate option is required for `audit`, `human-intake`, and `prediction-intake`.

A completed suite is sealed with the exact certificate fingerprint. Current execution provenance uses `gazeforge-visus-execution-provenance-v2` and freezes five governed input files: source-audit JSON, authority-certificate JSON, human AOI table, model prediction table, and external timestamp-grid JSON. The authority certificate is bound by both its raw-file SHA-256 and its validated semantic certificate fingerprint.

Current VISUS Frozen Evidence rejects legacy four-input execution provenance. Publication eligibility requires one identical authority-certificate fingerprint across the bound source audit, suite source/protocol identity, and v2 execution provenance.

## What remains required after a certificate

A source-authority certificate is not a `dataset_status="empirical"` source audit. The existing VISUS audit must still independently resolve and verify:

- exact video, gaze, AOI-annotation, and other file roles;
- all 11 stimulus identities and mappings;
- all 25 participant identities and mappings;
- coordinate units and their evidence basis;
- timestamp/frame-time basis;
- AOI annotation-stream identities;
- whether separately recoverable independent annotation streams genuinely exist.

Only after those gates pass can downstream human-human or model-human validation be considered. A certificate therefore creates **no** AOI performance claim, human-human agreement, model-human validation, Frozen Evidence eligibility, or native-device validity claim.

## Relationship to current public evidence

The intake is bound to the frozen VISUS authoritative-source recheck. That recheck found the current institutional publication listing but did not find a current authoritative download, a matching 2014 benchmark DaRUS deposit, a separate benchmark dataset DOI, or explicit current benchmark dataset licence. Modern DaRUS CC BY 4.0 examples and the reviewed public derivative evidence remain non-transferable to the missing full 2014 benchmark copy.

Accordingly, adding this intake and binding mechanism does not complete the Issue #1 checkbox to obtain/verify an authoritative current VISUS copy and reuse/distribution terms. It makes that future verification reproducible and fail-closed once legitimate evidence is available.
