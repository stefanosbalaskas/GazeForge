import json

import pytest

from gazeforge import visus_cli
from gazeforge.exceptions import BenchmarkIntegrityError


def test_evidence_validate_remains_review_eligibility_only(monkeypatch, tmp_path, capsys):
    calls = []

    def fake_eligibility(path):
        calls.append(("eligibility", path))
        return {
            "bundle": "visus-frozen-evidence-v3",
            "frozen_evidence_eligible_for_scientific_review": True,
            "scientific_review_completed": False,
        }

    def forbidden_publication(path):
        raise AssertionError("evidence-validate must not imply publication approval")

    monkeypatch.setattr(visus_cli, "validate_visus_frozen_evidence_bundle", fake_eligibility)
    monkeypatch.setattr(
        visus_cli,
        "validate_visus_scientific_review_approval",
        forbidden_publication,
    )

    code = visus_cli.main(["evidence-validate", str(tmp_path)])

    assert code == 0
    assert calls == [("eligibility", tmp_path)]
    payload = json.loads(capsys.readouterr().out)
    assert payload["frozen_evidence_eligible_for_scientific_review"] is True
    assert payload["scientific_review_completed"] is False


def test_publication_validate_requires_scientific_review_approval(monkeypatch, tmp_path, capsys):
    calls = []

    def fake_publication(path):
        calls.append(path)
        return {
            "schema": "gazeforge-visus-scientific-review-v1",
            "status": "approved-for-public-frozen-evidence",
            "scientific_boundary": {
                "scientific_review_completed": True,
                "approved_for_public_frozen_evidence": True,
                "empirical_performance_claim_created": False,
            },
            "review_fingerprint_sha256": "a" * 64,
        }

    monkeypatch.setattr(
        visus_cli,
        "validate_visus_scientific_review_approval",
        fake_publication,
    )

    code = visus_cli.main(["publication-validate", str(tmp_path)])

    assert code == 0
    assert calls == [tmp_path]
    payload = json.loads(capsys.readouterr().out)
    assert payload["scientific_boundary"]["scientific_review_completed"] is True
    assert payload["scientific_boundary"]["approved_for_public_frozen_evidence"] is True
    assert payload["scientific_boundary"]["empirical_performance_claim_created"] is False


def test_publication_validate_fails_closed_when_review_is_missing(monkeypatch, tmp_path):
    def fail(path):
        raise BenchmarkIntegrityError(
            "VISUS public Frozen Evidence requires visus-scientific-review.json."
        )

    monkeypatch.setattr(visus_cli, "validate_visus_scientific_review_approval", fail)

    with pytest.raises(BenchmarkIntegrityError, match="requires visus-scientific-review.json"):
        visus_cli.main(["publication-validate", str(tmp_path)])


def test_cli_help_distinguishes_eligibility_from_publication():
    help_text = " ".join(visus_cli.build_parser().format_help().split())

    assert "evidence-validate" in help_text
    assert "review eligibility" in help_text
    assert "does not approve public Frozen Evidence publication" in help_text
    assert "publication-validate" in help_text
    assert "review approval required for public Frozen Evidence publication" in help_text
