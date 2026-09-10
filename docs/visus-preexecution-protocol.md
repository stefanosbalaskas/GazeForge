# VISUS pre-execution protocol freeze

GazeForge can freeze the analysis choices for a VISUS Grounding DINO + SAM 2
dynamic-AOI benchmark **before a protocol-bound backend execution**.

This layer exists to prevent a weaker workflow in which prompts, detector thresholds,
model identity, or scoring settings are merely documented after predictions or
reference-performance results already exist.

The protocol is deliberately narrower than a formal preregistration. A cryptographic
fingerprint proves the identity of the frozen content. It does **not** prove that a
researcher had never inspected earlier outputs outside the protocol-bound execution.

## What the protocol freezes

`build_visus_grounded_sam2_preexecution_protocol()` and
`freeze_visus_grounded_sam2_preexecution_protocol()` bind the following before
Grounded-SAM-2 inference is allowed through the protocol-bound runner:

- the verified VISUS source-audit report, specification, and manifest fingerprints;
- the exact audited source video for every stimulus;
- the mechanically verified video-to-JPEG derivation report for every stimulus;
- the exact derived-frame manifest fingerprint;
- Grounding DINO model identifier and immutable revision;
- SAM 2 code revision, model configuration, checkpoint basename, byte count, and
  checkpoint SHA-256;
- one global detector/tracker policy across all VISUS stimuli;
- Grounding DINO box and text thresholds;
- frame rate and frame-index base;
- device, local-files-only setting, and minimum mask size;
- the semantic AOI labels and normalized prompt text for every stimulus;
- the prompt frame for every stimulus;
- the exact external timestamp grid for every stimulus;
- the human reference-stream identifier;
- timestamp-grid basis;
- maximum AOI interpolation gap;
- IoU match threshold;
- semantic-label match requirement;
- whether fixation-assignment analysis is planned; and
- the fixation-overlap rule.

The full timestamp values are embedded in the generated protocol, not only summarized.
Each grid also receives its own deterministic fingerprint.

## One model policy across stimuli

The protocol allows semantic labels and prompt frames to differ by stimulus because
the benchmark scenarios contain different AOI classes.

It does **not** allow per-stimulus changes to the model/checkpoint/threshold policy.
All stimuli must share one exact:

```text
Grounding DINO model + revision
SAM 2 code revision + configuration + checkpoint
frame rate + frame-index base
box threshold + text threshold
device + local-files-only policy
minimum mask-pixel rule
```

This fail-closed rule prevents scenario-by-scenario threshold tuning from being hidden
inside an otherwise complete benchmark run.

## Source and rights boundary

A protocol can be built only from a verified empirical `VisusSourceAuditRun` whose
reviewed reuse terms permit analysis.

That does **not** make the pre-execution protocol a new source-authority mechanism.
The existing authoritative-source intake, manual review, and certificate remain the
separate gate for authoritative distribution identity and rights.

The protocol therefore records:

```text
source_authority_certificate_required_separately = true
dataset_source_authority_promoted = false
dataset_rights_promoted = false
```

No raw VISUS source bytes are copied into the protocol.

## Mechanical frame provenance is mandatory

Every stimulus plan requires a valid `VideoFrameDerivationRun`.

The Grounded-SAM-2 configuration must name the same exact source-video SHA-256 and use
this exact extraction basis:

```text
GazeForge mechanically verified video-frame derivation <derivation-report-sha256>
```

The protocol revalidates the source video, extraction-tool identity, output-frame
bytes, frame-manifest fingerprint, and SAM 2 checkpoint bytes before freezing.

A pre-existing unverified JPEG directory therefore cannot be promoted into this
protocol simply by supplying a descriptive string.

## External evaluation grid

Prediction emission frames are never allowed to become the model-human evaluation
grid.

The caller supplies `timestamps_by_stimulus` independently. The protocol requires
complete audited-stimulus coverage, finite values, and strict monotonic increase.

The frozen document stores both the exact values and, for every stimulus:

