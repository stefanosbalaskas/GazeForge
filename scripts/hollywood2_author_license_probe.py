"""Live probe for the Hollywood2EM open-license statement in the author dissertation."""

from __future__ import annotations

import json
import subprocess
import tempfile
import urllib.request
from pathlib import Path

from gazeforge.hollywood2_author_license_evidence import SOURCE_URL, build_probe_record

OUTPUT_PATH = Path("hollywood2_author_license_live_probe.json")


def _download_pdf() -> tuple[bytes, str]:
    request = urllib.request.Request(
        SOURCE_URL,
        headers={"User-Agent": "GazeForge/hollywood2-author-license-probe"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:  # noqa: S310
        data = response.read()
        final_url = response.geturl()
    if not data.startswith(b"%PDF"):
        raise RuntimeError("TUM dissertation endpoint did not return a PDF payload.")
    return data, final_url


def main() -> int:
    """Download, fingerprint, text-extract, and record the live dissertation evidence."""
    pdf_bytes, final_url = _download_pdf()
    with tempfile.TemporaryDirectory(prefix="gazeforge-hollywood2-license-") as tmp:
        pdf_path = Path(tmp) / "thesis.pdf"
        text_path = Path(tmp) / "thesis.txt"
        pdf_path.write_bytes(pdf_bytes)
        subprocess.run(
            ["pdftotext", "-layout", str(pdf_path), str(text_path)],
            check=True,
            timeout=120,
        )
        text = text_path.read_text(encoding="utf-8", errors="strict")

    record = build_probe_record(pdf_bytes=pdf_bytes, extracted_text=text, final_url=final_url)
    OUTPUT_PATH.write_text(
        json.dumps(record, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(record, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
