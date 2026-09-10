from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from gazeforge.visus_scaffold import build_visus_source_audit_scaffold

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "inspect_visus_authoritative_source.py"
)
SOURCE_RECORD_TYPE = "visus-authoritative-source-manifest-v1"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def test_visus_authority_cli_candidate_review_certificate(tmp_path: Path) -> None:
    root = tmp_path / "candidate-visus"
    root.mkdir()
    (root / "asset.dat").write_bytes(b"synthetic candidate asset\n")

    source = tmp_path / "source-package.bin"
    source_bytes = b"synthetic source package\n"
    source.write_bytes(source_bytes)
    rights = tmp_path / "rights.txt"
    rights_bytes = b"synthetic rights evidence\n"
    rights.write_bytes(rights_bytes)

    scaffold = build_visus_source_audit_scaffold(root)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "record_type": SOURCE_RECORD_TYPE,
                "source_reference": "synthetic-cli://visus-source",
                "source_revision": "cli-test-revision",
                "source_authority_claim": "author_hosted_distribution",
                "source_artifact_sha256": hashlib.sha256(source_bytes).hexdigest(),
                "rights_evidence_reference": "synthetic-cli://visus-rights",
                "rights_evidence_sha256": hashlib.sha256(rights_bytes).hexdigest(),
                "inventory_fingerprint_sha256": scaffold.inventory_fingerprint_sha256,
                "file_count": scaffold.file_count,
                "obtained_via_authorized_channel_affirmed": True,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    candidate = tmp_path / "candidate.json"
    result = _run(
        "candidate",
        str(root),
        str(source),
        str(rights),
        str(manifest),
        "--output",
        str(candidate),
    )
    assert '"source_authority_verified": false' in result.stdout
    assert '"source_audit_stage_authorized": false' in result.stdout
    assert "synthetic rights evidence" not in result.stdout

    review = tmp_path / "review.json"
    _run("review-template", str(candidate), "--output", str(review))
    payload = json.loads(review.read_text(encoding="utf-8"))
    payload.update(
        {
            "decision": "approved",
            "reviewer": "Synthetic CLI Reviewer",
            "reviewed_at": "2026-09-10T13:00:00+03:00",
            "source_authority_verified": True,
            "source_authority_evidence": "Synthetic CLI authority evidence.",
            "current_authoritative_distribution_identity_verified": True,
            "current_distribution_identity_evidence": "Synthetic CLI identity evidence.",
            "source_artifact_matches_authoritative_distribution_verified": True,
            "source_artifact_match_evidence": "Synthetic CLI package evidence.",
            "extracted_tree_matches_source_artifact_verified": True,
            "extracted_tree_match_evidence": "Synthetic CLI extraction evidence.",
            "rights_evidence_authoritative_verified": True,
            "rights_evidence_authority_evidence": "Synthetic CLI rights authority evidence.",
            "analysis_use_permitted_verified": True,
            "analysis_use_evidence": "Synthetic CLI analysis evidence.",
            "redistribution_status_verified": "not_stated",
            "redistribution_evidence": "Synthetic CLI redistribution evidence.",
            "license_or_terms_identifier": "Synthetic CLI Terms",
            "rights_scope_limited_to_reviewed_source": True,
        }
    )
    review.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    sealed = tmp_path / "review-sealed.json"
    _run("seal-review", str(review), "--output", str(sealed))

    certificate = tmp_path / "certificate.json"
    result = _run(
        "certificate",
        str(root),
        str(source),
        str(rights),
        str(manifest),
        str(candidate),
        str(sealed),
        "--output",
        str(certificate),
    )
    assert '"source_audit_stage_authorized": true' in result.stdout
    assert '"analysis_use_permitted": true' in result.stdout
    assert '"model_human_validation_created": false' in result.stdout
    assert "synthetic rights evidence" not in result.stdout

    certified = json.loads(certificate.read_text(encoding="utf-8"))
    assert certified["record_type"] == "visus-authoritative-source-certificate-v1"
    assert certified["rights"]["redistribution_status"] == "not_stated"
    assert certified["scientific_boundary"]["model_human_validation_created"] is False
