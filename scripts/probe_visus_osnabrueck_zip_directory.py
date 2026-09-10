#!/usr/bin/env python3
"""Inspect only ZIP metadata for the legacy Osnabrueck Kurzhals/VISUS bundle.

The 2.6 GB dataset archive is not downloaded. This probe retrieves only the ZIP
end record and central directory using HTTP byte ranges over the legacy host.
TLS verification is deliberately bypassed only for reconnaissance because the
legacy server's certificate chain is invalid; no authority/rights promotion is
permitted from this evidence alone.
"""

from __future__ import annotations

import collections
import hashlib
import json
import re
import struct
import subprocess
from pathlib import Path

BUNDLE_URL = "https://w3o.ikw.uni-osnabrueck.de/media/cv/mm_mkv/Kurzhals.zip"
OUT = Path("visus_osnabrueck_zip_directory_probe.json")
TAIL = Path("zip_tail.bin")
CD = Path("zip_central_directory.bin")
HEADERS = Path("zip_headers.txt")
EOCD_SIG = b"PK\x05\x06"
CD_SIG = b"PK\x01\x02"
EOCD = struct.Struct("<4s4H2LH")
CD_HEADER = struct.Struct("<4s6H3L5H2L")


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args), check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )


def curl_range(spec: str, out: Path) -> dict[str, object]:
    out.unlink(missing_ok=True)
    HEADERS.unlink(missing_ok=True)
    proc = run(
        "curl", "--insecure", "-L", "--fail", "--silent", "--show-error",
        "--connect-timeout", "20", "--max-time", "180", "--range", spec,
        "-D", str(HEADERS), "-o", str(out), BUNDLE_URL,
    )
    header_text = (
        HEADERS.read_text(encoding="utf-8", errors="replace") if HEADERS.exists() else ""
    )
    ranges = re.findall(r"(?im)^content-range:\s*bytes\s+(\d+)-(\d+)/(\d+)\s*$", header_text)
    content_range = None
    if ranges:
        start, end, total = map(int, ranges[-1])
        content_range = {"start": start, "end": end, "total": total}
    data = out.read_bytes() if out.exists() else b""
    return {
        "range": spec,
        "curl_exit": proc.returncode,
        "stderr": proc.stderr.strip()[:3000],
        "bytes_received": len(data),
        "sha256": hashlib.sha256(data).hexdigest() if data else None,
        "content_range": content_range,
    }


def parse_eocd(raw: bytes, base_offset: int) -> dict[str, int]:
    pos = raw.rfind(EOCD_SIG)
    if pos < 0 or pos + EOCD.size > len(raw):
        raise RuntimeError("standard ZIP EOCD not found in suffix range")
    (
        sig, disk_no, cd_disk, disk_entries, total_entries, cd_size, cd_offset, comment_len
    ) = EOCD.unpack_from(raw, pos)
    if sig != EOCD_SIG:
        raise RuntimeError("EOCD signature mismatch")
    if pos + EOCD.size + comment_len > len(raw):
        raise RuntimeError("EOCD comment extends beyond fetched suffix")
    return {
        "absolute_offset": base_offset + pos,
        "disk_number": disk_no,
        "central_directory_disk": cd_disk,
        "entries_on_disk": disk_entries,
        "total_entries": total_entries,
        "central_directory_size": cd_size,
        "central_directory_offset": cd_offset,
        "comment_length": comment_len,
    }


