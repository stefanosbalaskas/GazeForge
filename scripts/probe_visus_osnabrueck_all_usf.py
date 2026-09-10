#!/usr/bin/env python3
"""Recover and structurally inspect the 11 standard Kurzhals/VISUS USF members.

The legacy Osnabrueck ZIP is accessed by exact HTTP ranges with TLS verification
bypassed only because its historical server has an invalid certificate chain.
Each ZIP member is validated against its central-directory metadata, inflated in
the ephemeral runner, inspected, then deleted. Only structural JSON and hashes
are retained; source video/gaze/AOI bytes are never uploaded.
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
OUT = Path("visus_osnabrueck_all_usf_probe.json")
EOCD = struct.Struct("<4s4H2LH")
CD_HEADER = struct.Struct("<4s6H3L5H2L")
LOCAL_HEADER = struct.Struct("<4s5H3L2H")
EOCD_SIG = b"PK\x05\x06"
CD_SIG = b"PK\x01\x02"
LOCAL_SIG = b"PK\x03\x04"
EBML_MAGIC = bytes.fromhex("1a45dfa3")
PARTICIPANT_RE = re.compile(r"^P(\d{1,2})([AB])$")


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args), check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )


def fetch_range(start: int, end: int, out: Path, max_size: int) -> dict[str, object]:
    headers = Path(f"{out.name}.headers")
    out.unlink(missing_ok=True)
    headers.unlink(missing_ok=True)
    proc = run(
        "curl", "--insecure", "-L", "--fail", "--silent", "--show-error",
        "--connect-timeout", "30", "--max-time", "600", "--max-filesize", str(max_size),
        "--range", f"{start}-{end}", "-D", str(headers), "-o", str(out), BUNDLE_URL,
    )
    text = headers.read_text(encoding="utf-8", errors="replace") if headers.exists() else ""
    found = re.findall(r"(?im)^content-range:\s*bytes\s+(\d+)-(\d+)/(\d+)\s*$", text)
    cr = None
    if found:
        a, b, total = map(int, found[-1])
        cr = {"start": a, "end": b, "total": total}
    size = out.stat().st_size if out.exists() else 0
    verified = (
        proc.returncode == 0
        and cr is not None
        and cr["start"] == start
        and cr["end"] == end
        and size == end - start + 1
    )
    headers.unlink(missing_ok=True)
    return {
        "start": start,
        "end": end,
        "curl_exit": proc.returncode,
        "stderr": proc.stderr.strip()[:2000],
        "content_range": cr,
        "bytes_received": size,
        "exact_range_verified": verified,
    }


def recover_directory() -> tuple[int, list[dict[str, object]], dict[str, object]]:
    suffix = Path("bundle_suffix.bin")
    probe = fetch_range(2_598_599_414, 2_598_730_484, suffix, 200_000)
    if not probe["exact_range_verified"]:
        raise RuntimeError("failed to recover exact archive suffix")
    total = int(probe["content_range"]["total"])
    raw = suffix.read_bytes()
    pos = raw.rfind(EOCD_SIG)
    if pos < 0:
        raise RuntimeError("EOCD not found")
    fields = EOCD.unpack_from(raw, pos)
    _, disk, cd_disk, disk_entries, total_entries, cd_size, cd_offset, comment_len = fields
    if disk or cd_disk or disk_entries != total_entries or comment_len != 0:
        raise RuntimeError("unexpected multi-disk/comment ZIP structure")
    cd = Path("bundle_cd.bin")
    cd_probe = fetch_range(cd_offset, cd_offset + cd_size - 1, cd, cd_size + 1024)
    if not cd_probe["exact_range_verified"]:
        raise RuntimeError("failed to recover exact central directory")
    entries: list[dict[str, object]] = []
    data = cd.read_bytes()
    cur = 0
    while cur + CD_HEADER.size <= len(data):
        if data[cur : cur + 4] != CD_SIG:
            break
        f = CD_HEADER.unpack_from(data, cur)
        (
            _sig, _vmade, _vneed, flags, method, _mtime, _mdate, crc32,
            compressed_size, uncompressed_size, name_len, extra_len, comment_len,
            _disk_start, _int_attr, _ext_attr, local_offset,
        ) = f
        start = cur + CD_HEADER.size
        name_raw = data[start : start + name_len]
        enc = "utf-8" if flags & 0x800 else "cp437"
        name = name_raw.decode(enc, errors="replace")
        entries.append({
            "name": name,
            "flags": flags,
            "compression_method": method,
            "crc32": f"{crc32:08x}",
            "crc32_int": crc32,
            "compressed_size": compressed_size,
            "uncompressed_size": uncompressed_size,
            "local_header_offset": local_offset,
        })
        cur = start + name_len + extra_len + comment_len
    if len(entries) != total_entries or cur != len(data):
        raise RuntimeError("central-directory parser did not consume declared inventory")
    suffix.unlink(missing_ok=True)
    cd.unlink(missing_ok=True)
    return total, entries, {"suffix": probe, "central_directory": cd_probe}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def inflate_member(compressed: Path, output: Path) -> tuple[int, int, str]:
    dec = zlib.decompressobj(-15)
    crc = 0
    size = 0
    sha = hashlib.sha256()
    with compressed.open("rb") as src, output.open("wb") as dst:
        for chunk in iter(lambda: src.read(1024 * 1024), b""):
            raw = dec.decompress(chunk)
            if raw:
                dst.write(raw)
                crc = binascii.crc32(raw, crc)
                size += len(raw)
                sha.update(raw)
        tail = dec.flush()
        if tail:
            dst.write(tail)
            crc = binascii.crc32(tail, crc)
            size += len(tail)
            sha.update(tail)
    return crc & 0xFFFFFFFF, size, sha.hexdigest()


def summarize_payload(path: Path) -> dict[str, object]:
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
        "sha256": hashlib.sha256(raw).hexdigest(),
        "line_count": text.count("\n") + 1,
        "top_tags": tags.most_common(12),
        "top_attributes": attrs.most_common(12),
        "semantic_terms": {
            term: term in text.lower()
            for term in ("gaze", "fixation", "timestamp", "point", "rectangle", "polygon")
        },
    }


def inspect_mkv(mkv: Path) -> dict[str, object]:
    ff = run(
        "ffprobe", "-v", "error", "-count_packets", "-show_format", "-show_streams",
        "-of", "json", str(mkv),
    )
    if ff.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {ff.stderr[:500]}")
    ffdata = json.loads(ff.stdout)
    videos = [s for s in ffdata.get("streams", []) if s.get("codec_type") == "video"]
    if len(videos) != 1:
        raise RuntimeError(f"expected exactly one video stream, got {len(videos)}")
    v = videos[0]

    mkvmerge = shutil.which("mkvmerge")
    mkvextract = shutil.which("mkvextract")
    if not (mkvmerge and mkvextract):
        raise RuntimeError("mkvtoolnix unavailable")
    ident = run(mkvmerge, "-J", str(mkv))
    if ident.returncode != 0:
        raise RuntimeError(f"mkvmerge identify failed: {ident.stderr[:500]}")
    data = json.loads(ident.stdout)
    tracks = data.get("tracks", [])
    subtitles = [t for t in tracks if t.get("type") == "subtitles"]
    participant_tracks = []
    aoi_tracks = []
    extract_args = [mkvextract, "tracks", str(mkv)]
    destinations: list[tuple[dict[str, object], Path]] = []
    for t in subtitles:
        tid = int(t["id"])
        props = t.get("properties", {})
        title = props.get("track_name") or f"track-{tid}"
        temp = Path(f"sub_{tid}.usf")
        extract_args.append(f"{tid}:{temp}")
        destinations.append((t, temp))
        m = PARTICIPANT_RE.match(title)
        entry = {"track_id": tid, "title": title}
        if m:
            entry["participant_number"] = int(m.group(1))
            entry["task_group"] = m.group(2)
            participant_tracks.append(entry)
        else:
            aoi_tracks.append(entry)
    ex = run(*extract_args)
    if ex.returncode != 0:
        raise RuntimeError(f"mkvextract failed: {ex.stderr[:500]}")

    payload_by_id = {}
    for t, temp in destinations:
        tid = int(t["id"])
        payload_by_id[tid] = summarize_payload(temp)
        temp.unlink(missing_ok=True)
    for collection in (participant_tracks, aoi_tracks):
        for item in collection:
            item["payload"] = payload_by_id[item["track_id"]]

    participant_numbers = sorted(int(x["participant_number"]) for x in participant_tracks)
    return {
        "video": {
            "codec_name": v.get("codec_name"),
            "width": v.get("width"),
            "height": v.get("height"),
            "r_frame_rate": v.get("r_frame_rate"),
            "avg_frame_rate": v.get("avg_frame_rate"),
            "packet_count": int(v["nb_read_packets"]) if v.get("nb_read_packets") else None,
            "container_duration": ffdata.get("format", {}).get("duration"),
            "container_size": int(ffdata.get("format", {}).get("size", 0)),
        },
        "track_count": len(tracks),
        "subtitle_track_count": len(subtitles),
        "participant_track_count": len(participant_tracks),
        "participant_numbers": participant_numbers,
        "participant_tracks": participant_tracks,
        "aoi_track_count": len(aoi_tracks),
        "aoi_tracks": aoi_tracks,
    }


def recover_one(entry: dict[str, object]) -> dict[str, object]:
    name = str(entry["name"])
    local = int(entry["local_header_offset"])
    comp_size = int(entry["compressed_size"])
    uncomp_size = int(entry["uncompressed_size"])
    crc_expected = int(entry["crc32_int"])
    hdr = Path("member_header.bin")
    compressed = Path("member_compressed.bin")
    mkv = Path("member.mkv")

    hfetch = fetch_range(local, local + LOCAL_HEADER.size - 1, hdr, 4096)
    if not hfetch["exact_range_verified"]:
        raise RuntimeError(f"{name}: local header fetch failed")
    f = LOCAL_HEADER.unpack(hdr.read_bytes())
    sig, _vneed, flags, method, _mt, _md, crc_local, comp_local, uncomp_local, name_len, extra_len = f
    if sig != LOCAL_SIG or method != int(entry["compression_method"]):
        raise RuntimeError(f"{name}: local header mismatch")
    nextra = fetch_range(
        local + LOCAL_HEADER.size,
        local + LOCAL_HEADER.size + name_len + extra_len - 1,
        hdr,
        max(65536, name_len + extra_len + 1024),
    )
    if not nextra["exact_range_verified"]:
        raise RuntimeError(f"{name}: filename/extra fetch failed")
    raw = hdr.read_bytes()
    local_name = raw[:name_len].decode("utf-8" if flags & 0x800 else "cp437", errors="replace")
    if local_name != name:
        raise RuntimeError(f"{name}: local filename mismatch {local_name!r}")
    data_start = local + LOCAL_HEADER.size + name_len + extra_len
    dfetch = fetch_range(
        data_start,
        data_start + comp_size - 1,
        compressed,
        min(400_000_000, comp_size + 1_000_000),
    )
    if not dfetch["exact_range_verified"]:
        raise RuntimeError(f"{name}: compressed payload fetch failed")
    compressed_sha = sha256_file(compressed)
    crc, inflated_size, inflated_sha = inflate_member(compressed, mkv)
    if inflated_size != uncomp_size or crc != crc_expected:
        raise RuntimeError(
            f"{name}: ZIP validation mismatch size={inflated_size}/{uncomp_size} "
            f"crc={crc:08x}/{crc_expected:08x}"
        )
    if mkv.read_bytes()[:4] != EBML_MAGIC:
        raise RuntimeError(f"{name}: inflated bytes lack EBML magic")
    inspection = inspect_mkv(mkv)
    result = {
        "member_name": name,
        "central_directory": {
            "local_header_offset": local,
            "compression_method": int(entry["compression_method"]),
            "compressed_size": comp_size,
            "uncompressed_size": uncomp_size,
            "crc32": f"{crc_expected:08x}",
        },
        "local_header_consistency": {
            "crc32": f"{crc_local:08x}",
            "compressed_size": comp_local,
            "uncompressed_size": uncomp_local,
            "name": local_name,
        },
        "range_fetches": {
            "header": hfetch,
            "name_extra": nextra,
            "payload": dfetch,
        },
        "validation": {
            "compressed_sha256": compressed_sha,
            "inflated_sha256": inflated_sha,
            "inflated_size": inflated_size,
            "crc32": f"{crc:08x}",
            "crc_match": True,
            "ebml_magic": True,
        },
        "inspection": inspection,
    }
    for p in (hdr, compressed, mkv):
        p.unlink(missing_ok=True)
    return result


def main() -> None:
    total, entries, directory_fetches = recover_directory()
    standard = [
        e for e in entries
        if re.match(r"^\d{2}-.*_usf\.mkv$", str(e["name"])) and "_poly_" not in str(e["name"])
    ]
    standard.sort(key=lambda e: str(e["name"]))
    if len(standard) != 11 or [str(e["name"])[:2] for e in standard] != [f"{i:02d}" for i in range(1, 12)]:
        raise RuntimeError("standard USF inventory is not exactly scenarios 01..11")
    if sum(int(e["compressed_size"]) for e in standard) > 1_400_000_000:
        raise RuntimeError("unexpected standard-USF transfer budget")

    scenarios = []
    for i, entry in enumerate(standard, 1):
        print(f"[{i}/11] recovering {entry['name']}", flush=True)
        scenario = recover_one(entry)
        if scenario["inspection"]["participant_track_count"] != 25:
            raise RuntimeError(f"{entry['name']}: expected 25 participant tracks")
        if scenario["inspection"]["participant_numbers"] != list(range(1, 26)):
            raise RuntimeError(f"{entry['name']}: participant numbers are not exactly 1..25")
        scenarios.append(scenario)

    aoi_counts = {s["member_name"]: s["inspection"]["aoi_track_count"] for s in scenarios}
    report = {
        "schema": "gazeforge.visus_osnabrueck_all_usf_probe.v1",
        "source": {
            "archive_url": BUNDLE_URL,
            "legacy_host_tls_verification": False,
            "remote_archive_size": total,
            "standard_usf_member_count": len(standard),
            "standard_usf_compressed_bytes": sum(int(e["compressed_size"]) for e in standard),
            "standard_usf_uncompressed_bytes": sum(int(e["uncompressed_size"]) for e in standard),
        },
        "directory_fetches": directory_fetches,
        "scenarios": scenarios,
        "cross_scenario_summary": {
            "scenario_count": len(scenarios),
            "all_crc_valid": all(s["validation"]["crc_match"] for s in scenarios),
            "all_ebml_valid": all(s["validation"]["ebml_magic"] for s in scenarios),
            "all_have_exact_participants_1_to_25": all(
                s["inspection"]["participant_numbers"] == list(range(1, 26)) for s in scenarios
            ),
            "participant_track_counts": {
                s["member_name"]: s["inspection"]["participant_track_count"] for s in scenarios
            },
            "aoi_track_counts": aoi_counts,
            "video_resolutions": {
                s["member_name"]: [
                    s["inspection"]["video"]["width"], s["inspection"]["video"]["height"]
                ] for s in scenarios
            },
            "video_frame_rates": {
                s["member_name"]: s["inspection"]["video"]["r_frame_rate"] for s in scenarios
            },
        },
        "claim_boundary": {
            "all_11_standard_usf_members_structurally_recovered": True,
            "all_25_participant_tracks_present_per_scenario": True,
            "legacy_insecure_tls_is_authority_evidence": False,
            "exact_original_file_identity_proven": False,
            "converter_transform_fidelity_independently_proven": False,
            "analysis_rights_promoted": False,
            "redistribution_rights_proven": False,
            "empirical_validation_promoted": False,
            "frozen_evidence_promoted": False,
        },
    }
    OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report["cross_scenario_summary"], indent=2), flush=True)


if __name__ == "__main__":
    main()
