from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "inspect_gaze_in_wild_explicit_task_mapping.py"
)
SOURCE_RECORD_TYPE = "gaze-in-wild-explicit-task-mapping-source-v1"
TRIAL_INDICES = (1, 2, 3, 4)
TASKS = ("Indoor_Walk", "Ball_Catch", "Visual_Search", "Tea_Making")


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def test_task_mapping_cli_candidate_review_and_certificate(tmp_path: Path) -> None:
    source = tmp_path / "authoritative-task-ledger.txt"
    source_bytes = b"Synthetic explicit TrIdx mapping source used only for CLI testing.\n"
    source.write_bytes(source_bytes)

    entries = [
        {"trial_index": index, "task_label": task}
        for index, task in zip(TRIAL_INDICES, TASKS, strict=True)
    ]
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "record_type": SOURCE_RECORD_TYPE,
                "source_reference": "synthetic-cli-test://authoritative-task-ledger",
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
    assert '"task_label"' not in result.stdout
    assert "Tea_Making" not in result.stdout

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
            "mapping_explicitness_evidence": "Synthetic CLI explicit lookup evidence.",
            "mapping_transcription_verified": True,
            "mapping_transcription_evidence": "Synthetic CLI transcription evidence.",
            "publication_task_semantics_verified": True,
            "publication_task_semantics_evidence": (
                "Synthetic CLI publication-task evidence."
            ),
            "source_version_scope_verified": True,
            "source_version_scope_evidence": "Synthetic CLI version-scope evidence.",
            "tridx4_explicit_in_source_verified": True,
            "tridx4_explicitness_evidence": "Synthetic source directly states TrIdx 4.",
            "no_elimination_or_order_inference_used_verified": True,
            "no_elimination_or_order_inference_evidence": (
                "Synthetic direct lookup; no elimination or order inference."
            ),
            "rights_scope_promoted": False,
            "empirical_validation_created": False,
            "quarantine_exit_authorized": False,
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
    assert '"task_label"' not in result.stdout
    assert "Tea_Making" not in result.stdout

    validated = json.loads(certificate.read_text(encoding="utf-8"))
    assert validated["record_type"] == (
        "gaze-in-wild-explicit-task-mapping-certificate-v1"
    )
    assert validated["trial_index_count"] == len(TRIAL_INDICES)
    assert validated["mapping_boundary"]["authoritative_trial_task_mapping_verified"] is True
    assert validated["mapping_boundary"]["tridx4_explicit_in_source_verified"] is True
    assert validated["mapping_boundary"]["tridx4_tea_making_inferred_by_elimination"] is False
    assert validated["scientific_boundary"]["task_stratified_validation_created"] is False

    serialized = certificate.read_text(encoding="utf-8")
    assert '"mapping_entries"' not in serialized
    assert '"trial_task_mapping"' not in serialized
    assert '"4": "Tea_Making"' not in serialized
