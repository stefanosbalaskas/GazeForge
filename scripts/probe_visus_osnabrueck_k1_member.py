#!/usr/bin/env python3
"""Selectively recover and inspect one USF member from the legacy VISUS ZIP.

The script fetches only the local header and compressed byte range for the exact
`01-car pursuit_usf.mkv` member, validates ZIP metadata/CRC, inflates it inside
the ephemeral Actions runner, inspects track structure, then deletes all source
bytes. Only a compact structural JSON report is retained.
"""

from __future__ import annotations

import binascii
import collections
import hashlib
import json
import re
import shutil
import struct
import subprocess
import zlib
from pathlib import Path

BUNDLE_URL = "https://w3o.ikw.uni-osnabrueck.de/media/cv/mm_mkv/Kurzhals.zip"
MEMBER_NAME = "01-car pursuit_usf.mkv"
EXPECTED_LOCAL_OFFSET = 122_791_262
EXPECTED_COMPRESSED_SIZE = 44_053_305
EXPECTED_UNCOMPRESSED_SIZE = 44_314_872
EXPECTED_CRC32 = 0x189CD76C
EXPECTED_METHOD = 8
LOCAL_HEADER = struct.Struct("<4s5H3L2H")
LOCAL_SIG = b"PK\x03\x04"
EBML_MAGIC = bytes.fromhex("1a45dfa3")
OUT = Path("visus_osnabrueck_k1_member_probe.json")
HEADER_BIN = Path("k1_local_header.bin")
COMPRESSED_BIN = Path("k1_compressed.bin")
MKV = Path("01-car pursuit_usf.mkv")
HEADERS = Path("range_headers.txt")


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args), check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_range(start: int, end: int, out: Path, max_size: int) -> dict[str, object]:
    out.unlink(missing_ok=True)
    HEADERS.unlink(missing_ok=True)
    proc = run(
        "curl", "--insecure", "-L", "--fail", "--silent", "--show-error",
        "--connect-timeout", "20", "--max-time", "300", "--max-filesize", str(max_size),
        "--range", f"{start}-{end}", "-D", str(HEADERS), "-o", str(out), BUNDLE_URL,
    )
    text = HEADERS.read_text(encoding="utf-8", errors="replace") if HEADERS.exists() else ""
    matches = re.findall(r"(?im)^content-range:\s*bytes\s+(\d+)-(\d+)/(\d+)\s*$", text)
    cr = None
    if matches:
        a, b, total = map(int, matches[-1])
        cr = {"start": a, "end": b, "total": total}
    raw_size = out.stat().st_size if out.exists() else 0
    ok = (
        proc.returncode == 0
        and cr is not None
        and cr["start"] == start
        and cr["end"] == end
        and raw_size == end - start + 1
    )
    return {
        "start": start,
        "end": end,
        "curl_exit": proc.returncode,
        "stderr": proc.stderr.strip()[:3000],
        "content_range": cr,
        "bytes_received": raw_size,
        "exact_range_verified": ok,
    }


