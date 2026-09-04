import json
from pathlib import Path

import pytest
from gazeforge import visus_source_resolution, visus_source_resolution_cli
from gazeforge.exceptions import BenchmarkIntegrityError


_RECORD = Path("validation/protocols/visus-source-resolution-2026-09-04.json")


def _payload():
    return json.loads(_RECORD.read_text(encoding="utf-8"))


def _write(tmp_path, payload):
    path = tmp_path / "status.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_repository_checkpoint_validates_and_stays_non_empirical():
    summary = visus_source_resolution.validate_visus_source_resolution_record(_RECORD)

    assert summary["status"] == "current_authoritative_distribution_unresolved"
    assert summary["current_authoritative_download_found"] is False
    assert summary["source_audit_ready"] is False
    assert summary["empirical_evidence_created"] is False
    assert summary["rights"]["analysis_use_terms_status"] == "unresolved"
    assert summary["rights"]["raw_data_redistribution_terms_status"] == "unresolved"
    assert (
        summary["annotation_independence"]["independent_annotation_streams_verified"] is False
    )
    assert summary["annotation_independence"]["human_human_agreement_ready"] is False
    assert len(summary["record_fingerprint_sha256"]) == 64

    typed = visus_source_resolution.load_visus_source_resolution_record(_RECORD)
    assert typed.status == summary["status"]
    assert typed.record_fingerprint_sha256 == summary["record_fingerprint_sha256"]
    assert typed.empirical_evidence_created is False


def test_unresolved_checkpoint_cannot_be_promoted_to_audit_ready(tmp_path):
    payload = _payload()
    payload["source_audit_ready"] = True

    with pytest.raises(BenchmarkIntegrityError, match="unresolved VISUS distribution"):
        visus_source_resolution.validate_visus_source_resolution_record(_write(tmp_path, payload))


def test_publication_copyright_cannot_be_promoted_to_dataset_license(tmp_path):
    payload = _payload()
    payload["rights"]["paper_copyright_notice_is_dataset_license"] = True

    with pytest.raises(BenchmarkIntegrityError, match="copyright notice"):
        visus_source_resolution.validate_visus_source_resolution_record(_write(tmp_path, payload))


def test_human_agreement_requires_verified_independent_streams(tmp_path):
    payload = _payload()
    payload["annotation_independence"]["human_human_agreement_ready"] = True

    with pytest.raises(BenchmarkIntegrityError, match="verified independent streams"):
        visus_source_resolution.validate_visus_source_resolution_record(_write(tmp_path, payload))


def test_stored_fingerprint_is_verified_when_present(tmp_path):
    payload = _payload()
    payload["record_fingerprint_sha256"] = "0" * 64

    with pytest.raises(BenchmarkIntegrityError, match="does not match"):
        visus_source_resolution.validate_visus_source_resolution_record(_write(tmp_path, payload))


def test_source_resolution_cli_emits_json_summary(capsys):
    code = visus_source_resolution_cli.main([str(_RECORD)])
    assert code == 0

    output = json.loads(capsys.readouterr().out)
    assert output["record_type"] == "source-resolution-status-v1"
    assert output["status"] == "current_authoritative_distribution_unresolved"
    assert output["source_audit_ready"] is False
    assert output["empirical_evidence_created"] is False
