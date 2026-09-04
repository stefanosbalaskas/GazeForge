# VISUS empirical execution CLI

GazeForge provides a dedicated `gazeforge-visus` command for running the audited VISUS dynamic-AOI workflow from local reviewed files. The command is deliberately stricter than a convenience loader: it preserves the source-audit, human-intake, model-intake, external-grid, suite, and raw-execution-provenance boundaries already used by the Python APIs.

This interface is **execution infrastructure, not empirical evidence by itself**. A successful command only becomes an empirical VISUS result when the source specification describes a real authoritative copy, reuse and analysis permission are reviewed, the exact file manifest verifies, the human AOI extraction is reviewed, and the model output is generated from the exact audited videos.

## Installation entry point

After installing GazeForge, inspect the dedicated command:

```bash
gazeforge-visus --help
```

The same interface can be invoked without the console-script shim:

```bash
python -m gazeforge.visus_cli --help
```

## 1. Audit the exact source snapshot

```bash
gazeforge-visus audit \
  /path/to/visus/source \
  /path/to/visus-source-audit.json \
  --output audit-report.json
```

The source specification must already contain the exact recursive file manifest, SHA-256 values, byte sizes, explicit stimulus and participant identities, reviewed reuse/analysis evidence, coordinate evidence, and frame-time/timestamp evidence. A template specification cannot pass the empirical audit.

The historical publication's two-person annotation process is not interpreted as two independent annotation streams. `independent_annotation_streams_verified=true` remains a separate source-evidence claim and is accepted only when separately recoverable streams are actually manifested and justified.

## 2. Check the reviewed human AOI extraction

The CLI does not guess or reverse-engineer the historical ViPER XML schema. Supply the same reviewed frame-indexed canonical table required by `prepare_visus_canonical_aoi_intake`:

```bash
gazeforge-visus human-intake \
  /path/to/visus/source \
  /path/to/visus-source-audit.json \
  /path/to/reviewed-human-aoi.csv \
  --extraction-basis "Reviewed extraction from the exact audited AOI XML files" \
  --frame-index-base 1 \
  --output human-intake-report.json
```

CSV and TSV inputs are supported. Complete linkage to the audited AOI annotation manifest remains required by default.

## 3. Check detector/tracker output

```bash
gazeforge-visus prediction-intake \
  /path/to/visus/source \
  /path/to/visus-source-audit.json \
  /path/to/model-predictions.csv \
  --model-name my-detector \
  --model-version 1.0.0 \
  --prediction-basis "Inference on the exact audited VISUS videos" \
  --prediction-coordinate-unit pixels \
  --frame-index-base 1 \
  --model-artifact-sha256 <64-hex-model-digest> \
  --output prediction-intake-report.json
```

The model name, version, generation basis, coordinate unit, and frame-index convention are explicit. Model prediction frames are converted to canonical keyframe timestamps using the audited video rate, but those emission frames are **never** promoted to the evaluation timestamp grid.

## 4. Supply a separate evaluation timestamp grid

The suite command requires a JSON object whose keys are audited stimulus IDs and whose values are finite, strictly increasing timestamps in milliseconds:

```json
{
  "S01": [0.0, 40.0, 80.0],
  "S02": [0.0, 40.0, 80.0]
}
```

The real file must cover every audited stimulus required by the suite. The CLI deliberately has no option to derive this grid from the prediction table.

## 5. Run and freeze the complete suite

```bash
gazeforge-visus suite \
  /path/to/visus/source \
  /path/to/visus-source-audit.json \
  /path/to/reviewed-human-aoi.csv \
  /path/to/model-predictions.csv \
  /path/to/external-timestamp-grids.json \
  /path/to/frozen-visus-suite \
  --extraction-basis "Reviewed extraction from exact audited AOI XML" \
  --human-frame-index-base 1 \
  --model-name my-detector \
  --model-version 1.0.0 \
  --prediction-basis "Inference on exact audited VISUS videos" \
  --prediction-coordinate-unit pixels \
  --prediction-frame-index-base 1 \
  --model-artifact-sha256 <64-hex-model-digest> \
  --reference-stream-id reviewed-reference \
  --timestamp-grid-basis "Separately reviewed fixed video-time evaluation grid" \
  --max-interpolation-gap-ms 100
```

The command snapshots the four raw execution inputs before execution, re-runs the source audit, human canonical intake, and model prediction intake, then calls the atomic VISUS suite. The suite completion manifest is written only after all required children are computed, frozen, fingerprint-checked, and cross-checked against the same source identity.

After the suite has completed, the CLI fingerprints the four raw inputs again and re-runs the exact source audit. Any change to the raw input files or audited source tree blocks raw-execution provenance freezing. A successful run writes `visus-execution-provenance.json` alongside the suite manifest and child reports.

If the source audit genuinely verifies two separately recoverable independent annotation streams, a complete suite must also include them:

```bash
  --human-agreement-streams annotator-a,annotator-b
```

Supplying that option while independence is unverified is blocked. Conversely, if the audit says independent streams are verified and available, omitting the human-human child is also blocked.

## 6. Revalidate a frozen suite

```bash
gazeforge-visus suite-validate /path/to/frozen-visus-suite
```

For manifest-only inspection without opening referenced child reports:

```bash
gazeforge-visus suite-validate /path/to/frozen-visus-suite --manifest-only
```

## 7. Revalidate raw execution provenance

```bash
gazeforge-visus execution-validate /path/to/frozen-visus-suite
```

By default this verifies the execution-provenance fingerprint and structure, reopens the sibling suite and all child reports, and checks source identity, suite fingerprint, report count, parsed human/model table fingerprints, canonical fingerprints, and external timestamp-grid provenance.

For provenance-file inspection without reopening the sibling suite:

```bash
gazeforge-visus execution-validate /path/to/frozen-visus-suite --provenance-only
```

The provenance-only mode does not establish that the currently adjacent suite files still match the recorded binding.

## Scientific boundaries

The CLI does not relax the VISUS evidence policy:

- infrastructure completion is not empirical validation;
- the published two-contributor annotation process is not human-human reliability evidence;
- model-human evaluation uses one explicitly selected human reference stream and does not treat it as ground truth;
- detector/tracker emission frames never define the evaluation timestamp grid;
- raw ViPER XML parsing is not claimed unless an authoritative schema/sample is separately reviewed;
- analysis-use permission and raw-data redistribution rights remain separate provenance fields;
- exact raw-input fingerprints do not prove that a local VISUS copy is authoritative;
- no VISUS performance result should enter Frozen Evidence until the authoritative source, reviewed human extraction, model output, external grid, suite, and scientific review have all been completed.
