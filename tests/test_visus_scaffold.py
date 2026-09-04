import json

import pytest

from gazeforge import visus_cli
from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.visus_audit import audit_visus_source, load_visus_source_audit_spec
from gazeforge.visus_scaffold import (
    build_visus_source_audit_scaffold,
    write_visus_source_audit_scaffold,
)


def _candidate_tree(root):
    (root / "video").mkdir(parents=True)
    (root / "gaze").mkdir()
    (root / "aoi").mkdir()
    (root / "video" / "S01.avi").write_bytes(b"video-fixture")
    (root / "gaze" / "P01-S01.tsv").write_text("x\ty\n1\t2\n", encoding="utf-8")
    (root / "aoi" / "S01.xml").write_text("<xml>fixture</xml>\n", encoding="utf-8")


def test_scaffold_inventory_is_deterministic_and_never_infers_roles(tmp_path):
    source = tmp_path / "candidate"
    _candidate_tree(source)

    first = build_visus_source_audit_scaffold(source)
    second = build_visus_source_audit_scaffold(source)

    assert first.inventory_fingerprint_sha256 == second.inventory_fingerprint_sha256
    assert len(first.inventory_fingerprint_sha256) == 64
    assert first.file_count == 3
    assert first.spec.dataset_status == "template"
    assert first.spec.reuse_terms_verified is False
    assert first.spec.analysis_use_permitted is False
    assert first.spec.coordinate_unit == "unverified"
    assert first.spec.independent_annotation_streams_verified is False
    assert [record.path for record in first.spec.files] == [
        "aoi/S01.xml",
        "gaze/P01-S01.tsv",
        "video/S01.avi",
    ]
    assert {record.role for record in first.spec.files} == {"other"}
    assert all(record.stimulus_id is None for record in first.spec.files)
    assert all(record.participant_id is None for record in first.spec.files)
    assert all(record.annotation_stream_id is None for record in first.spec.files)


def test_written_scaffold_is_loadable_but_cannot_be_empirical(tmp_path):
    source = tmp_path / "candidate"
    _candidate_tree(source)
    scaffold = build_visus_source_audit_scaffold(source)
    output = tmp_path / "review" / "visus-audit-template.json"

    assert write_visus_source_audit_scaffold(scaffold, output) == output
    loaded = load_visus_source_audit_spec(output)
    assert loaded.dataset_status == "template"
    assert len(loaded.files) == 3
    assert {record.role for record in loaded.files} == {"other"}

    with pytest.raises(BenchmarkIntegrityError, match="templates cannot be promoted"):
        audit_visus_source(source, loaded)


def test_source_mutation_changes_inventory_fingerprint_and_file_digest(tmp_path):
    source = tmp_path / "candidate"
    _candidate_tree(source)
    first = build_visus_source_audit_scaffold(source)
    first_digest = {record.path: record.sha256 for record in first.spec.files}

    (source / "video" / "S01.avi").write_bytes(b"different-video-fixture")
    second = build_visus_source_audit_scaffold(source)
    second_digest = {record.path: record.sha256 for record in second.spec.files}

    assert first.inventory_fingerprint_sha256 != second.inventory_fingerprint_sha256
    assert first_digest["video/S01.avi"] != second_digest["video/S01.avi"]


def test_scaffold_rejects_empty_and_zero_byte_candidate_trees(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(ValueError, match="at least one regular file"):
        build_visus_source_audit_scaffold(empty)

    zero = tmp_path / "zero"
    zero.mkdir()
    (zero / "empty.dat").write_bytes(b"")
    with pytest.raises(BenchmarkIntegrityError, match="zero-byte"):
        build_visus_source_audit_scaffold(zero)


def test_scaffold_rejects_symlinks_when_supported(tmp_path):
    source = tmp_path / "candidate"
    source.mkdir()
    target = tmp_path / "outside.dat"
    target.write_bytes(b"outside")
    link = source / "external.dat"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are unavailable on this platform")

    with pytest.raises(BenchmarkIntegrityError, match="symbolic links"):
        build_visus_source_audit_scaffold(source)


def test_scaffold_writer_refuses_output_inside_snapshot_and_overwrite(tmp_path):
    source = tmp_path / "candidate"
    _candidate_tree(source)
    scaffold = build_visus_source_audit_scaffold(source)

    with pytest.raises(BenchmarkIntegrityError, match="outside the inventoried source tree"):
        write_visus_source_audit_scaffold(scaffold, source / "audit-template.json")

    output = tmp_path / "audit-template.json"
    write_visus_source_audit_scaffold(scaffold, output)
    original = json.loads(output.read_text(encoding="utf-8"))
    assert original["dataset_status"] == "template"

    with pytest.raises(FileExistsError):
        write_visus_source_audit_scaffold(scaffold, output)

    write_visus_source_audit_scaffold(scaffold, output, overwrite=True)
    assert json.loads(output.read_text(encoding="utf-8")) == original


def test_scaffold_cli_writes_only_template_inventory(tmp_path, capsys):
    source = tmp_path / "candidate"
    _candidate_tree(source)
    output = tmp_path / "review" / "visus-template.json"

    code = visus_cli.main(["scaffold", str(source), str(output)])

    assert code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["dataset_status"] == "template"
    assert {row["role"] for row in payload["files"]} == {"other"}
    assert all(row["stimulus_id"] is None for row in payload["files"])
    message = capsys.readouterr().out
    assert '"roles_inferred": false' in message
    assert '"scientific_identities_inferred": false' in message
    assert '"empirical_evidence_created": false' in message
    assert '"inventory_fingerprint_sha256": "' in message
