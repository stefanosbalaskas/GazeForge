import numpy as np
import pytest
from scipy.io import savemat

from gazeforge import (
    BenchmarkDatasetCard,
    hollywood2_manual_event_card,
    prepare_lund2013_benchmark,
    visus_dynamic_aoi_card,
)


def test_algorithmic_reference_cannot_claim_human_validation():
    with pytest.raises(ValueError, match="Algorithm-generated"):
        BenchmarkDatasetCard(
            name="bad-reference",
            version="1",
            source="test",
            license="test",
            task="events",
            annotation_origin="vendor-algorithm",
            sampling_origin="native",
            reference_strength="expert-human-reference",
        )


def test_synthetic_sampling_cannot_claim_empirical_human_reference():
    with pytest.raises(ValueError, match="Synthetic sampling"):
        BenchmarkDatasetCard(
            name="bad-synthetic",
            version="1",
            source="generated",
            license="test",
            task="events",
            annotation_origin="synthetic",
            sampling_origin="synthetic",
            reference_strength="human-reference",
        )


def test_native_and_derived_human_reference_flags_are_distinct():
    native = BenchmarkDatasetCard(
        name="native",
        version="1",
        source="test",
        license="test",
        task="events",
        annotation_origin="expert-manual",
        sampling_origin="native",
        reference_strength="expert-human-reference",
        human_annotator_count=2,
    )
    derived = BenchmarkDatasetCard(
        name="derived",
        version="1",
        source="test",
        license="test",
        task="events",
        annotation_origin="expert-manual",
        sampling_origin="resampled",
        reference_strength="derived-human-reference",
    )
    assert native.is_native_human_reference
    assert derived.is_human_reference
    assert not derived.is_native_human_reference


def test_visus_catalog_card_is_native_60hz_human_aoi_reference():
    card = visus_dynamic_aoi_card()
    assert card.sampling_rates_hz == [60.0]
    assert card.sampling_origin == "native"
    assert card.annotation_origin == "human-manual"
    assert card.reference_strength == "human-reference"
    assert card.human_annotator_count == 2
    assert card.is_native_human_reference


def test_hollywood2_catalog_card_is_native_500hz_expert_reference():
    card = hollywood2_manual_event_card()
    assert card.sampling_rates_hz == [500.0]
    assert card.sampling_origin == "native"
    assert card.annotation_origin == "human-assisted"
    assert card.reference_strength == "expert-human-reference"
    assert card.is_native_human_reference


def _write_lund_recording(path, phase: float) -> None:
    n = 240
    pos = np.zeros((n, 6), dtype=float)
    t = np.arange(n, dtype=float)
    pos[:, 3] = 500 + 0.3 * t + phase
    pos[:, 4] = 300 + 5 * np.sin(t / 12 + phase)
    pos[:, 5] = np.where(np.arange(n) % 120 < 80, 1, 2)
    savemat(
        path,
        {
            "ETdata": {
                "pos": pos,
                "sampFreq": np.array([[500.0]]),
                "screenRes": np.array([[1920.0, 1080.0]]),
                "screenDim": np.array([[530.0, 300.0]]),
                "viewDist": np.array([[650.0]]),
            }
        },
    )


def test_lund_60hz_card_is_derived_human_reference(tmp_path):
    image_dir = tmp_path / "img"
    image_dir.mkdir()
    _write_lund_recording(image_dir / "P01_img_scene_labelled_RA.mat", 0.0)
    _write_lund_recording(image_dir / "P02_img_scene_labelled_RA.mat", 1.0)
    prepared = prepare_lund2013_benchmark(
        tmp_path,
        annotator="RA",
        target_sampling_rate_hz=60.0,
        min_label_purity=0.75,
    )
    card = prepared.dataset_card
    assert card.annotation_origin == "expert-manual"
    assert card.sampling_origin == "resampled"
    assert card.reference_strength == "derived-human-reference"
    assert card.is_human_reference
    assert not card.is_native_human_reference
