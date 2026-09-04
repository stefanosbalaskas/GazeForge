import json
from pathlib import Path

import pytest

from gazeforge import source_resolution, source_resolution_cli, visus_source_resolution
from gazeforge.exceptions import BenchmarkIntegrityError

_VISUS = Path("validation/protocols/visus-source-resolution-2026-09-04.json")
_HOLLYWOOD2 = Path("validation/protocols/hollywood2-source-resolution-2026-09-04.json")
_GAZE_IN_WILD = Path("validation/protocols/gaze-in-wild-source-resolution-2026-09-04.json")


def _payload(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write(tmp_path, payload, name="status.json"):
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_repository_source_resolution_bundle_validates_all_three_checkpoints():
    summary = source_resolution.validate_source_resolution_records(
        [_VISUS, _HOLLYWOOD2, _GAZE_IN_WILD]
    )

    assert summary["bundle_type"] == "source-resolution-validation-bundle-v1"
    assert summary["record_count"] == 3
    assert len(summary["bundle_fingerprint_sha256"]) == 64
    assert {record["dataset_key"] for record in summary["records"]} == {
        "visus",
        "hollywood2em",
        "gaze-in-the-wild",
    }
    assert all(record["source_audit_ready"] is False for record in summary["records"])
    assert all(record["empirical_evidence_created"] is False for record in summary["records"])


def test_unified_visus_dispatch_preserves_existing_validator_fingerprint():
    unified = source_resolution.validate_source_resolution_record(_VISUS)
    existing = visus_source_resolution.validate_visus_source_resolution_record(_VISUS)

    assert unified["dataset_key"] == "visus"
    assert unified["status"] == existing["status"]
    assert unified["record_fingerprint_sha256"] == existing["record_fingerprint_sha256"]


def test_hollywood2_sequential_annotation_cannot_be_promoted_to_independent(tmp_path):
    payload = _payload(_HOLLYWOOD2)
    payload["annotation_provenance"]["independent_human_annotation_streams_verified"] = True

    with pytest.raises(BenchmarkIntegrityError, match="independent annotations"):
        source_resolution.validate_source_resolution_record(_write(tmp_path, payload))


def test_hollywood2_article_license_cannot_be_promoted_to_dataset_license(tmp_path):
    payload = _payload(_HOLLYWOOD2)
    payload["rights"]["article_cc_by_is_dataset_license"] = True

    with pytest.raises(BenchmarkIntegrityError, match="dataset license"):
        source_resolution.validate_source_resolution_record(_write(tmp_path, payload))


def test_gaze_in_wild_published_independence_does_not_make_agreement_ready(tmp_path):
    payload = _payload(_GAZE_IN_WILD)
    payload["annotation_provenance"]["human_human_agreement_execution_ready"] = True

    with pytest.raises(BenchmarkIntegrityError, match="agreement must remain blocked"):
        source_resolution.validate_source_resolution_record(_write(tmp_path, payload))


def test_gaze_in_wild_rate_discrepancy_cannot_be_silently_reconciled(tmp_path):
    payload = _payload(_GAZE_IN_WILD)
    payload["sampling_rate_provenance"]["rates_reconciled"] = True

    with pytest.raises(BenchmarkIntegrityError, match="cannot be silently reconciled"):
        source_resolution.validate_source_resolution_record(_write(tmp_path, payload))


def test_current_source_resolution_status_cannot_be_promoted_to_empirical(tmp_path):
    payload = _payload(_HOLLYWOOD2)
    payload["empirical_evidence_created"] = True

    with pytest.raises(BenchmarkIntegrityError, match="non-empirical checkpoints"):
        source_resolution.validate_source_resolution_record(_write(tmp_path, payload))


def test_unknown_dataset_requires_a_reviewed_validator(tmp_path):
    payload = _payload(_HOLLYWOOD2)
    payload["dataset"] = "Unreviewed benchmark"

    with pytest.raises(BenchmarkIntegrityError, match="reviewed validator"):
        source_resolution.validate_source_resolution_record(_write(tmp_path, payload))


def test_validation_bundle_rejects_duplicate_dataset_checkpoints():
    with pytest.raises(BenchmarkIntegrityError, match="duplicate dataset checkpoints"):
        source_resolution.validate_source_resolution_records([_HOLLYWOOD2, _HOLLYWOOD2])


def test_typed_source_resolution_record_exposes_common_governance_state():
    record = source_resolution.load_source_resolution_record(_GAZE_IN_WILD)

    assert record.dataset_key == "gaze-in-the-wild"
    assert record.source_audit_ready is False
    assert record.empirical_evidence_created is False
    assert record.analysis_use_terms_status == "unresolved"
    assert record.raw_data_redistribution_terms_status == "unresolved"
    assert len(record.record_fingerprint_sha256) == 64


def test_unified_source_resolution_cli_emits_json_bundle(capsys):
    code = source_resolution_cli.main([str(_VISUS), str(_HOLLYWOOD2), str(_GAZE_IN_WILD)])
    assert code == 0

    output = json.loads(capsys.readouterr().out)
    assert output["bundle_type"] == "source-resolution-validation-bundle-v1"
    assert output["record_count"] == 3
    assert len(output["bundle_fingerprint_sha256"]) == 64
