"""Build the reviewed non-empirical source-resolution governance lock."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from gazeforge.source_resolution_lock import build_source_resolution_bundle_lock

_DEFAULT_PROTOCOLS = Path("validation/protocols")
_DEFAULT_OUTPUT = Path("validation/governance/source-resolution-bundle-lock-v1.json")
_REVIEW_BASIS = (
    "Reviewed current source-resolution checkpoint set for VISUS, Hollywood2EM, and Gaze-in-the-Wild; Hollywood2EM references separately frozen empirical source evidence and Gaze-in-the-Wild now binds first-author processing provenance plus publication-level Supplementary Table 1 participant/task context while exact dataset copy, rights, distributed-file identity, complete trial-to-task mapping, and source-audit readiness remain unresolved.",
    "This governance lock snapshots checkpoint identities only; it does not authorize empirical evidence, rights, source-audit readiness, or Frozen Evidence publication.",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocols", type=Path, default=_DEFAULT_PROTOCOLS)
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    parser.add_argument("--reviewed-on", default="2026-09-05")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    payload = build_source_resolution_bundle_lock(
        args.protocols,
        reviewed_on=args.reviewed_on,
        review_basis=_REVIEW_BASIS,
    )
    rendered = json.dumps(payload, indent=2, sort_keys=False) + "\n"
    if args.write:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
