import json

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.source_candidate import (
    build_candidate_source_inventory,
    write_candidate_source_inventory,
)
from gazeforge.source_candidate_review import (
    build_candidate_source_review_scaffold,
    validate_candidate_source_review_scaffold,
    write_candidate_source_review_scaffold,
)


def _candidate(tmp_path, dataset_key):
    root = tmp_path / "candidate"
    nested = root / "nested"
    nested.mkdir(parents=True)
    if dataset_key == "hollywood2em":
        (root / "opaque.arff").write_text("@relation x\n@data\n1\n", encoding="utf-8")
        (nested / "notes.txt").write_text("review me\n", encoding="utf-8")
    else:
        (root / "opaque-1.mat").write_bytes(b"label-ish")
        (nested / "opaque-2.mat").write_bytes(b"process-ish")
    inventory = build_candidate_source_inventory(root, dataset_key=dataset_key)
    inventory_path = tmp_path / "inventory.json"
    write_candidate_source_inventory(inventory, inventory_path)
    return root, inventory, inventory_path


@pytest.mark.parametrize("dataset_key", ["hollywood2em", "gaze-in-the-wild"])
def test_review_scaffold_preserves_exact_identity_without_inference(tmp_path, dataset_key):
    root, inventory, inventory_path = _candidate(tmp_path, dataset_key)
    scaffold = build_candidate_source_review_scaffold(inventory)

    assert scaffold.candidate_file_count == inventory.file_count
    assert scaffold.candidate_inventory_fingerprint_sha256 == (
        inventory.inventory_fingerprint_sha256
    )
    assert all(row.role == "unresolved" for row in scaffold.files)
    assert all(row.include_in_audit is False for row in scaffold.files)
    assert all(row.participant_id is None for row in scaffold.files)
    assert all(row.trial_id is None for row in scaffold.files)
    assert all(row.labeller_id is None for row in scaffold.files)
    assert all(row.process_path is None for row in scaffold.files)

    payload = scaffold.to_dict()
    assert payload["record_type"] == "candidate-source-review-scaffold-v1"
    assert payload["source_review"]["dataset_status"] == "template"
    assert payload["scientific_boundary"] == {
        "candidate_copy_only": True,
        "review_scaffold_only": True,
        "authorizes_source_audit": False,
        "authorizes_empirical_evidence": False,
        "empirical_evidence_created": False,
    }

    review_path = tmp_path / "review.json"
    write_candidate_source_review_scaffold(scaffold, review_path)
    validated = validate_candidate_source_review_scaffold(review_path, inventory_path, root)
    assert validated.files == scaffold.files


def test_review_scaffold_allows_manual_semantic_edits_without_empirical_promotion(tmp_path):
    root, inventory, inventory_path = _candidate(tmp_path, "gaze-in-the-wild")
    scaffold = build_candidate_source_review_scaffold(inventory)
    review_path = tmp_path / "review.json"
    write_candidate_source_review_scaffold(scaffold, review_path)

    payload = json.loads(review_path.read_text(encoding="utf-8"))
    payload["source_review"]["authoritative_source"] = "manually reviewed source"
    payload["source_review"]["coordinate_unit"] = "pixels"
    payload["files"][0].update(
        {
            "role": "label",
            "include_in_audit": True,
            "participant_id": "P01",
            "trial_id": "T01",
            "labeller_id": 1,
            "process_path": "nested/opaque-2.mat",
        }
    )
    payload["files"][1]["role"] = "process"
    payload["files"][1]["include_in_audit"] = True
    review_path.write_text(json.dumps(payload), encoding="utf-8")

    validated = validate_candidate_source_review_scaffold(review_path, inventory_path, root)
    assert validated.files[0].role == "label"
    assert validated.files[0].participant_id == "P01"
    assert validated.source_review["dataset_status"] == "template"


def test_review_scaffold_refuses_empirical_dataset_status(tmp_path):
    root, inventory, inventory_path = _candidate(tmp_path, "hollywood2em")
    scaffold = build_candidate_source_review_scaffold(inventory)
    review_path = tmp_path / "review.json"
    write_candidate_source_review_scaffold(scaffold, review_path)

    payload = json.loads(review_path.read_text(encoding="utf-8"))
    payload["source_review"]["dataset_status"] = "empirical"
    review_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(BenchmarkIntegrityError, match="must remain 'template'"):
        validate_candidate_source_review_scaffold(review_path, inventory_path, root)


def test_review_scaffold_refuses_inventory_identity_tampering(tmp_path):
    root, inventory, inventory_path = _candidate(tmp_path, "hollywood2em")
    scaffold = build_candidate_source_review_scaffold(inventory)
    review_path = tmp_path / "review.json"
    write_candidate_source_review_scaffold(scaffold, review_path)

    payload = json.loads(review_path.read_text(encoding="utf-8"))
    payload["files"][0]["sha256"] = "0" * 64
    review_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(BenchmarkIntegrityError, match="path/hash/size identity"):
        validate_candidate_source_review_scaffold(review_path, inventory_path, root)


def test_review_scaffold_refuses_unsupported_review_role(tmp_path):
    root, inventory, inventory_path = _candidate(tmp_path, "gaze-in-the-wild")
    scaffold = build_candidate_source_review_scaffold(inventory)
    review_path = tmp_path / "review.json"
    write_candidate_source_review_scaffold(scaffold, review_path)

    payload = json.loads(review_path.read_text(encoding="utf-8"))
    payload["files"][0]["role"] = "guessed-label"
    review_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(BenchmarkIntegrityError, match="Unsupported review role"):
        validate_candidate_source_review_scaffold(review_path, inventory_path, root)


def test_review_scaffold_output_must_not_mutate_candidate_tree(tmp_path):
    root, inventory, _ = _candidate(tmp_path, "hollywood2em")
    scaffold = build_candidate_source_review_scaffold(inventory)

    with pytest.raises(BenchmarkIntegrityError, match="outside the candidate source tree"):
        write_candidate_source_review_scaffold(scaffold, root / "review.json")
