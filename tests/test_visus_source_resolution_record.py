import json
from pathlib import Path


_RECORD = Path("validation/protocols/visus-source-resolution-2026-09-04.json")


def _load_record():
    return json.loads(_RECORD.read_text(encoding="utf-8"))


def test_visus_source_resolution_checkpoint_remains_non_empirical():
    record = _load_record()

    assert record["record_type"] == "source-resolution-status-v1"
    assert record["dataset"] == "VISUS dynamic-video eye-tracking benchmark"
    assert record["status"] == "current_authoritative_distribution_unresolved"
    assert record["empirical_evidence_created"] is False
    assert record["source_audit_ready"] is False
    assert record["current_authoritative_download_found"] is False


def test_visus_source_resolution_does_not_infer_dataset_rights_from_publication():
    record = _load_record()
    rights = record["rights"]

    assert rights["analysis_use_terms_status"] == "unresolved"
    assert rights["raw_data_redistribution_terms_status"] == "unresolved"
    assert rights["paper_copyright_notice_is_dataset_license"] is False
    assert rights["license_inference_permitted"] is False


def test_visus_source_resolution_preserves_annotation_independence_gate():
    record = _load_record()
    annotation = record["annotation_independence"]

    assert annotation["published_contributor_count"] == 2
    assert annotation["status"] == "not_established"
    assert annotation["independent_annotation_streams_verified"] is False
    assert annotation["human_human_agreement_ready"] is False


def test_visus_source_resolution_preserves_both_historical_endpoints():
    record = _load_record()

    assert record["authoritative_publication"]["original_distribution_url"] == (
        "http://go.visus.uni-stuttgart.de/eyetrackingBenchmark"
    )
    historical = record["historical_distribution_evidence"]
    assert len(historical) == 1
    assert historical[0]["reported_distribution_url"] == (
        "https://www.visus.uni-stuttgart.de/publikationen/benchmark-eyetracking"
    )
    assert historical[0]["reported_access_date"] == "2021-04-12"
