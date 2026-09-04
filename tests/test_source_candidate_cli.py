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


def test_candidate_source_cli_manual_authorization_gate(tmp_path, capsys):
    root = tmp_path / "candidate"
    root.mkdir()
    audit_template = tmp_path / "audit-template.json"
    authorization = tmp_path / "authorization.json"
    empirical_spec = tmp_path / "empirical-spec.json"
    audit_template.write_text(
        json.dumps(
            {
                "dataset_name": "Hollywood2EM",
                "dataset_version": "reviewed-version",
                "source": "reviewed authoritative source",
                "source_revision": "reviewed revision",
                "license": "reviewed terms",
                "reuse_terms_source": "reviewed terms source",
                "dataset_status": "template",
                "coordinate_unit": "pixels",
                "coordinate_verification_basis": "reviewed coordinate basis",
                "participant_identity_mapping_basis": "reviewed participant mapping basis",
                "files": [
                    {
                        "path": "sample.arff",
                        "sha256": "a" * 64,
                        "bytes": 111,
                        "participant_id": "P01",
                        "trial_id": "T01",
                    }
                ],
                "notes": ["compiled template note"],
            }
        ),
        encoding="utf-8",
    )

    assert (
        main(
            [
                "authorization",
                "--dataset",
                "hollywood2em",
                "--template",
                str(audit_template),
                "--root",
                str(root),
                "--output",
                str(authorization),
            ]
        )
        == 0
    )
    pending = json.loads(capsys.readouterr().out)
    assert pending["record_type"] == "candidate-source-audit-authorization-v1"
    assert pending["decision"] == "pending"
    assert pending["scientific_boundary"]["source_audit_executed"] is False
    assert pending["scientific_boundary"]["empirical_evidence_created"] is False

    pending.update(
        {
            "decision": "authorized",
            "reviewer": "independent scientific reviewer",
            "reviewed_at": "2026-09-04",
            "source_authority_verified": True,
            "source_authority_evidence": "authority evidence reviewed",
            "reuse_terms_verified": True,
            "reuse_terms_evidence": "reuse terms reviewed",
            "analysis_use_permitted": True,
            "analysis_use_evidence": "analysis permission reviewed",
            "redistribution_status": "restricted",
            "redistribution_evidence": "redistribution restrictions reviewed",
            "coordinate_unit_verified": True,
            "coordinate_verification_evidence": "coordinate evidence reviewed",
            "participant_mapping_verified": True,
            "participant_mapping_evidence": "participant mapping reviewed",
            "sampling_contract_reviewed": True,
            "sampling_contract_evidence": "sampling contract reviewed",
            "annotation_contract_reviewed": True,
            "annotation_contract_evidence": "annotation contract reviewed",
            "authorization_basis": "all required audit-entry gates reviewed",
        }
    )
    authorization.write_text(json.dumps(pending), encoding="utf-8")

    assert (
        main(
            [
                "authorization-validate",
                "--dataset",
                "hollywood2em",
                "--template",
                str(audit_template),
                "--authorization",
                str(authorization),
            ]
        )
        == 0
    )
    validated = json.loads(capsys.readouterr().out)
    assert validated["decision"] == "authorized"

    assert (
        main(
            [
                "authorization-apply",
                "--dataset",
                "hollywood2em",
                "--template",
                str(audit_template),
                "--authorization",
                str(authorization),
                "--root",
                str(root),
                "--output",
                str(empirical_spec),
            ]
        )
        == 0
    )
    authorized = json.loads(capsys.readouterr().out)
    assert authorized["dataset_status"] == "empirical"
    assert authorized["reuse_terms_verified"] is True
    assert authorized["analysis_use_permitted"] is True
    assert authorized["coordinate_unit_verified"] is True
    assert authorized["participant_identity_mapping_verified"] is True
    assert json.loads(empirical_spec.read_text(encoding="utf-8")) == authorized
