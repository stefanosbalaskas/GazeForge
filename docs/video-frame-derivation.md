# Verified video-to-frame derivation

GazeForge can mechanically derive the exact JPEG frame directory used by a video model from an exact source-video file. This closes a provenance gap that remains intentionally open when a researcher supplies an already-extracted frame directory.

The layer is **model-input provenance infrastructure**. It does not establish dataset authority, reuse rights, redistribution rights, annotation validity, or model performance.

## Why this layer exists

The Grounding DINO + SAM 2 backend binds two things independently:

- the exact source-video SHA-256; and
- the SHA-256 of every supplied JPEG frame.

That is necessary but, by itself, it does not prove that the supplied JPEGs were actually decoded from the bound source video.

`derive_video_frames()` changes that relationship. GazeForge invokes a local extractor itself, starting from an absent or empty output directory, and records the exact transformation that produced the model-input frames.

## What is bound

A successful `VideoFrameDerivationRun` binds:

- source-video path, byte count, and SHA-256;
- extractor name and exact version string;
- extractor executable path, byte count, and SHA-256;
- exact extraction argument vector;
- extractor return code;
- SHA-256 and byte count of captured stdout and stderr;
- JPEG quality setting;
- explicit zero- or one-based frame indexing;
- every produced JPEG basename, frame index, byte count, and SHA-256;
- a deterministic frame-manifest fingerprint;
- a deterministic report fingerprint.

The validator re-hashes the source video, extractor executable, and every output frame. Mutation of any of those local bytes invalidates the run.

## Built-in FFmpeg extractor

`FFmpegJPEGFrameExtractor` is the production extractor supplied by this tranche. It resolves the exact local FFmpeg executable, hashes it, records the first line of `ffmpeg -version`, and invokes FFmpeg with an explicit argument vector.

The extraction uses the first video stream and requests timestamp passthrough rather than imposing a new constant frame rate:

```text
ffmpeg
  -nostdin
  -hide_banner
  -loglevel error
  -i <source-video>
  -map 0:v:0
  -fps_mode passthrough
  -q:v <quality>
  -start_number <0-or-1>
  <output-dir>/%06d.jpg
```

Numeric JPEG naming is intentionally compatible with the SAM 2 video-frame loader. The output directory must be absent or empty before execution; GazeForge does not mix newly decoded frames with pre-existing files.

The default `q:v` value is `2`. JPEGs are derived model inputs, not byte-identical copies of encoded video frames.

## Pin the extractor before execution

For an auditable run, inspect the local FFmpeg identity and pin the observed values into `VideoFrameDerivationConfig`. The executable SHA-256 is treated as part of the scientific execution identity rather than assuming that every executable called `ffmpeg` is equivalent.

A project can also supply another local extractor implementing the narrow `VideoFrameExtractor` protocol. The same source, tool, execution, and output validation still applies.

## Example

```python
import hashlib
from pathlib import Path

from gazeforge.video_frame_derivation import (
    FFmpegJPEGFrameExtractor,
    VideoFrameDerivationConfig,
    derive_video_frames,
)

ffmpeg = FFmpegJPEGFrameExtractor("/usr/bin/ffmpeg")
identity = ffmpeg.identify()

video = Path("/data/stimulus.mp4")
video_sha = hashlib.sha256(video.read_bytes()).hexdigest()

config = VideoFrameDerivationConfig(
    source_video_path=video,
    source_video_sha256=video_sha,
    output_dir="/data/stimulus-frames",
    expected_extractor_name=identity.name,
    expected_extractor_version=identity.version,
    expected_extractor_sha256=identity.artifact_sha256,
    frame_index_base=0,
    jpeg_quality=2,
)

derivation = derive_video_frames(config, extractor=ffmpeg)
print(derivation.report["report_fingerprint_sha256"])
```

For large video files, use the repository's ordinary streaming hash utilities or another streaming SHA-256 command when preparing the pinned source digest; the example above is deliberately compact.

