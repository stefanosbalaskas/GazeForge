from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "inspect_hollywood2_explicit_crosswalk.py"
)
SOURCE_RECORD_TYPE = "hollywood2-explicit-crosswalk-source-v1"
GIN_TOKENS = (
    "001",
    "002",
    "003",
    "004",
    "005",
    "006",
    "008",
    "010",
    "011",
    "012",
    "013",
    "014",
    "015",
    "017",
    "018",
    "019",
)


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def test_crosswalk_cli_candidate_review_and_certificate(tmp_path: Path) -> None:
    source = tmp_path / "authoritative-ledger.txt"
    source_bytes = b"Synthetic explicit crosswalk source used only for CLI testing.\n"
    source.write_bytes(source_bytes)

    entries = [
        {
            "gin_token": token,
            "original_subject_id": f"CLI-S{index + 1:02d}",
            "task_group": "active" if index < 12 else "free_viewing",
        }
        for index, token in enumerate(GIN_TOKENS)
    ]
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "record_type": SOURCE_RECORD_TYPE,
                "source_reference": "synthetic-cli-test://authoritative-ledger",
                "source_authority_claim": "author_statement",
                "source_file_sha256": hashlib.sha256(source_bytes).hexdigest(),
                "obtained_via_authorized_channel_affirmed": True,
                "mapping_entries": entries,
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
        str(source),
        str(manifest),
        "--output",
        str(candidate),
    )
    assert "CLI-S01" not in result.stdout
    assert "free_viewing" not in result.stdout

    review = tmp_path / "review.json"
    _run("review-template", str(candidate), "--output", str(review))
    review_payload = json.loads(review.read_text(encoding="utf-8"))
    review_payload.update(
        {
            "decision": "approved",
            "reviewer": "Synthetic CLI Reviewer",
            "reviewed_at": "2026-09-10T12:00:00+03:00",
            "source_authority_verified": True,
            "source_authority_evidence": "Synthetic CLI authority evidence.",
            "mapping_explicit_in_source_verified": True,
            "mapping_explicitness_evidence": "Synthetic CLI explicitness evidence.",
            "mapping_transcription_verified": True,
            "mapping_transcription_evidence": "Synthetic CLI transcription evidence.",
            "task_group_semantics_verified": True,
            "task_group_semantics_evidence": "Synthetic CLI group-semantics evidence.",
            "source_version_scope_verified": True,
            "source_version_scope_evidence": "Synthetic CLI version-scope evidence.",
            "rights_scope_promoted": False,
            "empirical_validation_created": False,
        }
    )
    review.write_text(
        json.dumps(review_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    sealed = tmp_path / "review-sealed.json"
    _run("seal-review", str(review), "--output", str(sealed))

    certificate = tmp_path / "certificate.json"
    result = _run(
        "certificate",
        str(source),
        str(manifest),
        str(candidate),
        str(sealed),
        "--output",
        str(certificate),
    )
    assert "CLI-S01" not in result.stdout
    assert "free_viewing" not in result.stdout

    validated = json.loads(certificate.read_text(encoding="utf-8"))
    assert validated["record_type"] == "hollywood2-explicit-crosswalk-certificate-v1"
    assert validated["token_count"] == len(GIN_TOKENS)
    assert validated["mapping_boundary"]["participant_identity_mapping_verified"] is True
    assert validated["scientific_boundary"]["cross_dataset_validation_created"] is False

    serialized = certificate.read_text(encoding="utf-8")
    assert "CLI-S01" not in serialized
    assert "CLI-S16" not in serialized
    assert "free_viewing" not in serialized
