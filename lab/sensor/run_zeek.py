from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline processing of a captured PCAP with Zeek.")
    parser.add_argument("--pcap", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--storage-backend", default="host_filesystem", choices=("host_filesystem", "docker_volume"))
    parser.add_argument("--capture-volume", default="filin_sensor_capture")
    parser.add_argument("--run-id")
    parser.add_argument("--attempt-id", default="attempt_001")
    args = parser.parse_args()
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    if args.storage_backend == "docker_volume":
        sys.path.insert(0, str(Path(__file__).parent))
        from artifact_storage import SensorArtifactStorage

        result = SensorArtifactStorage(volume_name=args.capture_volume).run_zeek(
            args.pcap, args.run_id or "run", args.attempt_id
        )
        if result.returncode == 0:
            subprocess.run(
                [
                    "docker", "run", "--rm", "-v", "filin_sensor_zeek:/zeek:ro",
                    "-v", f"{output.resolve()}:/export", "busybox", "sh", "-c",
                    f"cp -a /zeek/{args.run_id or 'run'}/{args.attempt_id}/. /export/",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
    else:
        result = subprocess.run(
            [
                "docker", "run", "--rm", "-v", f"{Path(args.pcap).resolve()}:/input/capture.pcap:ro",
                "-v", f"{output.resolve()}:/output", "zeek/zeek:latest", "sh", "-c",
                "cd /output && zeek -C -r /input/capture.pcap LogAscii::use_json=T",
            ],
            capture_output=True,
            text=True,
        )
    if args.strict and (result.returncode or not (output / "conn.log").exists()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
