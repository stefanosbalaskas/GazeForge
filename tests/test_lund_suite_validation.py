import json

import pytest

from gazeforge.benchmarks import (
    BenchmarkDatasetCard,
    benchmark_fingerprint,
    build_benchmark_report,
)
from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.lund_fetch import (
    LUND2013_COMMIT,
    LUND2013_DATA_PATH,
    LUND2013_REPOSITORY,
)
from gazeforge.lund_suite import validate_lund2013_suite_manifest

_REPORT_NAMES = (
    "annotator_sensitivity_mn_60hz",
    "human_agreement_60hz",
    "human_agreement_native",
    "primary_ra_60hz",
    "sampling_purity_sensitivity_ra",
)


def _write_json(path, payload):
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _child_report(name):
    card = BenchmarkDatasetCard(
        name=f"test-{name}",
        version="1",
        source="test",
        license="test-only",
        task="test",
        sampling_rates_hz=[60.0],
    )
    return build_benchmark_report(
        benchmark=card,
        metrics={"score": 0.5},
        model={"models": [name]},
        protocol={"test": True},
    )


def _make_suite(root):
    records = []
    for name in _REPORT_NAMES:
        report = _child_report(name)
        filename = f"{name}.json"
        _write_json(root / filename, report)
        records.append(
            {
                "name": name,
                "path": filename,
                "report_fingerprint_sha256": report["report_fingerprint_sha256"],
            }
        )
    body = {
        "suite": "lund2013-event-validation-v1",
        "status": "complete",
        "source_manifest": {
            "repository": LUND2013_REPOSITORY,
            "commit": LUND2013_COMMIT,
            "data_path": LUND2013_DATA_PATH,
            "manifest_fingerprint_sha256": "a" * 64,
            "files_verified_at_run": True,
        },
        "protocol": {"target_sampling_rate_hz": 60.0},
        "reports": records,
    }
    manifest = {
        **body,
        "suite_fingerprint_sha256": benchmark_fingerprint(body),
    }
    path = root / "lund2013-suite-manifest.json"
    _write_json(path, manifest)
    return path, manifest


def test_validate_lund_suite_verifies_manifest_and_all_children(tmp_path):
    path, manifest = _make_suite(tmp_path)

    summary = validate_lund2013_suite_manifest(tmp_path)

    assert summary["status"] == "complete"
    assert summary["report_count"] == 5
    assert summary["reports_verified"] is True
    assert summary["suite_fingerprint_sha256"] == manifest[
        "suite_fingerprint_sha256"
    ]
    assert summary["manifest_path"] == str(path)


def test_validate_lund_suite_rejects_modified_manifest(tmp_path):
    path, manifest = _make_suite(tmp_path)
    manifest["protocol"]["target_sampling_rate_hz"] = 75.0
    _write_json(path, manifest)

    with pytest.raises(BenchmarkIntegrityError, match="suite manifest fingerprint mismatch"):
        validate_lund2013_suite_manifest(path)


def test_validate_lund_suite_rejects_modified_child_report(tmp_path):
    _, manifest = _make_suite(tmp_path)
    child_path = tmp_path / manifest["reports"][0]["path"]
    child = json.loads(child_path.read_text(encoding="utf-8"))
    child["metrics"]["score"] = 0.99
    _write_json(child_path, child)

    with pytest.raises(BenchmarkIntegrityError, match="child.*fingerprint mismatch"):
        validate_lund2013_suite_manifest(tmp_path)


def test_validate_lund_suite_manifest_only_skips_child_io(tmp_path):
    _, manifest = _make_suite(tmp_path)
    child_path = tmp_path / manifest["reports"][0]["path"]
    child_path.unlink()

    summary = validate_lund2013_suite_manifest(tmp_path, verify_reports=False)

    assert summary["report_count"] == 5
    assert summary["reports_verified"] is False


def test_validate_lund_suite_rejects_unsafe_report_path_even_with_valid_manifest_hash(
    tmp_path,
):
    path, manifest = _make_suite(tmp_path)
    manifest["reports"][0]["path"] = "../escape.json"
    body = {
        key: value
        for key, value in manifest.items()
        if key != "suite_fingerprint_sha256"
    }
    manifest["suite_fingerprint_sha256"] = benchmark_fingerprint(body)
    _write_json(path, manifest)

    with pytest.raises(BenchmarkIntegrityError, match="unsafe report path"):
        validate_lund2013_suite_manifest(path)