## Grounding DINO + SAM 2 orchestration

`run_grounded_sam2_with_verified_frame_derivation()` performs the full implementation-side chain:

1. verify the source-video SHA-256;
2. verify the pinned extraction-tool identity;
3. create the output frame directory from an absent/empty state;
4. invoke the extractor;
5. hash and validate the complete numeric frame sequence;
6. pass that exact generated directory to the existing Grounded-SAM-2 backend;
7. revalidate the Grounded-SAM-2 run;
8. require the backend source-video SHA to equal the derivation source SHA;
9. require the backend frame manifest to equal the mechanical derivation manifest;
10. emit a separate binding fingerprint.

The Grounded-SAM-2 backend's own `frame_derivation_mechanically_verified` field remains `false` by design: the backend alone did not perform the decode. The separate binding record is the object that can truthfully state that mechanical derivation has been verified.

This separation prevents a caller from promoting an unverified pre-existing JPEG directory merely by changing a configuration string.

## Combined example

```python
from gazeforge.grounded_sam2 import GroundedSAM2Config
from gazeforge.video_frame_derivation import (
    run_grounded_sam2_with_verified_frame_derivation,
)

grounded = GroundedSAM2Config(
    grounding_model_id="IDEA-Research/grounding-dino-tiny",
    grounding_model_revision="<40-character immutable HF revision>",
    sam2_model_cfg="configs/sam2.1/sam2.1_hiera_s.yaml",
    sam2_checkpoint_path="/models/sam2.1_hiera_small.pt",
    sam2_checkpoint_sha256="<64-character checkpoint SHA-256>",
    sam2_code_revision="<40-character SAM 2 Git revision>",
    source_video_path=video,
    source_video_sha256=video_sha,
    frame_extraction_basis="Superseded by verified derivation at execution.",
    frame_rate_hz=25.0,
    frame_index_base=0,
    prompt_frame_index=0,
    device="cuda",
)

combined = run_grounded_sam2_with_verified_frame_derivation(
    config,
    grounded,
    labels=["Red Car", "White Car"],
    extractor=ffmpeg,
)

assert combined.binding_report["frame_derivation_mechanically_verified"] is True
```

The model runtime remains optional and is not installed or downloaded by the base GazeForge CI matrix.

## Validation boundaries

A verified frame derivation means only that the recorded local extraction process produced the exact JPEG bytes later consumed by the model. It does **not** mean:

- the source video is an authoritative copy of a benchmark;
- analysis or redistribution rights have been established;
- the derived JPEGs may be redistributed;
- FFmpeg's decoding is a ground-truth representation of scene content;
- model detections are correct;
- human AOI annotations are correct;
- model-human agreement has been measured;
- any VISUS Frozen Evidence gate has been satisfied.

Those are separate evidentiary questions.

## VISUS use

For VISUS, this layer should be used only after the existing authoritative-source and rights gates permit analysis of an exact source copy.

A future empirical execution should therefore bind:

```text
authoritative VISUS source certificate
        ↓
audited exact stimulus video SHA-256
        ↓
verified source-video → JPEG derivation
        ↓
Grounding DINO + SAM 2 backend report
        ↓
derivation/backend binding fingerprint
        ↓
VISUS prediction intake
        ↓
predeclared external evaluation timestamp grid
        ↓
model-human evaluation
```

The recovered University of Osnabrück converted derivative is not promoted to an authoritative VISUS source by this functionality.

## Reproducibility note

The extractor executable SHA and version output are recorded because decoder implementation identity matters. The produced JPEGs themselves are also fully hashed, so the scientific record identifies the exact model inputs even when another platform or decoder build would not reproduce byte-identical JPEG encodings.

This is stronger than relying on an undocumented statement such as “frames were extracted with FFmpeg,” but it remains a provenance record rather than a claim that all decoder environments are computationally equivalent.
