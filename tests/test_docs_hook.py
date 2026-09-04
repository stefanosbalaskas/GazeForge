import json
import shutil
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace

from gazeforge.benchmarks import BenchmarkDatasetCard, build_benchmark_report


def _load_on_pre_build():
    hook_path = Path(__file__).parents[1] / "scripts" / "mkdocs_hooks.py"
    spec = spec_from_file_location("gazeforge_mkdocs_hooks", hook_path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.on_pre_build


def _copy_source_resolution_governance(root: Path) -> None:
    repository_root = Path(__file__).parents[1]
    source_protocols = repository_root / "validation" / "protocols"
    target_protocols = root / "validation" / "protocols"
    target_protocols.mkdir(parents=True, exist_ok=True)
    for source in source_protocols.glob("*-source-resolution-*.json"):
        shutil.copy2(source, target_protocols / source.name)

    source_lock = (
        repository_root
        / "validation"
        / "governance"
        / "source-resolution-bundle-lock-v1.json"
    )
    target_governance = root / "validation" / "governance"
    target_governance.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_lock, target_governance / source_lock.name)


def test_mkdocs_hook_generates_conservative_empty_evidence_page(tmp_path):
    (tmp_path / "validation").mkdir()
    (tmp_path / "docs").mkdir()
    _copy_source_resolution_governance(tmp_path)
    config = SimpleNamespace(config_file_path=str(tmp_path / "mkdocs.yml"))

    _load_on_pre_build()(config)

    page = (tmp_path / "docs" / "frozen-evidence.md").read_text(encoding="utf-8")
    assert "No integrity-checked frozen empirical benchmark reports" in page
    assert "do **not** become empirical validation" in page
    assert "validation-status.md" in page

    source_page = (tmp_path / "docs" / "source-resolution-status.md").read_text(
        encoding="utf-8"
    )
    assert "Non-empirical governance status" in source_page
    assert "## Reviewed governance snapshot" in source_page
    assert "f68ad9d2ff7f" in source_page
    assert "Gaze-in-the-Wild naturalistic eye-head event benchmark" in source_page


def test_mkdocs_hook_renders_details_from_validated_frozen_report(tmp_path):
    validation = tmp_path / "validation"
    validation.mkdir()
    (tmp_path / "docs").mkdir()
    _copy_source_resolution_governance(tmp_path)
    card = BenchmarkDatasetCard(
        name="Hook-test-benchmark",
        version="1",
        source="test",
        license="test-only",
        task="event classification",
        sampling_rates_hz=[60.0],
        validation_scope="external-empirical-benchmark",
        annotation_origin="expert-manual",
        sampling_origin="native",
        reference_strength="expert-human-reference",
    )
    report = build_benchmark_report(
        benchmark=card,
        model={"models": ["RandomForest"]},
        protocol={"n_splits": 5},
        metrics={
            "summary": [
                {
                    "model": "RandomForest",
                    "n_folds": 5,
                    "accuracy_mean": 0.81,
                    "balanced_accuracy_mean": 0.79,
                    "macro_f1_mean": 0.77,
                    "event_f1_mean": 0.68,
                    "event_mean_matched_iou_mean": 0.72,
                    "multiclass_brier_score_mean": 0.21,
                    "expected_calibration_error_mean": 0.07,
                }
            ]
        },
    )
    (validation / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    config = SimpleNamespace(config_file_path=str(tmp_path / "mkdocs.yml"))

    _load_on_pre_build()(config)

    page = (tmp_path / "docs" / "frozen-evidence.md").read_text(encoding="utf-8")
    assert "## Validated report details" in page
    assert "Hook-test-benchmark" in page
    assert "Overall held-out model performance" in page
    assert "RandomForest" in page
    assert "fingerprint-validated JSON" in page
    assert report["report_fingerprint_sha256"][:12] in page
