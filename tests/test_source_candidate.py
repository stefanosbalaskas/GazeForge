import json

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.source_candidate import (
    build_candidate_source_inventory,
    validate_candidate_source_inventory,
    write_candidate_source_inventory,
)


def _candidate_tree(tmp_path):
    root = tmp_path / "candidate"
    nested = root / "nested"
    nested.mkdir(parents=True)
    (root / "README.txt").write_text("candidate source\n", encoding="utf-8")
    (nested / "sample.mat").write_bytes(b"gaze-data")
    return root


def test_candidate_inventory_is_exact_portable_and_non_empirical(tmp_path):
    root = _candidate_tree(tmp_path)
    inventory = build_candidate_source_inventory(root, dataset_key="gaze-in-the-wild")

    assert inventory.file_count == 2
    assert [record.path for record in inventory.files] == ["README.txt", "nested/sample.mat"]
    assert len(inventory.inventory_fingerprint_sha256) == 64

    payload = inventory.to_dict()
    assert payload["record_type"] == "candidate-source-inventory-v1"
    assert payload["dataset_key"] == "gaze-in-the-wild"
    assert payload["scientific_boundary"] == {
        "candidate_copy_only": True,
        "source_authority_verified": False,
        "reuse_terms_verified": False,
        "analysis_use_permitted": False,
        "source_audit_ready": False,
        "empirical_evidence_created": False,
    }
    assert set(payload["files"][0]) == {"path", "sha256", "bytes"}

    manifest = tmp_path / "candidate-inventory.json"
    write_candidate_source_inventory(inventory, manifest)
    validated = validate_candidate_source_inventory(manifest, root)
    assert validated.inventory_fingerprint_sha256 == inventory.inventory_fingerprint_sha256
    assert validated.files == inventory.files


def test_candidate_inventory_supports_hollywood_without_inferring_identity(tmp_path):
    root = tmp_path / "hollywood"
    root.mkdir()
    (root / "opaque.arff").write_text("@relation x\n@data\n1\n", encoding="utf-8")

    inventory = build_candidate_source_inventory(root, dataset_key="hollywood2em")

    payload = inventory.to_dict()
    assert payload["dataset_key"] == "hollywood2em"
    assert set(payload["files"][0]) == {"path", "sha256", "bytes"}
    assert "participant_id" not in payload["files"][0]
    assert "trial_id" not in payload["files"][0]
    assert "role" not in payload["files"][0]


def test_candidate_inventory_refuses_unsupported_dataset(tmp_path):
    root = _candidate_tree(tmp_path)
    with pytest.raises(ValueError, match="dataset_key must be one of"):
        build_candidate_source_inventory(root, dataset_key="unreviewed-dataset")


def test_candidate_inventory_refuses_zero_byte_files(tmp_path):
    root = tmp_path / "candidate"
    root.mkdir()
    (root / "empty.mat").write_bytes(b"")

    with pytest.raises(BenchmarkIntegrityError, match="zero-byte"):
        build_candidate_source_inventory(root, dataset_key="gaze-in-the-wild")


def test_candidate_inventory_output_must_not_mutate_source_snapshot(tmp_path):
    root = _candidate_tree(tmp_path)
    inventory = build_candidate_source_inventory(root, dataset_key="gaze-in-the-wild")

    with pytest.raises(BenchmarkIntegrityError, match="outside the inventoried tree"):
        write_candidate_source_inventory(inventory, root / "inventory.json")


def test_candidate_inventory_detects_file_drift(tmp_path):
    root = _candidate_tree(tmp_path)
    inventory = build_candidate_source_inventory(root, dataset_key="gaze-in-the-wild")
    manifest = tmp_path / "candidate-inventory.json"
    write_candidate_source_inventory(inventory, manifest)

    (root / "nested" / "sample.mat").write_bytes(b"changed-gaze-data")

    with pytest.raises(BenchmarkIntegrityError, match="no longer matches"):
        validate_candidate_source_inventory(manifest, root)


def test_candidate_inventory_detects_serialized_fingerprint_tampering(tmp_path):
    root = _candidate_tree(tmp_path)
    inventory = build_candidate_source_inventory(root, dataset_key="hollywood2em")
    manifest = tmp_path / "candidate-inventory.json"
    write_candidate_source_inventory(inventory, manifest)

    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["inventory_fingerprint_sha256"] = "0" * 64
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(BenchmarkIntegrityError, match="fingerprint"):
        validate_candidate_source_inventory(manifest, root)