def parse_central_directory(raw: bytes, expected_entries: int) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    pos = 0
    while pos + CD_HEADER.size <= len(raw):
        if raw[pos : pos + 4] != CD_SIG:
            break
        fields = CD_HEADER.unpack_from(raw, pos)
        (
            _sig, version_made, version_needed, flags, method, mod_time, mod_date,
            crc32, compressed_size, uncompressed_size, name_len, extra_len, comment_len,
            disk_start, internal_attrs, external_attrs, local_header_offset,
        ) = fields
        start = pos + CD_HEADER.size
        name_raw = raw[start : start + name_len]
        extra_start = start + name_len
        comment_start = extra_start + extra_len
        end = comment_start + comment_len
        if end > len(raw):
            raise RuntimeError("central directory entry extends beyond fetched range")
        encoding = "utf-8" if flags & 0x800 else "cp437"
        name = name_raw.decode(encoding, errors="replace")
        entries.append(
            {
                "name": name,
                "version_made_by": version_made,
                "version_needed": version_needed,
                "flags": flags,
                "compression_method": method,
                "crc32": f"{crc32:08x}",
                "compressed_size": compressed_size,
                "uncompressed_size": uncompressed_size,
                "disk_start": disk_start,
                "internal_attributes": internal_attrs,
                "external_attributes": external_attrs,
                "local_header_offset": local_header_offset,
            }
        )
        pos = end
    if len(entries) != expected_entries:
        raise RuntimeError(
            f"parsed {len(entries)} central-directory entries; expected {expected_entries}"
        )
    if pos != len(raw):
        trailing = len(raw) - pos
        if trailing > 0:
            raise RuntimeError(f"unexpected {trailing} trailing central-directory bytes")
    return entries


def main() -> None:
    suffix = curl_range("-131072", TAIL)
    cr = suffix.get("content_range")
    if not isinstance(cr, dict):
        raise RuntimeError("suffix probe did not return Content-Range")
    total_size = int(cr["total"])
    suffix_start = int(cr["start"])
    eocd = parse_eocd(TAIL.read_bytes(), suffix_start)

    cd_start = eocd["central_directory_offset"]
    cd_size = eocd["central_directory_size"]
    cd_end = cd_start + cd_size - 1
    directory_fetch = curl_range(f"{cd_start}-{cd_end}", CD)
    if directory_fetch.get("bytes_received") != cd_size:
        raise RuntimeError("central-directory byte count differs from EOCD declaration")
    entries = parse_central_directory(CD.read_bytes(), eocd["total_entries"])

    suffixes = collections.Counter(Path(str(e["name"])).suffix.lower() for e in entries)
    methods = collections.Counter(int(e["compression_method"]) for e in entries)
    ass = [e for e in entries if str(e["name"]).lower().endswith("_ass.mkv")]
    usf = [e for e in entries if str(e["name"]).lower().endswith("_usf.mkv")]
    dirs = [e for e in entries if str(e["name"]).endswith("/")]

    report = {
        "schema": "gazeforge.visus_osnabrueck_zip_directory_probe.v1",
        "source": {
            "url": BUNDLE_URL,
            "legacy_host_tls_verification": False,
            "remote_archive_size": total_size,
        },
        "range_fetches": {"suffix": suffix, "central_directory": directory_fetch},
        "eocd": eocd,
        "inventory": {
            "entry_count": len(entries),
            "directory_count": len(dirs),
            "suffix_counts": dict(sorted(suffixes.items())),
            "compression_method_counts": {str(k): v for k, v in sorted(methods.items())},
            "ass_mkv_count": len(ass),
            "usf_mkv_count": len(usf),
            "total_uncompressed_bytes": sum(int(e["uncompressed_size"]) for e in entries),
            "total_compressed_member_bytes": sum(int(e["compressed_size"]) for e in entries),
            "entries": entries,
        },
        "claim_boundary": {
            "central_directory_recovered": True,
            "dataset_member_bytes_recovered": False,
            "legacy_insecure_tls_is_authority_evidence": False,
            "original_visus_identity_proven": False,
            "complete_25_participant_corpus_proven": False,
            "analysis_rights_proven": False,
            "redistribution_rights_proven": False,
            "empirical_promotion_authorized": False,
            "frozen_evidence_promoted": False,
        },
    }
    OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "remote_archive_size": total_size,
        "entry_count": len(entries),
        "ass_mkv_count": len(ass),
        "usf_mkv_count": len(usf),
        "compression_methods": dict(methods),
        "member_names": [e["name"] for e in entries],
    }, indent=2))

    TAIL.unlink(missing_ok=True)
    CD.unlink(missing_ok=True)
    HEADERS.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
