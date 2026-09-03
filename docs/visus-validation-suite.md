# VISUS validation suite

GazeForge can bind the audited VISUS source, reviewed human-reference extraction, model-prediction intake, and model-human evaluation into one deterministic completion manifest.

This layer is designed for **freezing reviewed evidence**, not for turning infrastructure or synthetic fixtures into empirical claims.

## What the suite binds

`run_visus_dynamic_aoi_validation_suite()` accepts:

- a verified `VisusSourceAuditRun`;
- a verified `VisusCanonicalAOIIntakeRun` containing the selected human-reference stream;
- a verified `VisusDynamicAOIPredictionIntakeRun` containing one explicit model/version;
- a separately supplied timestamp grid for every audited stimulus;
- the model-human evaluation settings;
- optionally, fixation tables;
- and, only when the source audit verifies independent streams, the two human stream IDs required for human-human agreement.

The suite revalidates every parent fingerprint before computing a child result.

## Completion semantics

The completion manifest is written **last**. Before that happens, GazeForge:

1. revalidates the source-audit report and specification fingerprints;
2. revalidates the human-reference and model-prediction intake reports;
3. checks that both intakes share the exact audited source and manifest identity;
4. confirms that model prediction intake did not generate the evaluation timestamp grid;
5. runs the model-human dynamic-AOI evaluation on the explicit external grid;
6. requires and runs human-human agreement when the source audit genuinely verifies independent annotation streams;
7. cross-checks child report source/model/reference/grid identities;
8. freezes all required child reports;
9. writes the deterministic suite manifest;
10. reopens and validates the manifest and every child report.

An orphan child JSON file is therefore not equivalent to a completed VISUS validation suite.

## Human-human agreement rule

The suite follows the project-wide evidence rule that human annotation variability should accompany model-human performance **when independently comparable human references are genuinely available**.

Accordingly:

- if the source audit does **not** verify separately recoverable independent annotation streams, the suite blocks any attempt to add a human-human child and records why that child is unavailable;
- if the source audit **does** verify independent streams, the suite refuses to complete unless the caller supplies two distinct stream IDs and the guarded human-human runner succeeds;
- neither human stream is treated as error-free ground truth.

The historical VISUS description of two contributors to one curation process is not sufficient to activate this path.

## Timestamp-grid rule

The model-prediction intake records `evaluation_timestamp_grid_generated=false`. The suite additionally requires the model-human child to report an explicit external timestamp grid and copies its per-stimulus grid fingerprints into the completion manifest.

This prevents detector emission times from becoming the benchmark comparison grid.

## Frozen artifacts

A model-human-only suite contains:

```text
visus-human-reference-intake.json
visus-model-prediction-intake.json
visus-model-human-validation.json
visus-dynamic-aoi-suite-manifest.json
```

When verified independent human streams exist, the required additional child is:

```text
visus-human-human-agreement.json
```

Each child has its own `report_fingerprint_sha256`. The completion manifest contains the exact child inventory and a separate `suite_fingerprint_sha256`.

## Example

```python
from gazeforge.visus_suite import run_visus_dynamic_aoi_validation_suite

suite = run_visus_dynamic_aoi_validation_suite(
    audit,
    reference_intake,
    prediction_intake,
    timestamps_by_stimulus,
    "validation/evidence/visus-run-001",
    reference_stream_id="published_curated",
    timestamp_grid_basis="Pre-registered 25 fps video-frame grid.",
    max_interpolation_gap_ms=80.0,
)
```

If an authoritative source later verifies two independent streams, pass for example:

```python
human_agreement_streams=("annotator_a", "annotator_b")
```

The suite will then require the human-human report as part of completion.

## Revalidation

A frozen suite can be checked independently:

```python
from gazeforge.visus_suite import validate_visus_dynamic_aoi_suite_manifest

status = validate_visus_dynamic_aoi_suite_manifest(
    "validation/evidence/visus-run-001"
)
```

By default, the validator checks the suite fingerprint, exact child inventory, safe relative paths, every child report fingerprint, shared source identity, model identity, selected human-reference stream, explicit timestamp-grid provenance, and the human-agreement independence/not-ground-truth rules.

## Claim boundary

Suite completion means that the required artifacts form a coherent, reproducible, fingerprinted tranche. It does **not** establish generalizable detector validity by itself.

A VISUS empirical result should only enter the public Frozen Evidence layer after the underlying authoritative source/reuse provenance, human extraction, model artifact/output provenance, evaluation grid, metrics, and resulting suite have been independently reviewed. Synthetic tests exercise the integrity machinery only.
