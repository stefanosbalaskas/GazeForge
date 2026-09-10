from pathlib import Path

import pytest

from gazeforge import visus_authority_cli
from gazeforge import visus_cli as legacy
from gazeforge.visus_authority_execution_strict import (
    build_visus_authority_execution_provenance,
    validate_visus_authority_execution_provenance,
)


def test_authority_cli_rejects_empirical_command_without_certificate():
    with pytest.raises(SystemExit, match="require --authority-certificate"):
        visus_authority_cli.main(["audit", "/tmp/source", "/tmp/spec.json"])


def test_authority_cli_strips_certificate_option_and_patches_empirical_runtime(monkeypatch):
    observed = {}
    original_load = legacy._load_audit
    original_build = legacy.build_visus_execution_provenance
    original_validate = legacy.validate_visus_execution_provenance

    def fake_main(argv):
        observed["argv"] = list(argv)
        observed["load_is_patched"] = legacy._load_audit is not original_load
        observed["build_is_v2"] = (
            legacy.build_visus_execution_provenance
            is build_visus_authority_execution_provenance
        )
        observed["validate_is_v2"] = (
            legacy.validate_visus_execution_provenance
            is validate_visus_authority_execution_provenance
        )
        return 0

    monkeypatch.setattr(legacy, "main", fake_main)
    result = visus_authority_cli.main(
        [
            "suite",
            "/tmp/source",
            "/tmp/spec.json",
            "/tmp/human.csv",
            "/tmp/model.csv",
            "/tmp/grid.json",
            "/tmp/output",
            "--authority-certificate",
            "/tmp/certificate.json",
        ]
    )

    assert result == 0
    assert observed["argv"] == [
        "suite",
        "/tmp/source",
        "/tmp/spec.json",
        "/tmp/human.csv",
        "/tmp/model.csv",
        "/tmp/grid.json",
        "/tmp/output",
    ]
    assert observed["load_is_patched"] is True
    assert observed["build_is_v2"] is True
    assert observed["validate_is_v2"] is True
    assert legacy._load_audit is original_load
    assert legacy.build_visus_execution_provenance is original_build
    assert legacy.validate_visus_execution_provenance is original_validate


def test_authority_cli_accepts_equals_form(monkeypatch):
    observed = {}

    def fake_main(argv):
        observed["argv"] = list(argv)
        return 0

    monkeypatch.setattr(legacy, "main", fake_main)
    result = visus_authority_cli.main(
        [
            "audit",
            "/tmp/source",
            "/tmp/spec.json",
            "--authority-certificate=/tmp/certificate.json",
        ]
    )
    assert result == 0
    assert observed["argv"] == ["audit", "/tmp/source", "/tmp/spec.json"]


def test_authority_cli_validation_commands_do_not_require_live_certificate(monkeypatch):
    observed = {}

    def fake_main(argv):
        observed["argv"] = list(argv)
        observed["validator_is_v2"] = (
            legacy.validate_visus_execution_provenance
            is validate_visus_authority_execution_provenance
        )
        return 0

    monkeypatch.setattr(legacy, "main", fake_main)
    result = visus_authority_cli.main(["execution-validate", "/tmp/suite"])

    assert result == 0
    assert observed["argv"] == ["execution-validate", "/tmp/suite"]
    assert observed["validator_is_v2"] is True


def test_authority_cli_empirical_help_remains_available_without_certificate(monkeypatch, capsys):
    monkeypatch.setattr(legacy, "main", lambda argv: 0)
    result = visus_authority_cli.main(["suite", "--help"])

    assert result == 0
    assert "Authority requirement" in capsys.readouterr().out


def test_authority_cli_rejects_duplicate_certificate_options():
    with pytest.raises(SystemExit, match="exactly once"):
        visus_authority_cli.main(
            [
                "audit",
                "/tmp/source",
                "/tmp/spec.json",
                "--authority-certificate",
                "/tmp/a.json",
                "--authority-certificate",
                "/tmp/b.json",
            ]
        )


def test_console_entrypoint_points_to_authority_wrapper():
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    assert 'gazeforge-visus = "gazeforge.visus_authority_cli:main"' in pyproject
