from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from pypdf import PdfReader

_REQUIRED_MARKERS = (
    "Dataset status and error measures",
    "Indoor navigation",
    "Ball catching",
    "Visual search",
    "Tea making",
    "Data discarded",
)


def _inspect_pdf(path: Path, *, require_participant_23: bool) -> dict[str, object]:
    raw = path.read_bytes()
    if not raw.startswith(b"%PDF"):
        raise SystemExit(f"{path} is not a PDF")
    reader = PdfReader(str(path))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)
    canonical = re.sub(r"\s+", " ", text).strip()
    required = all(marker in text for marker in _REQUIRED_MARKERS)
    if require_participant_23:
        required = required and bool(re.search(r"23\s+60", text))
    return {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "byte_size": len(raw),
        "page_count": len(reader.pages),
        "text_sha256_whitespace_canonical": hashlib.sha256(
            canonical.encode("utf-8")
        ).hexdigest(),
        "required_markers_present": required,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build metadata-only GIW participant/task publication probe."
    )
    parser.add_argument("--springer", type=Path, required=True)
    parser.add_argument("--arxiv", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    record = {
        "record_type": "gaze-in-wild-participant-task-live-probe-v2",
        "springer": _inspect_pdf(args.springer, require_participant_23=True),
        "arxiv": _inspect_pdf(args.arxiv, require_participant_23=True),
        "boundaries": {
            "exact_distribution_equivalence_verified": False,
            "universal_tridx_to_task_name_mapping_verified": False,
            "analysis_use_permitted": False,
            "redistribution_permission_verified": False,
            "new_empirical_performance_claim_created": False,
        },
    }
    args.output.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("springer sha256:", record["springer"]["sha256"])
    print("arxiv sha256:", record["arxiv"]["sha256"])
    print("springer markers:", record["springer"]["required_markers_present"])
    print("arxiv markers:", record["arxiv"]["required_markers_present"])
    print("universal TrIdx mapping verified: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