- timestamp count;
- first and last timestamp;
- timestamp-grid SHA-256 fingerprint.

The protocol permanently records:

```text
prediction_emission_grid_used = false
```

## Freeze before execution

A typical scientific workflow is:

```python
from gazeforge.visus_preexecution_protocol import (
    VisusGroundedSAM2StimulusPlan,
    freeze_visus_grounded_sam2_preexecution_protocol,
    run_grounded_sam2_from_preexecution_protocol,
)

plans = {
    "S01": VisusGroundedSAM2StimulusPlan(
        stimulus_id="S01",
        labels=("red car", "white car"),
        config=s01_grounded_config,
        derivation=s01_derivation,
    ),
    # ...exactly one plan for every audited VISUS stimulus...
}

protocol = freeze_visus_grounded_sam2_preexecution_protocol(
    audit,
    plans,
    timestamps_by_stimulus,
    "outputs/visus-grounded-sam2-preexecution-protocol.json",
    reference_stream_id="published_curated",
    timestamp_grid_basis="Externally fixed audited 25 Hz video-frame grid.",
    max_interpolation_gap_ms=80.0,
    min_iou=0.50,
    require_label_match=True,
    fixation_assignment_planned=False,
    overlap_rule="highest_confidence",
)

s01 = run_grounded_sam2_from_preexecution_protocol(
    protocol,
    audit,
    plans["S01"],
    runtime=runtime,
)
```

The protocol-bound runner performs the important ordering internally:

1. reload and fingerprint-check the frozen protocol file;
2. revalidate the current source audit;
3. revalidate the current source video, checkpoint, derivation, and frame bytes;
4. require the current stimulus plan to equal the frozen plan;
5. only then call Grounded-SAM-2;
6. bind the backend output to the mechanical frame derivation; and
7. bind the backend report to the frozen pre-execution protocol.

The resulting binding can truthfully state:

```text
protocol_validated_before_backend_call = true
local_execution_order_verified = true
```

That statement applies only to this GazeForge execution path.

## Replay before reuse

Use `replay_visus_grounded_sam2_preexecution_protocol()` before a later run when the
original in-memory plan objects are still available.

Replay rebuilds the complete protocol from the current local source audit, model
configs, checkpoint bytes, frame-derivation runs, timestamp grids, and frozen
evaluation settings. Any mismatch is rejected.

`load_visus_grounded_sam2_preexecution_protocol()` is the lighter structural loader.
It verifies the document fingerprint and scientific claim boundaries but does not by
itself recreate unavailable local model/source inputs.

## Downstream model-human settings

`validation_settings_from_preexecution_protocol()` returns the exact frozen model-human
evaluation settings:

```python
settings = validation_settings_from_preexecution_protocol(protocol)

timestamps = settings["timestamps_by_stimulus"]
reference_stream = settings["reference_stream_id"]
grid_basis = settings["timestamp_grid_basis"]
max_gap = settings["max_interpolation_gap_ms"]
min_iou = settings["min_iou"]
require_label_match = settings["require_label_match"]
overlap_rule = settings["overlap_rule"]
```

These values should be passed unchanged into the existing VISUS model-human validation
suite once authoritative source/rights and empirical execution prerequisites are
satisfied.

## Formal preregistration boundary

The protocol may record an external registration reference and a timezone-aware
registration timestamp.

Those values are **metadata only**. This layer deliberately keeps:

```text
formal_preregistration_verified = false
```

even when such metadata are present.

A future formal-preregistration certificate would need to verify a trusted external
registration or timestamping service and bind that external evidence to the exact
GazeForge protocol fingerprint. Merely typing an OSF/registry URL and timestamp into
a local file is not sufficient.

## What this tranche does not claim

A successful pre-execution protocol does not establish:

- that the 2014 VISUS copy is the current authoritative distribution;
- redistribution permission;
- independent human annotation streams;
- human-human agreement;
- Grounding DINO + SAM 2 accuracy;
- model-human validity;
- a formal preregistration; or
- a Frozen Evidence result.

Those gates remain independent and fail closed.
