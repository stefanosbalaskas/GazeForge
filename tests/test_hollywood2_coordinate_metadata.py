from __future__ import annotations

import json
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.hollywood2_coordinate_metadata import (
    build_hollywood2_coordinate_metadata_probe,
    inspect_hollywood2_arff_header,
    probe_fingerprint,
)


def _write_arff(path: Path, *, comment: str = "% x and y are pixel coordinates") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "% synthetic header for contract testing",
                comment,
                "@relation gaze",
                "@attribute time numeric",
                "@attribute x numeric",
                "@attribute y numeric",
                "@attribute confidence numeric",
                "@attribute handlabeller_1 numeric",
                "@attribute handlabeller_final numeric",
                "@data",
                "SECRET_RAW_ROW_SHOULD_NEVER_BE_READ,123,456,1,1,1",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_header_inspection_stops_before_raw_rows(tmp_path: Path) -> None:
    path = tmp_path / "ground_truth" / "001_clip.arff"
    _write_arff(path)

    record = inspect_hollywood2_arff_header(path)
    text = json.dumps(record, sort_keys=True)

    assert record["data_marker_found"] is True
    assert record["required_gaze_attributes_present"] is True
    assert record["markers"]["pixel_or_px"] is True
    assert record["raw_source_rows_read"] is False
    assert record["raw_source_rows_embedded"] is False
    assert record["source_filename_embedded"] is False
    assert "SECRET_RAW_ROW_SHOULD_NEVER_BE_READ" not in text
    assert "001_clip.arff" not in text


def test_probe_keeps_coordinate_and_scientific_gates_closed(tmp_path: Path) -> None:
    _write_arff(tmp_path / "ground_truth" / "001_clip.arff")
    _write_arff(tmp_path / "ground_truth" / "002_clip.arff")

    record = build_hollywood2_coordinate_metadata_probe(tmp_path)

    assert record["header_inventory"]["arff_file_count"] == 2
    assert record["header_inventory"]["required_gaze_schema_file_count"] == 2
    assert record["header_inventory"]["marker_file_counts"]["pixel_or_px"] == 2
    boundary = record["coordinate_boundary"]
    assert boundary["coordinate_unit_candidate"] == "pixels"
    assert boundary["coordinate_unit_verified"] is False
    assert boundary["coordinate_verification_basis_created"] is False
    assert boundary["pixel_to_visual_angle_conversion_verified"] is False
    assert boundary["unit_sensitive_cross_dataset_modelling_ready"] is False
    scientific = record["scientific_boundary"]
    assert scientific["raw_source_rows_read"] is False
    assert scientific["raw_source_rows_embedded"] is False
    assert scientific["source_filenames_embedded"] is False
    assert scientific["participant_disjoint_validation_created"] is False
    assert scientific["cross_dataset_validation_created"] is False
    assert scientific["new_empirical_performance_claim_created"] is False
    assert record["probe_fingerprint_sha256"] == probe_fingerprint(record)


def test_pixel_header_hint_is_not_coordinate_verification(tmp_path: Path) -> None:
    _write_arff(tmp_path / "ground_truth" / "001_clip.arff")
    record = build_hollywood2_coordinate_metadata_probe(tmp_path)

    assert record["header_inventory"]["marker_file_counts"]["pixel_or_px"] == 1
    assert record["coordinate_boundary"]["coordinate_unit_verified"] is False
    assert record["mapping_boundary"]["participant_identity_mapping_verified"] is False
    assert record["rights_boundary"]["new_rights_permission_created"] is False


def test_missing_data_marker_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "broken.arff"
    path.write_text(
        "@relation broken\n@attribute time numeric\n@attribute x numeric\n",
        encoding="utf-8",
    )

    with pytest.raises(BenchmarkIntegrityError, match="missing an @data marker"):
        inspect_hollywood2_arff_header(path)
