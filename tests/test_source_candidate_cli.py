import json

from gazeforge.source_candidate_cli import main


def test_candidate_source_cli_build_validate_review_and_review_validate(tmp_path, capsys):
    root = tmp_path / "candidate"
    root.mkdir()
    (root / "sample.arff").write_text("@relation x\n@data\n1\n", encoding="utf-8")
    manifest = tmp_path / "inventory.json"
    review = tmp_path / "review.json"

    assert (
        main(
            [
                "build",
                "--dataset",
                "hollywood2em",
                "--root",
                str(root),
                "--output",
                str(manifest),
            ]
        )
        == 0
    )
    built = json.loads(capsys.readouterr().out)
    assert built["record_type"] == "candidate-source-inventory-v1"
    assert built["dataset_key"] == "hollywood2em"
    assert built["file_count"] == 1
    assert manifest.is_file()

    assert main(["validate", "--inventory", str(manifest), "--root", str(root)]) == 0
    validated = json.loads(capsys.readouterr().out)
    assert validated == built

    assert (
        main(
            [
                "review",
                "--inventory",
                str(manifest),
                "--root",
                str(root),
                "--output",
                str(review),
            ]
        )
        == 0
    )
    scaffold = json.loads(capsys.readouterr().out)
    assert scaffold["record_type"] == "candidate-source-review-scaffold-v1"
    assert scaffold["source_review"]["dataset_status"] == "template"
    assert scaffold["files"][0]["role"] == "unresolved"
    assert review.is_file()

    assert (
        main(
            [
                "review-validate",
                "--review",
                str(review),
                "--inventory",
                str(manifest),
                "--root",
                str(root),
            ]
        )
        == 0
    )
    review_validated = json.loads(capsys.readouterr().out)
    assert review_validated == scaffold


def test_candidate_source_cli_compiles_completed_review_to_template_only(tmp_path, capsys):
    root = tmp_path / "candidate"
    root.mkdir()
    (root / "sample.arff").write_text("@relation x\n@data\n1\n", encoding="utf-8")
    manifest = tmp_path / "inventory.json"
    review = tmp_path / "review.json"
    audit_template = tmp_path / "audit-template.json"

    assert (
        main(
            [
                "build",
                "--dataset",
                "hollywood2em",
                "--root",
                str(root),
                "--output",
                str(manifest),
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert (
        main(
            [
                "review",
                "--inventory",
                str(manifest),
                "--root",
                str(root),
                "--output",
                str(review),
            ]
        )
        == 0
    )
    capsys.readouterr()

    payload = json.loads(review.read_text(encoding="utf-8"))
    payload["source_review"].update(
        {
            "dataset_version": "reviewed-version",
            "authoritative_source": "reviewed source",
            "source_revision": "reviewed revision",
            "license_or_terms": "reviewed terms",
            "reuse_terms_source": "reviewed terms source",
            "source_authority_evidence": "reviewed authority evidence",
            "analysis_use_evidence": "reviewed analysis evidence",
            "redistribution_evidence": "reviewed redistribution evidence",
            "coordinate_unit": "pixels",
            "coordinate_verification_basis": "reviewed coordinate evidence",
            "participant_mapping_basis": "reviewed participant mapping",
            "annotation_columns_review": "reviewed annotation columns",
            "sampling_rate_review": "reviewed sampling-rate evidence",
        }
    )
    payload["files"][0].update(
        {
            "role": "arff",
            "include_in_audit": True,
            "participant_id": "P01",
            "trial_id": "T01",
        }
    )
    review.write_text(json.dumps(payload), encoding="utf-8")

    assert (
        main(
            [
                "audit-template",
                "--review",
                str(review),
                "--inventory",
                str(manifest),
                "--root",
                str(root),
                "--output",
                str(audit_template),
            ]
        )
        == 0
    )
    compiled = json.loads(capsys.readouterr().out)
    assert compiled["dataset_name"] == "Hollywood2EM"
    assert compiled["dataset_status"] == "template"
    assert compiled["reuse_terms_verified"] is False
    assert compiled["analysis_use_permitted"] is False
    assert compiled["coordinate_unit_verified"] is False
    assert compiled["participant_identity_mapping_verified"] is False
    assert compiled["files"][0]["participant_id"] == "P01"
    assert json.loads(audit_template.read_text(encoding="utf-8")) == compiled
