# VISUS execution provenance

The guarded VISUS workflow can now freeze a second manifest alongside the dynamic-AOI validation suite: `visus-execution-provenance.json`. Its purpose is narrow. It binds the exact raw files supplied to the execution command to the already-verified VISUS suite without turning provenance infrastructure into a new empirical claim.

## What is bound

The manifest records four raw execution inputs in a fixed role order:

1. the reviewed source-audit JSON;
2. the reviewed human AOI CSV/TSV table;
3. the detector/tracker prediction CSV/TSV table;
4. the separately supplied evaluation timestamp-grid JSON.

For every input, GazeForge records the basename, byte size, and SHA-256 digest. The source-audit JSON additionally receives a semantic fingerprint of the parsed `VisusSourceAuditSpec`. That semantic fingerprint must equal the source-spec fingerprint already carried by the verified source audit and frozen suite.

The manifest also binds the parsed human/model table fingerprints, canonical intake fingerprints, external timestamp-grid fingerprints and basis, exact source-audit/source-manifest fingerprints, suite fingerprint, and suite report count.

## Why the raw files are snapshotted twice

`gazeforge-visus suite` fingerprints the four raw input files before execution. After the source audit, canonical human intake, prediction intake, and atomic suite have completed, the same four files are fingerprinted again. A byte-level or semantic change causes provenance freezing to fail.

The CLI also re-runs the exact source audit after suite execution and requires the source-audit report fingerprint to remain unchanged. This catches mutation of the audited VISUS source tree during the run.

## Validation

A frozen execution manifest can be revalidated with:

```bash
gazeforge-visus execution-validate /path/to/frozen-visus-suite
```

By default the validator reopens the sibling suite manifest and every suite child. It verifies:

- the execution-manifest fingerprint and schema;
- the fixed four-role raw-input inventory;
- the source-spec semantic binding;
- the source-audit, source-spec, and source-manifest identity shared with the suite;
- the suite fingerprint and report count;
- the parsed human/model input and canonical fingerprints against the frozen intake children;
- the external timestamp-grid fingerprints and basis against the frozen suite protocol;
- that prediction-emission frames were not used as the evaluation grid.

For inspection of the provenance file alone, without reopening the sibling suite, use:

```bash
gazeforge-visus execution-validate /path/to/frozen-visus-suite --provenance-only
```

`--provenance-only` verifies the internal execution-manifest structure and fingerprint. It does not establish that the currently adjacent suite files still match the recorded binding.

## Python API

The module `gazeforge.visus_execution` exposes:

- `VisusExecutionInputSnapshot`;
- `VisusExecutionProvenanceRun`;
- `snapshot_visus_execution_inputs`;
- `verify_visus_execution_inputs_unchanged`;
- `build_visus_execution_provenance`;
- `write_visus_execution_provenance`;
- `validate_visus_execution_provenance`;
- `visus_execution_provenance_path`.

These functions are intentionally separate from source acquisition. They do not download VISUS, infer file roles, parse an undocumented historical ViPER XML schema, or decide whether the reviewed source is authoritative.

## Scientific limits

Execution provenance does not close any empirical VISUS task by itself. In particular:

- an exact local fingerprint does not prove that a copy is authoritative;
- analysis-use permission remains distinct from redistribution permission;
- a published two-contributor annotation process does not prove two independent annotation streams;
- a selected human reference stream is not ground truth;
- detector emission frames cannot silently become the evaluation timestamp grid;
- a frozen execution manifest does not create model-performance or human-reliability evidence unless the underlying real source and outputs have been independently reviewed.
