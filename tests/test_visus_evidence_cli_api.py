from pathlib import Path

import gazeforge
from gazeforge import visus_cli


def test_visus_frozen_evidence_bundle_is_exposed_from_top_level_api():
    assert gazeforge.VisusFrozenEvidenceBundle.__name__ == "VisusFrozenEvidenceBundle"
    assert callable(gazeforge.load_visus_frozen_evidence_bundle)
    assert callable(gazeforge.validate_visus_frozen_evidence_bundle)
    assert "VisusFrozenEvidenceBundle" in gazeforge.__all__
    assert "load_visus_frozen_evidence_bundle" in gazeforge.__all__
    assert "validate_visus_frozen_evidence_bundle" in gazeforge.__all__


def test_evidence_validate_command_runs_full_bundle_gate(monkeypatch, tmp_path, capsys):
    calls = {}

    def fake_validate(path):
        calls["path"] = path
        return {
            "bundle": "visus-frozen-evidence-v1",
            "status": "verified-bundle",
            "frozen_evidence_eligible_for_scientific_review": True,
            "suite_fingerprint_sha256": "a" * 64,
            "execution_fingerprint_sha256": "b" * 64,
            "report_count": 3,
            "raw_execution_input_count": 4,
            "source": {
                "source_audit_report_fingerprint_sha256": "c" * 64,
                "source_audit_spec_fingerprint_sha256": "d" * 64,
                "source_manifest_fingerprint_sha256": "e" * 64,
            },
            "protocol": {"prediction_emission_grid_used": False},
            "claim_limits": ["Integrity eligibility is not empirical validation."],
        }

    monkeypatch.setattr(visus_cli, "validate_visus_frozen_evidence_bundle", fake_validate)
    bundle = tmp_path / "frozen-visus-suite"
    code = visus_cli.main(["evidence-validate", str(bundle)])

    assert code == 0
    assert calls["path"] == Path(bundle)
    output = capsys.readouterr().out
    assert '"status": "verified-bundle"' in output
    assert '"frozen_evidence_eligible_for_scientific_review": true' in output
    assert '"raw_execution_input_count": 4' in output


def test_evidence_validate_parser_offers_no_weaker_validation_mode(tmp_path):
    args = visus_cli.build_parser().parse_args(["evidence-validate", str(tmp_path)])
    assert args.command == "evidence-validate"
    assert args.path == tmp_path
    assert not hasattr(args, "manifest_only")
    assert not hasattr(args, "provenance_only")
