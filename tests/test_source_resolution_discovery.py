import json
from pathlib import Path

import pytest

from gazeforge import source_resolution_cli, source_resolution_discovery
from gazeforge.exceptions import BenchmarkIntegrityError

_PROTOCOLS = Path("validation/protocols")


def _copy_json(source, target):
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def test_repository_discovery_finds_exact_current_source_resolution_set():
    paths = source_resolution_discovery.discover_source_resolution_paths(_PROTOCOLS)

    assert [path.name for path in paths] == [
        "gaze-in-wild-source-resolution-2026-09-04.json",
        "hollywood2-source-resolution-2026-09-05.json",
        "visus-source-resolution-2026-09-04.json",
    ]

    summary = source_resolution_discovery.validate_source_resolution_directory(_PROTOCOLS)
    assert summary["record_count"] == 3
    records = {record["dataset_key"]: record for record in summary["records"]}
    assert set(records) == {"gaze-in-the-wild", "hollywood2em", "visus"}
    assert records["hollywood2em"]["empirical_evidence_created"] is True


def test_discovery_ignores_other_protocol_json_files(tmp_path):
    source = _PROTOCOLS / "hollywood2-source-resolution-2026-09-05.json"
    _copy_json(source, tmp_path / source.name)
    (tmp_path / "unrelated-protocol.json").write_text("not json", encoding="utf-8")

    paths = source_resolution_discovery.discover_source_resolution_paths(tmp_path)
    assert [path.name for path in paths] == [source.name]


def test_discovery_refuses_empty_candidate_set(tmp_path):
    with pytest.raises(BenchmarkIntegrityError, match="No source-resolution checkpoints"):
        source_resolution_discovery.discover_source_resolution_paths(tmp_path)


def test_discovery_refuses_malformed_matching_candidate(tmp_path):
    path = tmp_path / "broken-source-resolution-2026-09-04.json"
    path.write_text("{broken", encoding="utf-8")

    with pytest.raises(BenchmarkIntegrityError, match="not valid UTF-8 JSON"):
        source_resolution_discovery.discover_source_resolution_paths(tmp_path)


def test_discovery_refuses_non_object_matching_candidate(tmp_path):
    path = tmp_path / "list-source-resolution-2026-09-04.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(BenchmarkIntegrityError, match="must be a JSON object"):
        source_resolution_discovery.discover_source_resolution_paths(tmp_path)


def test_discovery_refuses_wrong_record_type_for_matching_candidate(tmp_path):
    path = tmp_path / "wrong-source-resolution-2026-09-04.json"
    path.write_text(json.dumps({"record_type": "other"}), encoding="utf-8")

    with pytest.raises(BenchmarkIntegrityError, match="record_type"):
        source_resolution_discovery.discover_source_resolution_paths(tmp_path)


def test_directory_validation_rejects_duplicate_dataset_checkpoints(tmp_path):
    source = _PROTOCOLS / "hollywood2-source-resolution-2026-09-05.json"
    _copy_json(source, tmp_path / "hollywood2-source-resolution-2026-09-05.json")
    _copy_json(source, tmp_path / "hollywood2-source-resolution-2026-09-06.json")

    with pytest.raises(BenchmarkIntegrityError, match="duplicate dataset checkpoints"):
        source_resolution_discovery.validate_source_resolution_directory(tmp_path)


def test_directory_mode_cli_emits_complete_repository_bundle(capsys):
    code = source_resolution_cli.main(["--directory", str(_PROTOCOLS)])
    assert code == 0

    output = json.loads(capsys.readouterr().out)
    assert output["record_count"] == 3
    assert output["bundle_fingerprint_sha256"] == (
        "57064fea405e4a2e944bb066dd2dd7bff919ec12fb380d9cc1a8ba67d3bbbc5a"
    )


def test_cli_rejects_directory_and_explicit_paths_together():
    source = _PROTOCOLS / "visus-source-resolution-2026-09-04.json"

    with pytest.raises(SystemExit) as exc:
        source_resolution_cli.main(["--directory", str(_PROTOCOLS), str(source)])
    assert exc.value.code == 2


def test_cli_requires_explicit_paths_or_directory():
    with pytest.raises(SystemExit) as exc:
        source_resolution_cli.main([])
    assert exc.value.code == 2
