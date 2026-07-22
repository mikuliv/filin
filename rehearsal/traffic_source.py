from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import struct
import time
from datetime import UTC, datetime
from pathlib import Path

from rehearsal.common import append_jsonl, digest, file_sha256, read_json, write_json


def _packet(seed: int, tick: int, ordinal: int, timestamp: float) -> tuple[int, int, bytes]:
    source = bytes((2, 0, 0, 17, (seed + ordinal) % 255, 1))
    target = bytes((2, 0, 0, 17, (tick + ordinal) % 255, 2))
    ethernet = target + source + struct.pack("!H", 0x0800)
    source_ip = socket.inet_aton(f"10.17.{(seed // 100) % 250 + 1}.{ordinal % 250 + 1}")
    target_ip = socket.inet_aton(f"10.18.{tick % 250 + 1}.{(ordinal * 7) % 250 + 1}")
    identification = (seed + tick + ordinal) & 0xFFFF
    ip = struct.pack("!BBHHHBBH4s4s", 0x45, 0, 40, identification, 0, 64, 6, 0, source_ip, target_ip)
    tcp = struct.pack("!HHIIBBHHH", 20000 + ordinal % 40000, 80 + ordinal % 32, tick * 1000 + ordinal, 0, 0x50, 0x02, 8192, 0, 0)
    packet = ethernet + ip + tcp
    seconds = int(timestamp)
    microseconds = int((timestamp - seconds) * 1_000_000)
    return seconds, microseconds, packet


def write_pcap(path: Path, seed: int, tick: int, rate: int, wall_time: float) -> dict[str, object]:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".pcap.tmp")
    with temporary.open("wb") as stream:
        stream.write(struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1))
        for ordinal in range(rate):
            timestamp = wall_time + ordinal / max(rate, 1)
            seconds, microseconds, packet = _packet(seed, tick, ordinal, timestamp)
            stream.write(struct.pack("<IIII", seconds, microseconds, len(packet), len(packet)))
            stream.write(packet)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    return {"pcap_sha256": file_sha256(path), "pcap_size": path.stat().st_size, "packet_count": rate}


def scheduled_rate(phases: list[dict[str, object]], elapsed_second: int) -> tuple[str, int]:
    for phase in phases:
        if int(phase["start_second"]) <= elapsed_second < int(phase["end_second"]):
            rate = phase["rate"]
            if isinstance(rate, int):
                return str(phase["phase"]), rate
            start, end = map(int, rate)
            span = max(1, int(phase["end_second"]) - int(phase["start_second"]) - 1)
            position = elapsed_second - int(phase["start_second"])
            return str(phase["phase"]), round(start + (end - start) * position / span)
    raise RuntimeError(f"schedule_gap:{elapsed_second}")


def execute(control: dict[str, object], root: Path) -> dict[str, object]:
    run_id = str(control["run_id"])
    duration = int(control["duration_seconds"])
    seed = int(control["seed"])
    phases = list(control["phases"])
    run_root = root / run_id
    receipts = run_root / "capture_receipts.jsonl"
    started_wall = time.time()
    started_monotonic = time.monotonic_ns()
    write_json(run_root / "source_started.json", {
        "run_id": run_id,
        "started_at": datetime.now(UTC).isoformat(),
        "started_wall_ns": time.time_ns(),
        "started_monotonic_ns": started_monotonic,
        "source_instance_id": control["source_instance_id"],
    })
    for tick in range(duration):
        deadline = started_monotonic + tick * 1_000_000_000
        remaining = (deadline - time.monotonic_ns()) / 1_000_000_000
        if remaining > 0:
            time.sleep(remaining)
        actual_monotonic = time.monotonic_ns()
        actual_wall = time.time()
        phase, rate = scheduled_rate(phases, tick)
        pcap = run_root / "captures" / f"window_{tick:05d}.pcap"
        detail = write_pcap(pcap, seed, tick, rate, actual_wall)
        capture_id = "cap_" + digest(["v0317", run_id, tick, detail["pcap_sha256"]])
        append_jsonl(receipts, [{
            "schema_version": "v0317_capture_receipt_v1",
            "run_id": run_id,
            "capture_sequence": tick,
            "capture_id": capture_id,
            "capture_path": str(pcap.relative_to(root)).replace("\\", "/"),
            "capture_closed_monotonic_ns": time.monotonic_ns(),
            "capture_wall_ns": time.time_ns(),
            "phase": phase,
            "scheduled_event_rate": rate,
            "synthetic_only": True,
            "closed_before_processing": True,
            **detail,
        }])
    final_deadline = started_monotonic + duration * 1_000_000_000
    remaining = (final_deadline - time.monotonic_ns()) / 1_000_000_000
    if remaining > 0:
        time.sleep(remaining)
    ended_monotonic = time.monotonic_ns()
    completed = {
        "schema_version": "v0317_source_completion_v1",
        "run_id": run_id,
        "started_wall_seconds": started_wall,
        "ended_wall_seconds": time.time(),
        "started_monotonic_ns": started_monotonic,
        "ended_monotonic_ns": ended_monotonic,
        "scheduled_duration_seconds": duration,
        "actual_duration_seconds": (ended_monotonic - started_monotonic) / 1_000_000_000,
        "capture_segment_count": duration,
        "captured_window_count": sum(scheduled_rate(phases, tick)[1] for tick in range(duration)),
        "completion_sha256": hashlib.sha256(receipts.read_bytes()).hexdigest(),
    }
    write_json(run_root / "source_completion.json", completed)
    return completed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--control", type=Path, default=Path("/run/rehearsal/control.json"))
    parser.add_argument("--runtime", type=Path, default=Path("/run/rehearsal"))
    args = parser.parse_args()
    last_control = None
    while True:
        if args.control.is_file():
            control = read_json(args.control)
            control_id = control.get("control_id")
            if control_id and control_id != last_control:
                result = execute(control, args.runtime)
                write_json(args.runtime / "source_last_completion.json", result)
                last_control = control_id
        time.sleep(0.2)


if __name__ == "__main__":
    raise SystemExit(main())
