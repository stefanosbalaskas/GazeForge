from __future__ import annotations

import json
from pathlib import Path

from gazeforge.gaze_in_wild_first_party_resolution import response_fingerprint
from gazeforge.gaze_in_wild_first_party_resolution_cli import main

_ROOT = Path(__file__).resolve().parents[1]
_DISTRIBUTION = (
    _ROOT
    / "validation/evidence/gaze-in-wild/gaze-in-wild-distribution-availability-evidence-v1.json"
)
_CURRENT = (
    _ROOT
    / "validation/evidence/gaze-in-wild/"
    "gaze-in-wild-current-first-party-listing-evidence-v1.json"
)
_REQUEST = (
    _ROOT
    / "validation/requests/gaze-in-wild/gaze-in-wild-first-party-resolution-request-v1.json"
)


def _parent_args() -> list[str]:
    return [
        "--distribution-evidence",
        str(_DISTRIBUTION),
        "--current-listing-evidence",
        str(_CURRENT),
    ]


def test_cli_generates_exact_request_packet(tmp_path: Path, capsys) -> None:
    output = tmp_path / "request.json"
    assert main(["request", *_parent_args(), "--output", str(output)]) == 0
    payload = json.loads(capsys.readouterr().out)
    record = json.loads(output.read_text(encoding="utf-8"))
    assert payload["request_fingerprint_sha256"] == record["request_fingerprint_sha256"]
    assert record == json.loads(_REQUEST.read_text(encoding="utf-8"))


def test_cli_validates_committed_request(capsys) -> None:
    assert main(["request-validate", *_parent_args(), "--request", str(_REQUEST)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["request_fingerprint_sha256"].startswith("39ae2742")


def test_cli_response_scaffold_hashes_but_does_not_serialize_message(
    tmp_path: Path,
    capsys,
) -> None:
    message = tmp_path / "reply.eml"
    message.write_text("private correspondence text", encoding="utf-8")
    output = tmp_path / "response.json"
    assert (
        main(
            [
                "response-scaffold",
                *_parent_args(),
                "--request",
                str(_REQUEST),
                "--correspondence",
                str(message),
                "--output",
                str(output),
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    record = json.loads(output.read_text(encoding="utf-8"))
    assert payload["raw_correspondence_serialized"] is False
    assert "private correspondence text" not in output.read_text(encoding="utf-8")
    assert payload["correspondence_sha256"] == record["correspondence_sha256"]


def test_cli_validates_reviewed_structured_response(tmp_path: Path, capsys) -> None:
    message = tmp_path / "reply.eml"
    message.write_text("reviewed first-party response", encoding="utf-8")
    response_path = tmp_path / "response.json"
    assert (
        main(
            [
                "response-scaffold",
                *_parent_args(),
                "--request",
                str(_REQUEST),
                "--correspondence",
                str(message),
                "--output",
                str(response_path),
            ]
        )
        == 0
    )
    capsys.readouterr()

    record = json.loads(response_path.read_text(encoding="utf-8"))
    record["received_on"] = "2026-09-06"
    record["channel"] = "email"
    record["sender"].update(
        {
            "name": "First Party",
            "email_or_identifier": "first.party@rit.edu",
            "claimed_role": "dataset steward",
        }
    )
    record["review"].update(
        {
            "status": "reviewed",
            "reviewer": "Stefanos Balaskas",
            "reviewed_on": "2026-09-06",
        }
    )
    record["response_fingerprint_sha256"] = response_fingerprint(record)
    response_path.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    assert (
        main(
            [
                "response-validate",
                *_parent_args(),
                "--request",
                str(_REQUEST),
                "--response",
                str(response_path),
                "--correspondence",
                str(message),
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["review_status"] == "reviewed"
    assert payload["authority_status"] == "unresolved"
    assert payload["analysis_use_status"] == "unresolved"
