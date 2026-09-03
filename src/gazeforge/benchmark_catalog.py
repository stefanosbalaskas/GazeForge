"""Evidence-aware catalog entries for external GazeForge validation datasets."""

from __future__ import annotations

from .benchmarks import BenchmarkDatasetCard


def visus_dynamic_aoi_card() -> BenchmarkDatasetCard:
    """Return the verified metadata card for the VISUS dynamic-AOI benchmark.

    The historical data endpoint has moved/retired, so GazeForge records the benchmark but does
    not claim to redistribute it or provide a stable downloader until current reuse terms and a
    surviving authoritative distribution location are independently verified.
    """
    return BenchmarkDatasetCard(
        name="VISUS",
        version="Kurzhals-et-al-2014",
        source=(
            "Kurzhals, Heimerl & Weiskopf (ETRA 2014); historical VISUS Stuttgart "
            "benchmark-eyetracking distribution"
        ),
        license="Reuse/distribution terms require independent verification; not bundled",
        task="dynamic video AOI detection and fixation-to-AOI assignment",
        sampling_rates_hz=[60.0],
        participant_count=25,
        stimulus_count=11,
        split_unit="stimulus_id",
        validation_scope="external-empirical-benchmark-candidate",
        annotation_origin="human-manual",
        sampling_origin="native",
        reference_strength="human-reference",
        human_annotator_count=2,
        reference_description=(
            "Two independent human annotators supplied rectangular AOI keyframes; intermediate "
            "AOI positions were interpolated in the published evaluation workflow."
        ),
        notes=[
            "Native 60 Hz gaze was recorded with a Tobii T60 XL in the published benchmark.",
            "The dataset contains 25 participants viewing 11 dynamic video stimuli.",
            "Do not redistribute raw files until current reuse terms are verified.",
        ],
    )


def hollywood2_manual_event_card() -> BenchmarkDatasetCard:
    """Return metadata for the expert-corrected Hollywood2 eye-movement annotations."""
    return BenchmarkDatasetCard(
        name="Hollywood2-manual-events",
        version="Agtzidis-Startsev-Dorr-2020",
        source="https://gin.g-node.org/ioannis.agtzidis/hollywood2_em",
        license="Article CC BY 4.0; dataset-specific redistribution terms must be checked",
        task="sample-level fixation/saccade/smooth-pursuit/noise classification",
        sampling_rates_hz=[500.0],
        participant_count=16,
        stimulus_count=56,
        split_unit="participant_id",
        validation_scope="external-cross-dataset-human-reference-candidate",
        annotation_origin="human-assisted",
        sampling_origin="native",
        reference_strength="expert-human-reference",
        human_annotator_count=2,
        reference_description=(
            "A novice annotator used rudimentary algorithmic suggestions and an expert annotator "
            "subsequently corrected the sample-level event labels."
        ),
        notes=[
            "Approximately 130 minutes of manually annotated gaze data.",
            "Recorded at 500 Hz with an SMI iView X HiSpeed 1250.",
            "Useful for cross-dataset validation, not as a native low-rate/GP3-class benchmark.",
        ],
    )


def gaze_in_wild_manual_event_card() -> BenchmarkDatasetCard:
    """Return metadata for the independently hand-labelled Gaze-in-the-Wild corpus."""
    return BenchmarkDatasetCard(
        name="Gaze-in-the-Wild-manual-events",
        version="Kothari-et-al-2020",
        source="https://doi.org/10.1038/s41598-020-59251-5",
        license=(
            "Article open access; dataset-specific redistribution terms require verification; "
            "raw data not bundled"
        ),
        task="head-free fixation/saccade/pursuit/blink/VOR classification",
        sampling_rates_hz=[120.0],
        participant_count=19,
        stimulus_count=None,
        split_unit="participant_id",
        validation_scope="external-native-low-rate-human-reference-candidate",
        annotation_origin="human-manual",
        sampling_origin="native",
        reference_strength="human-reference",
        human_annotator_count=5,
        reference_description=(
            "Five trained annotators independently hand-labelled naturalistic head-free gaze; "
            "uncertain regions and low-confidence samples were left unlabelled."
        ),
        notes=[
            "The primary paper reports 120 Hz binocular Pupil Labs eye-tracking glasses.",
            "More than 140 minutes of hand-labelled data were reported.",
            "Published classes include fixation, saccade, pursuit, blink, and VOR.",
            "The GazeForge loader infers analysis cadence from LabelData.T for every file.",
            "Secondary processed benchmark metadata has reported a different cadence; do not "
            "replace file-timestamp provenance with that summary value.",
            "Head-mounted naturalistic evidence is complementary to, not equivalent to, GP3 data.",
        ],
    )
