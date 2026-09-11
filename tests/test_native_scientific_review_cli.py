import argparse
import json
from pathlib import Path

from gazeforge import cli


def _approval() -> dict:
    return {
        "schema": "gazeforge-native-event-scientific-review-v1",
        "status": "approved-for-public-frozen-evidence",
        "decision": "approved",
        "reviewer": "Scientific Reviewer",
        "reviewed_at": "2026-09-11T18:30:00Z",
        "review_scope": "native-event-suite-publication-review",
        "review_rationale": "Reviewed.",
        "lineage": {
            "suite": "native-event-validation-v1",
            "suite_fingerprint_sha256": "a" * 64,
            "report_count": 3,
            "data_file_name": "native.csv",
            "data_file_sha256": "b" * 64,
            "spec_file_name": "native-spec.json",
            "spec_fingerprint_sha256": "c" * 64,
            "reports_verified": True,
        },
        "scientific_boundary": {
            "scientific_review_completed": True,
            "approved_for_public_frozen_evidence": True,
            "cross_device_generalizability_claim_created": False,
            "gp3_general_validity_claim_created": False,
            "human_reference_ground_truth_promoted": False,
            "source_rights_expanded": False,
            "raw_source_redistribution_authorized": False,
            "universal_performance_validity_claim_created": False,
        },
        "review_fingerprint_sha256": "d" * 64,
    }


def test_cli_registers_native_review_publication_commands():
    parser = cli.build_parser()
    subparsers = next(
        action
        for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)
    )
    assert "native-event-review-approve" in subparsers.choices
    assert "native-event-publication-validate" in subparsers.choices


def test_cli_writes_native_review_approval(monkeypatch, tmp_path, capsys):
    review_path = tmp_path / "native-scientific-review.json"
    approval = _approval()
    observed = {}

    def fake_write(path, **kwargs):
        observed["path"] = path
        observed.update(kwargs)
        return review_path

    monkeypatch.setattr(cli, "write_native_scientific_review_approval", fake_write)
    monkeypatch.setattr(
        cli,
        "validate_native_scientific_review_approval",
        lambda path: approval,
    )

    assert (
        cli.main(
            [
                "native-event-review-approve",
                str(tmp_path),
                "--reviewer",
                "Scientific Reviewer",
                "--reviewed-at",
                "2026-09-11T18:30:00Z",
                "--rationale",
                "Reviewed.",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert observed["path"] == Path(tmp_path)
    assert observed["reviewer"] == "Scientific Reviewer"
    assert observed["reviewed_at"] == "2026-09-11T18:30:00Z"
    assert observed["review_rationale"] == "Reviewed."
    assert observed["overwrite"] is False
    assert payload["status"] == "approved-for-public-frozen-evidence"
    assert payload["review_fingerprint_sha256"] == "d" * 64
    assert payload["suite_fingerprint_sha256"] == "a" * 64


def test_cli_validates_native_publication_approval(monkeypatch, tmp_path, capsys):
    approval = _approval()
    monkeypatch.setattr(
        cli,
        "validate_native_scientific_review_approval",
        lambda path: approval,
    )

    assert cli.main(["native-event-publication-validate", str(tmp_path)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == approval
