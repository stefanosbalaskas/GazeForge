# Grounding DINO + SAM 2 dynamic AOI backend

GazeForge includes an **optional, non-empirical** bridge for text-grounded dynamic AOI detection and video tracking. The backend combines a Grounding DINO open-vocabulary detector with SAM 2 video propagation and emits ordinary `DynamicAOIKeyframe` objects plus a fingerprinted per-frame table.

This backend is infrastructure. Its presence does **not** establish VISUS source authority, dataset rights, or model-human validity. Those remain separate gates.

## Why this backend

VISUS uses semantic moving AOIs such as cars, people, bags, hands, cards, and other scene-specific objects. A fixed closed-set detector is therefore a poor first benchmark target. Grounding DINO accepts text prompts for open-set detection, while SAM 2 propagates prompted objects through video. The upstream Grounding DINO project explicitly points to Grounded-SAM-2 for open-world video tracking.

The implementation contract was reviewed against these upstream snapshots on 10 September 2026:

- `IDEA-Research/Grounded-SAM-2@b7a9c29f196edff0eb54dbe14588d7ae5e3dde28`;
- `IDEA-Research/GroundingDINO@856dde20aee659246248e20734ef9ba5214f5e44`;
- `facebookresearch/sam2@2b90b9f5ceec907a1c18123530e92e794ad901a4`.

Grounded-SAM-2 and SAM 2 publish their code under Apache-2.0. The official Hugging Face `IDEA-Research/grounding-dino-tiny` model card currently identifies that model as Apache-2.0. GazeForge does not vendor or redistribute any third-party model code or weights; exact model/checkpoint terms still belong to the selected upstream artifacts.

## Scientific design

`GroundedSAM2DynamicAOIProvider` implements the existing GazeForge `DynamicAOIProvider` protocol. It deliberately keeps the heavyweight computer-vision stack optional and lazily imported.

Each execution requires:

- an immutable 40-character Hugging Face revision for the Grounding DINO model;
- an immutable 40-character Git revision for the SAM 2 code;
- a local SAM 2 checkpoint plus its exact SHA-256;
- an exact source-video file plus its exact SHA-256;
- a resolved statement describing how the JPEG frames were extracted from that source video;
- contiguous integer-named JPEG frames (`0.jpg`, `1.jpg`, ... or explicitly one-based);
- an explicit frame rate and prompt frame;
- predeclared semantic AOI labels.

Every JPEG is hashed. The report therefore binds both the source-video bytes and the exact frame set used by the model. GazeForge does **not** claim to mechanically re-decode the source video and prove that the supplied frame directory is a faithful decode; that provenance limitation is explicit in the report and can be closed later by a dedicated deterministic decoder/verification layer if required.

## Confidence semantics

Grounding DINO provides the seed detection score. SAM 2 then propagates the object mask through the video. The current bridge carries the seed score into the rectangular keyframes because the core `DynamicAOIKeyframe` schema requires a confidence value.

That value is explicitly recorded as **seed-detection confidence**, not per-frame SAM 2 tracking confidence. It must not be interpreted or reported as a frame-wise calibrated probability.

Empty or too-small propagated masks are skipped and counted. Mask geometry is required to remain constant across the run.

## Installation

Base GazeForge does not install the GPU/video stack. Install the ordinary vision dependencies, then install SAM 2 from its official repository at the exact revision you intend to report. SAM 2 currently documents Python 3.10+, PyTorch 2.5.1+, and torchvision 0.20.1+ for its current code.

A reproducible empirical run should record the exact installation commands, CUDA/runtime versions, immutable Git revisions, and checkpoint SHA-256 alongside the GazeForge report.

## Example

```python
from gazeforge.dynamic_aoi import detect_dynamic_aois
from gazeforge.grounded_sam2 import (
    GroundedSAM2Config,
    GroundedSAM2DynamicAOIProvider,
)

config = GroundedSAM2Config(
    grounding_model_id="IDEA-Research/grounding-dino-tiny",
    grounding_model_revision="<40-char HF commit SHA>",
    sam2_model_cfg="configs/sam2.1/sam2.1_hiera_s.yaml",
    sam2_checkpoint_path="/models/sam2.1_hiera_small.pt",
    sam2_checkpoint_sha256="<64-char SHA-256>",
    sam2_code_revision="<40-char SAM 2 Git commit SHA>",
    source_video_path="/data/stimulus.mp4",
    source_video_sha256="<64-char SHA-256>",
    frame_extraction_basis="ffmpeg <exact version and command>",
    frame_rate_hz=25.0,
    frame_index_base=0,
    prompt_frame_index=0,
    device="cuda",
)

provider = GroundedSAM2DynamicAOIProvider(config=config)
keyframes = detect_dynamic_aois(
    "/data/stimulus_frames",
    labels=["Red Car", "White Car"],
    provider=provider,
    min_confidence=0.0,
)

run = provider.last_run
assert run is not None
print(run.report["report_fingerprint_sha256"])
```

The Grounding DINO prompt is normalized to lower-case, period-terminated phrases following the upstream inference guidance, while GazeForge preserves the caller's exact semantic labels in the canonical output.

## VISUS handoff

After an authoritative VISUS copy and analysis rights are verified, each backend run can be converted directly to the existing VISUS prediction-intake schema:

```python
from gazeforge.grounded_sam2 import grounded_sam2_to_visus_prediction_table
from gazeforge.visus_prediction import prepare_visus_dynamic_aoi_predictions

predictions = grounded_sam2_to_visus_prediction_table(
    run,
    stimulus_id="S01",
)

prediction_intake = prepare_visus_dynamic_aoi_predictions(
    audit,
    predictions,
    model_name=run.report["model_name"],
    model_version=run.report["model_version"],
    prediction_basis=(
        "Grounded-SAM-2 backend report "
        + run.report["report_fingerprint_sha256"]
    ),
    prediction_coordinate_unit="pixels",
    frame_index_base=0,
)
```

Before that handoff is accepted for empirical work, the backend report's `source_video.sha256` must equal the corresponding audited VISUS video SHA-256. The authoritative source audit remains responsible for the dataset identity, coordinate basis, frame/time basis, and rights decision.

## What this tranche does not do

It does not:

- download or bundle model weights;
- create a VISUS prediction result from the recovered Osnabrück derivative;
- use human AOI geometry to seed the model;
- infer an evaluation grid from model-emission frames;
- claim that text-prompted localization is fully unsupervised object discovery;
- claim per-frame calibrated tracker confidence;
- create model-human performance evidence;
- satisfy the authoritative VISUS source/rights roadmap item.

For later VISUS evaluation, the semantic prompt ontology must be declared before inspecting model outputs. Using the benchmark's declared AOI class names is class-level supervision; the model must not receive the human AOI coordinates, masks, or keyframes being used as the reference.

## Next empirical gate

When the requested VISUS source arrives from a current custodian, the sequence is:

1. validate source authority and analysis/redistribution terms with the existing VISUS certificate path;
2. audit and hash the authoritative videos and AOI files;
3. verify the model input source-video SHA against the audited video SHA;
4. predeclare the semantic prompts and model configuration;
5. run Grounding DINO + SAM 2 without using human reference geometry;
6. pass its table through `prepare_visus_dynamic_aoi_predictions`;
7. evaluate on a separately supplied timestamp grid;
8. freeze model-human reports only after the complete provenance chain revalidates.