def summarize_subtitle(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    tags = collections.Counter(
        m.group(1).lower() for m in re.finditer(r"<\s*/?\s*([A-Za-z_][\w:.-]*)", text)
    )
    attrs = collections.Counter(
        m.group(1).lower() for m in re.finditer(r"\s([A-Za-z_][\w:.-]*)\s*=\s*[\"']", text)
    )
    return {
        "bytes": len(raw),
        "sha256": sha256_bytes(raw),
        "line_count": text.count("\n") + 1,
        "top_tag_names": tags.most_common(30),
        "top_attribute_names": attrs.most_common(40),
        "contains_gaze_term": "gaze" in text.lower(),
        "contains_fixation_term": "fixation" in text.lower(),
        "contains_polygon_term": "polygon" in text.lower(),
        "contains_point_term": "point" in text.lower(),
        "contains_timestamp_term": "timestamp" in text.lower(),
    }


def inspect_mkv() -> dict[str, object]:
    ff = run(
        "ffprobe", "-v", "error", "-count_packets", "-show_format", "-show_streams",
        "-of", "json", str(MKV),
    )
    result: dict[str, object] = {
        "ffprobe_exit": ff.returncode,
        "ffprobe_stderr": ff.stderr.strip()[:3000],
    }
    if ff.returncode == 0:
        data = json.loads(ff.stdout)
        streams = []
        for s in data.get("streams", []):
            streams.append({
                "index": s.get("index"),
                "codec_name": s.get("codec_name"),
                "codec_long_name": s.get("codec_long_name"),
                "codec_type": s.get("codec_type"),
                "width": s.get("width"),
                "height": s.get("height"),
                "r_frame_rate": s.get("r_frame_rate"),
                "avg_frame_rate": s.get("avg_frame_rate"),
                "duration": s.get("duration"),
                "nb_read_packets": s.get("nb_read_packets"),
                "tags": s.get("tags", {}),
            })
        result["ffprobe"] = {
            "format": {k: data.get("format", {}).get(k) for k in (
                "format_name", "format_long_name", "duration", "size", "bit_rate"
            )},
            "stream_count": len(streams),
            "stream_type_counts": dict(collections.Counter(s["codec_type"] for s in streams)),
            "streams": streams,
        }

    mkvmerge = shutil.which("mkvmerge")
    mkvextract = shutil.which("mkvextract")
    if not (mkvmerge and mkvextract):
        result["mkvtoolnix_available"] = False
        return result
    result["mkvtoolnix_available"] = True
    ident = run(mkvmerge, "-J", str(MKV))
    result["mkvmerge_exit"] = ident.returncode
    result["mkvmerge_stderr"] = ident.stderr.strip()[:3000]
    if ident.returncode != 0:
        return result
    data = json.loads(ident.stdout)
    tracks = []
    payloads = []
    for t in data.get("tracks", []):
        p = t.get("properties", {})
        tracks.append({
            "id": t.get("id"),
            "type": t.get("type"),
            "codec": t.get("codec"),
            "codec_id": p.get("codec_id"),
            "track_name": p.get("track_name"),
            "language": p.get("language"),
            "default_track": p.get("default_track"),
            "forced_track": p.get("forced_track"),
        })
        if t.get("type") != "subtitles":
            continue
        tid = int(t["id"])
        temp = Path(f"subtitle_{tid}.bin")
        ex = run(mkvextract, "tracks", str(MKV), f"{tid}:{temp}")
        item: dict[str, object] = {
            "track_id": tid,
            "extract_exit": ex.returncode,
            "stderr": ex.stderr.strip()[:2000],
        }
        if ex.returncode == 0 and temp.exists():
            item.update(summarize_subtitle(temp))
            temp.unlink()
        payloads.append(item)
    result["mkvmerge"] = {
        "track_count": len(tracks),
        "track_type_counts": dict(collections.Counter(t["type"] for t in tracks)),
        "tracks": tracks,
    }
    result["subtitle_payload_summaries"] = payloads
    return result


def main() -> None:
    header_fetch = fetch_range(
        EXPECTED_LOCAL_OFFSET, EXPECTED_LOCAL_OFFSET + LOCAL_HEADER.size - 1,
        HEADER_BIN, 4096,
    )
    if not header_fetch["exact_range_verified"]:
        raise RuntimeError("local-header range was not returned exactly")
    raw_header = HEADER_BIN.read_bytes()
    (
        sig, version_needed, flags, method, mod_time, mod_date, crc_local,
        comp_local, uncomp_local, name_len, extra_len,
    ) = LOCAL_HEADER.unpack(raw_header)
    if sig != LOCAL_SIG:
        raise RuntimeError("local header signature mismatch")
    name_extra_fetch = fetch_range(
        EXPECTED_LOCAL_OFFSET + LOCAL_HEADER.size,
        EXPECTED_LOCAL_OFFSET + LOCAL_HEADER.size + name_len + extra_len - 1,
        HEADER_BIN, 65536,
    )
    if not name_extra_fetch["exact_range_verified"]:
        raise RuntimeError("name/extra range was not returned exactly")
    name_extra = HEADER_BIN.read_bytes()
    name = name_extra[:name_len].decode("utf-8" if flags & 0x800 else "cp437", errors="replace")
    if name != MEMBER_NAME:
        raise RuntimeError(f"local-header member mismatch: {name!r}")
    if method != EXPECTED_METHOD:
        raise RuntimeError(f"unexpected compression method {method}")

    data_start = EXPECTED_LOCAL_OFFSET + LOCAL_HEADER.size + name_len + extra_len
    data_end = data_start + EXPECTED_COMPRESSED_SIZE - 1
    data_fetch = fetch_range(data_start, data_end, COMPRESSED_BIN, 60_000_000)
    if not data_fetch["exact_range_verified"]:
        raise RuntimeError("compressed member range was not returned exactly")

    compressed = COMPRESSED_BIN.read_bytes()
    inflated = zlib.decompress(compressed, -15)
    crc = binascii.crc32(inflated) & 0xFFFFFFFF
    if len(inflated) != EXPECTED_UNCOMPRESSED_SIZE:
        raise RuntimeError("inflated size mismatch")
    if crc != EXPECTED_CRC32:
        raise RuntimeError(f"CRC mismatch: {crc:08x}")
    if not inflated.startswith(EBML_MAGIC):
        raise RuntimeError("inflated member lacks EBML magic")
    MKV.write_bytes(inflated)

    report = {
        "schema": "gazeforge.visus_osnabrueck_k1_member_probe.v1",
        "source": {
            "archive_url": BUNDLE_URL,
            "legacy_host_tls_verification": False,
            "member_name": MEMBER_NAME,
            "central_directory_expected": {
                "local_header_offset": EXPECTED_LOCAL_OFFSET,
                "compression_method": EXPECTED_METHOD,
                "compressed_size": EXPECTED_COMPRESSED_SIZE,
                "uncompressed_size": EXPECTED_UNCOMPRESSED_SIZE,
                "crc32": f"{EXPECTED_CRC32:08x}",
            },
        },
        "local_header": {
            "version_needed": version_needed,
            "flags": flags,
            "compression_method": method,
            "mod_time": mod_time,
            "mod_date": mod_date,
            "local_crc32_field": f"{crc_local:08x}",
            "local_compressed_size_field": comp_local,
            "local_uncompressed_size_field": uncomp_local,
            "name_length": name_len,
            "extra_length": extra_len,
            "member_name": name,
        },
        "range_fetches": {
            "local_header": header_fetch,
            "name_extra": name_extra_fetch,
            "compressed_payload": data_fetch,
        },
        "validation": {
            "compressed_sha256": sha256_file(COMPRESSED_BIN),
            "inflated_sha256": sha256_file(MKV),
            "inflated_bytes": MKV.stat().st_size,
            "crc32": f"{crc:08x}",
            "crc_matches_central_directory": crc == EXPECTED_CRC32,
            "ebml_magic": True,
        },
        "inspection": inspect_mkv(),
        "claim_boundary": {
            "single_institutional_derivative_member_recovered": True,
            "legacy_insecure_tls_is_authority_evidence": False,
            "original_visus_identity_proven": False,
            "complete_25_participant_corpus_proven": False,
            "annotation_identity_proven": False,
            "analysis_rights_proven": False,
            "redistribution_rights_proven": False,
            "empirical_promotion_authorized": False,
            "frozen_evidence_promoted": False,
        },
    }
    OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "member": MEMBER_NAME,
        "inflated_bytes": MKV.stat().st_size,
        "crc32": f"{crc:08x}",
        "inflated_sha256": report["validation"]["inflated_sha256"],
        "track_counts": report["inspection"].get("mkvmerge", {}).get("track_type_counts"),
    }, indent=2))

    for path in (HEADER_BIN, COMPRESSED_BIN, MKV, HEADERS):
        path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
