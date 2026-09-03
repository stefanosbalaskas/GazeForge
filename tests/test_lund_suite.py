import json
from types import SimpleNamespace

import pytest

import gazeforge.lund_suite as lund_suite
from gazeforge.benchmarks import (
    BenchmarkDatasetCard,
    benchmark_fingerprint,
    build_benchmark_report,
)
from gazeforge.exceptions import BenchmarkIntegrityError


def _child_report(name: str) -> dict:
    card = BenchmarkDatasetCard(
        name=name,
        version="test",
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


def _agreement(target_rate):
    return {
        "dataset": "Lund2013",
        "left_annotator": "MN",
        "right_annotator": "RA",
        "sampling_rate_hz": 500.0 if target_rate is None else float(target_rate),
        "overall": {"exact_agreement": 0.8, "cohen_kappa": 0.7},
        "by_stimulus_type": {"image": {"exact_agreement": 0.82}},
        "source_manifest": {"manifest_fingerprint_sha256": "a" * 64},
    }


def _install_fake_analyses(monkeypatch):
    source = {
        "repository": "richardandersson/EyeMovementDetectorEvaluation",
        "commit": "3e12416ab3fd6254c81811cf03f8e5d67c5d7129",
        "data_path": "annotated_data/data used in the article",
        "manifest_fingerprint_sha256": "a" * 64,
        "files_verified_at_run": True,
    }
    monkeypatch.setattr(
        lund_suite,
        "validate_lund2013_source_manifest",
        lambda root: source,
    )
    monkeypatch.setattr(
        lund_suite,
        "compare_lund2013_annotators",
        lambda root, **kwargs: _agreement(kwargs["target_sampling_rate_hz"]),
    )

    def fake_benchmark(root, *, annotator, **kwargs):
        return SimpleNamespace(report=_child_report(f"primary-{annotator}"))

    monkeypatch.setattr(lund_suite, "run_lund2013_event_benchmark", fake_benchmark)
    monkeypatch.setattr(
        lund_suite,
        "run_lund2013_sampling_sensitivity",
        lambda root, **kwargs: SimpleNamespace(
            report=_child_report("sampling-sensitivity")
        ),
    )
    return source


def test_lund_suite_freezes_five_reports_and_complete_manifest(monkeypatch, tmp_path):
    source = _install_fake_analyses(monkeypatch)
    output = tmp_path / "validation"

    run = lund_suite.run_lund2013_benchmark_suite(tmp_path / "lund", output)

    assert set(run.reports) == {
        "human_agreement_native",
        "human_agreement_60hz",
        "primary_ra_60hz",
        "annotator_sensitivity_mn_60hz",
        "sampling_purity_sensitivity_ra",
    }
    assert all(path.is_file() for path in run.report_paths.values())
    assert run.manifest_path.is_file()
    assert run.manifest["status"] == "complete"
    assert run.manifest["source_manifest"] == source
    assert len(run.manifest["reports"]) == 5

    body = {
        key: value
        for key, value in run.manifest.items()
        if key != "suite_fingerprint_sha256"
    }
    assert run.suite_fingerprint_sha256 == benchmark_fingerprint(body)
    on_disk = json.loads(run.manifest_path.read_text(encoding="utf-8"))
    assert on_disk == run.manifest
    fingerprints = {
        item["name"]: item["report_fingerprint_sha256"]
        for item in run.manifest["reports"]
    }
    assert fingerprints == {
        name: report["report_fingerprint_sha256"]
        for name, report in run.reports.items()
    }


def test_lund_suite_preflights_protected_outputs_before_analysis(monkeypatch, tmp_path):
    output = tmp_path / "validation"
    output.mkdir()
    target = output / "lund2013-ra-60hz-primary.json"
    target.write_text("protected", encoding="utf-8")
    monkeypatch.setattr(
        lund_suite,
        "validate_lund2013_source_manifest",
        lambda root: pytest.fail("analysis must not start before output preflight"),
    )

    with pytest.raises(FileExistsError, match="suite output already exists"):
        lund_suite.run_lund2013_benchmark_suite(tmp_path / "lund", output)


def test_lund_suite_analysis_failure_leaves_no_frozen_evidence(monkeypatch, tmp_path):
    output = tmp_path / "validation"
    monkeypatch.setattr(lund_suite, "validate_lund2013_source_manifest", lambda root: None)

    def fail_agreement(root, **kwargs):
        if kwargs["target_sampling_rate_hz"] is not None:
            raise RuntimeError("synthetic analysis failure")
        return _agreement(None)

    monkeypatch.setattr(lund_suite, "compare_lund2013_annotators", fail_agreement)

    with pytest.raises(RuntimeError, match="synthetic analysis failure"):
        lund_suite.run_lund2013_benchmark_suite(tmp_path / "lund", output)

    assert not output.exists()


def test_lund_suite_rejects_child_report_fingerprint_mismatch(monkeypatch, tmp_path):
    _install_fake_analyses(monkeypatch)
    tampered = _child_report("sampling-sensitivity")
    tampered["metrics"]["score"] = 0.9
    monkeypatch.setattr(
        lund_suite,
        "run_lund2013_sampling_sensitivity",
        lambda root, **kwargs: SimpleNamespace(report=tampered),
    )
    output = tmp_path / "validation"

    with pytest.raises(BenchmarkIntegrityError, match="fingerprint mismatch"):
        lund_suite.run_lund2013_benchmark_suite(tmp_path / "lund", output)

    assert not output.exists()


def test_lund_suite_forwards_primary_and_sensitivity_settings(monkeypatch, tmp_path):
    _install_fake_analyses(monkeypatch)
    benchmark_calls = []
    sensitivity_calls = []

    def fake_benchmark(root, *, annotator, **kwargs):
        benchmark_calls.append((annotator, kwargs))
        return SimpleNamespace(report=_child_report(f"primary-{annotator}"))

    def fake_sensitivity(root, **kwargs):
        sensitivity_calls.append(kwargs)
        return SimpleNamespace(report=_child_report("sampling-sensitivity"))

    monkeypatch.setattr(lund_suite, "run_lund2013_event_benchmark", fake_benchmark)
    monkeypatch.setattr(lund_suite, "run_lund2013_sampling_sensitivity", fake_sensitivity)

    lund_suite.run_lund2013_benchmark_suite(
        tmp_path / "lund",
        tmp_path / "validation",
        target_sampling_rate_hz=75.0,
        min_label_purity=0.8,
        n_splits=4,
        n_estimators=25,
        sensitivity_target_rates_hz=(100.0, 75.0),
        sensitivity_min_label_purities=(0.7, 0.8),
    )

    assert [annotator for annotator, _ in benchmark_calls] == ["RA", "MN"]
    for _, kwargs in benchmark_calls:
        assert kwargs["target_sampling_rate_hz"] == 75.0
        assert kwargs["min_label_purity"] == 0.8
        assert kwargs["n_splits"] == 4
        assert kwargs["n_estimators"] == 25
    assert sensitivity_calls[0]["annotator"] == "RA"
    assert sensitivity_calls[0]["target_sampling_rates_hz"] == (100.0, 75.0)
    assert sensitivity_calls[0]["min_label_purities"] == (0.7, 0.8)
