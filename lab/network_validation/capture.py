from __future__ import annotations

import hashlib
import struct
from pathlib import Path
from typing import Any

from .contracts import CAPTURE_SCHEMA, ContractError, validate_capture_manifest


def pcap_summary(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    if len(data) < 24:
        raise ValueError("pcap header missing")
    magic = data[:4]
    endian = "<" if magic in {b"\xd4\xc3\xb2\xa1", b"\x4d\x3c\xb2\xa1"} else ">" if magic in {b"\xa1\xb2\xc3\xd4", b"\xa1\xb2\x3c\x4d"} else None
    if endian is None:
        raise ValueError("unsupported pcap magic")
    offset, packets = 24, 0
    while offset + 16 <= len(data):
        _, _, captured, _ = struct.unpack_from(endian + "IIII", data, offset)
        offset += 16
        if captured < 0 or offset + captured > len(data):
            raise ValueError("truncated pcap record")
        offset += captured
        packets += 1
    if offset != len(data):
        raise ValueError("trailing pcap bytes")
    return {"packet_count": packets, "byte_count": len(data), "pcap_sha256": hashlib.sha256(data).hexdigest()}


def build_capture_manifest(metadata: dict[str, Any], dataset_root: Path, execution: dict[str, Any]) -> dict[str, Any]:
    pcap_path = dataset_root / metadata["pcap_path"]
    if not pcap_path.is_file():
        raise ContractError("pcap file missing")
    summary = pcap_summary(pcap_path)
    manifest = {"schema_version": CAPTURE_SCHEMA, **metadata, **summary}
    validate_capture_manifest(manifest, dataset_root, execution)
    return manifest


def validate_capture_set(
    manifests: list[dict[str, Any]],
    dataset_root: Path,
    executions: dict[str, dict[str, Any]],
    markers: dict[str, list[dict[str, Any]]] | None = None,
) -> None:
    ids = [row["capture_id"] for row in manifests]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate capture ID")
    for manifest in manifests:
        scenario_token = manifest.get("scenario_token")
        if scenario_token not in executions:
            raise ContractError("capture execution reference missing")
        validate_capture_manifest(manifest, dataset_root, executions[scenario_token])
        if markers is not None:
            scenario_markers = markers.get(scenario_token, [])
            if {row.get("marker_type") for row in scenario_markers} != {"start", "end"}:
                raise ContractError("capture marker pair missing")
            if any(
                row.get("marker_nonce") != manifest["marker_association"]
                or row.get("capture_association") != manifest["capture_id"]
                or row.get("scenario_token") != scenario_token
                or row.get("campaign_token") != manifest["campaign_token"]
                for row in scenario_markers
            ):
                raise ContractError("capture marker linkage mismatch")
