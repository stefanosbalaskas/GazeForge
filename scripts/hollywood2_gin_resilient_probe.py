#!/usr/bin/env python3
"""Run the Hollywood2EM live probe while preserving fail-closed failure evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

REPOSITORY = "https://gin.g-node.org/ioannis.agtzidis/hollywood2_em.git"
UNAVAILABLE_RECORD_TYPE = "hollywood2-gin-live-probe-unavailable-v1"
UNAVAILABLE_STATUS = "canonical_repository_route_unavailable"
LIVE_PROBE_SCRIPT = Path(__file__).with_name("hollywood2_gin_live_probe.py")
HTTP_STATUS_RE = re.compile(r"returned error:\s*(\d{3})\b", flags=re.IGNORECASE)


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def probe_fingerprint(payload: dict[str, Any]) -> str:
    """Return a SHA-256 identity excluding the record's self-fingerprint."""

    body = {
        key: value
        for key, value in payload.items()
        if key != "probe_fingerprint_sha256"
    }
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def _diagnostic_line(stderr: str) -> str:
    lines = [line.strip() for line in stderr.splitlines() if line.strip()]
    for line in reversed(lines):
        if line.lower().startswith("fatal:"):
            return line
    return lines[-1] if lines else ""


def _failure_class(diagnostic: str) -> tuple[str, int | None]:
    lowered = diagnostic.lower()
    match = HTTP_STATUS_RE.search(diagnostic)
    http_status = int(match.group(1)) if match else None
    if http_status == 403:
        return "http_forbidden", http_status
    if http_status == 404:
        return "http_not_found", http_status
    if "could not resolve host" in lowered:
        return "dns_resolution_failure", http_status
    if "timed out" in lowered or "timeout" in lowered:
        return "network_timeout", http_status
    if "failed to connect" in lowered or "connection refused" in lowered:
        return "connection_failure", http_status
    return "git_remote_failure", http_status


def build_failure_record(
    *,
    repository: str,
    attempt: int,
    result: subprocess.CompletedProcess[str],
) -> dict[str, Any]:
    """Build a compact failure record without embedding volatile traceback text."""

    diagnostic = _diagnostic_line(result.stderr)
    failure_class, http_status = _failure_class(diagnostic)
    record: dict[str, Any] = {
        "record_type": UNAVAILABLE_RECORD_TYPE,
        "status": UNAVAILABLE_STATUS,
        "repository": repository,
        "attempt": attempt,
        "child_probe": {
            "script": LIVE_PROBE_SCRIPT.name,
            "returncode": int(result.returncode),
            "failure_class": failure_class,
            "http_status": http_status,
            "diagnostic_sha256": hashlib.sha256(diagnostic.encode("utf-8")).hexdigest(),
        },
        "scientific_boundary": {
            "authoritative_repository_revision_resolved_in_this_attempt": False,
            "source_identity_invalidated": False,
            "dataset_license_verified": False,
            "analysis_use_authorized": False,
            "raw_data_redistribution_authorized": False,
            "participant_identity_mapping_verified": False,
            "participant_disjoint_model_validation_created": False,
            "cross_dataset_validation_created": False,
            "new_frozen_evidence_performance_claim_created": False,
            "native_60hz_or_gp3_validity_created": False,
            "scientific_reproduction_failure_inferred": False,
        },
        "claim_limits": [
            "This record proves only that the canonical public GIN route was unavailable to this probe attempt.",
            "A route-level access failure does not invalidate the previously pinned source identity or reviewed aggregate evidence.",
            "No dataset licence, participant mapping, cross-dataset, Frozen Evidence, or native-GP3 claim is created by an availability failure.",
        ],
    }
    record["probe_fingerprint_sha256"] = probe_fingerprint(record)
    return record


def _write_record(path: Path, record: dict[str, Any]) -> None:
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", default=REPOSITORY)
    parser.add_argument("--output", default="hollywood2_gin_live_probe.json")
    parser.add_argument("--attempt", type=int, required=True)
    args = parser.parse_args()
    if args.attempt < 1:
        parser.error("--attempt must be at least 1")

    output = Path(args.output)
    command = [
        sys.executable,
        str(LIVE_PROBE_SCRIPT),
        "--repository",
        args.repository,
        "--output",
        str(output),
    ]
    result = subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode == 0:
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        return 0

    record = build_failure_record(
        repository=args.repository,
        attempt=args.attempt,
        result=result,
    )
    _write_record(output, record)
    summary = {
        "attempt": record["attempt"],
        "failure_class": record["child_probe"]["failure_class"],
        "http_status": record["child_probe"]["http_status"],
        "probe_fingerprint_sha256": record["probe_fingerprint_sha256"],
        "status": record["status"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True), file=sys.stderr)
    return int(result.returncode) or 1


if __name__ == "__main__":
    raise SystemExit(main())
