import json

import pytest

from gazeforge.benchmarks import (
    BenchmarkDatasetCard,
    benchmark_fingerprint,
    build_benchmark_report,
)
from gazeforge.dashboard import (
    build_benchmark_dashboard,
    render_benchmark_dashboard_markdown,
)
from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.lund_fetch import (
    LUND2013_COMMIT,
    LUND2013_DATA_PATH,
    LUND2013_REPOSITORY,
)

_REPORT_NAMES = (
    "annotator_sensitivity_mn_60hz",
    "human_agreement_60hz",
    "human_agreement_native",
    "primary_ra_60hz",
    "sampling_purity_sensitivity_ra",
)


def _write(path, payload):
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _install_suite(root):
    records = []
    for index, name in enumerate(_REPORT_NAMES):
        card = BenchmarkDatasetCard(
            name=f"Lund-test-{name}",
            version="1",
            source=LUND2013_REPOSITORY,
            license="test-only",
            task="test",
            sampling_rates_hz=[60.0],
            validation_scope="external-empirical-benchmark",
            annotation_origin="expert-manual",
            sampling_origin="resampled",
            reference_strength="derived-human-reference",
            human_annotator_count=2,
        )
        report = build_benchmark_report(
            benchmark=card,
            metrics={"score": index / 10},
            model={"models": [name]},
            protocol={"index": index},
        )
        filename = f"{name}.json"
        _write(root / filename, report)
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
            "manifest_fingerprint_sha256": "f" * 64,
            "files_verified_at_run": True,
        },
        "protocol": {"target_sampling_rate_hz": 60.0},
        "reports": records,
    }
    manifest = {
        **body,
        "suite_fingerprint_sha256": benchmark_fingerprint(body),
    }
    manifest_path = root / "lund2013-suite-manifest.json"
    _write(manifest_path, manifest)
    return manifest_path, manifest


def test_dashboard_surfaces_verified_suite_separately_from_reports(tmp_path):
    _, manifest = _install_suite(tmp_path)

    dashboard = build_benchmark_dashboard(tmp_path)

    assert len(dashboard.reports) == 5
    assert len(dashboard.suites) == 1
    assert len(dashboard.suite_table) == 1
    row = dashboard.suite_table.iloc[0]
    assert row["status"] == "complete"
    assert row["report_count"] == 5
    assert row["target_sampling_rate_hz"] == "60"
    assert row["suite_fingerprint_sha256"] == manifest[
        "suite_fingerprint_sha256"
    ]

    markdown = render_benchmark_dashboard_markdown(dashboard)
    assert "## Verified report suites" in markdown
    assert "## Frozen reports" in markdown
    assert manifest["suite_fingerprint_sha256"][:12] in markdown
    assert manifest["suite_fingerprint_sha256"] not in markdown


def test_dashboard_fails_when_suite_manifest_is_tampered(tmp_path):
    manifest_path, manifest = _install_suite(tmp_path)
    manifest["status"] = "incomplete"
    _write(manifest_path, manifest)

    with pytest.raises(BenchmarkIntegrityError):
        build_benchmark_dashboard(tmp_path)
