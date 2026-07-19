from __future__ import annotations

from pathlib import Path

from .common import ROOT, read_yaml, sha256_file, sha256_json, write_json


def create(campaign_path: Path, output_root: Path, output: Path, protocol_sha256: str) -> dict:
    campaign = read_yaml(campaign_path)
    captures = []
    for run in campaign["runs"]:
        run_dir = output_root / "runs" / run["run_id"]
        manifest = read_yaml(run_dir / "scenario_manifest.yaml")
        for scenario in manifest["scenarios"]:
            path = run_dir / "captures" / f"{int(scenario['run_sequence']):03d}.pcap"
            if not path.is_file() or path.stat().st_size <= 24:
                raise RuntimeError(f"Отсутствует canonical capture: {path}")
            captures.append({"run_id": run["run_id"], "marker_id": scenario["execution_id"], "environment_group": run["group"], "path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256_file(path), "size": path.stat().st_size})
    hashes = [row["sha256"] for row in captures]
    payload = {"protocol_sha256": protocol_sha256, "campaign_sha256": sha256_file(campaign_path), "source_commit": "8f060a73b13aa8b89333da13cc645b5202d57eb9", "capture_count": len(captures), "capture_hash_count": len(hashes), "duplicate_capture_hash_count": len(hashes) - len(set(hashes)), "missing_capture_count": 0, "fallback_path_count": 0, "captures": captures}
    payload["capture_manifest_content_sha256"] = sha256_json(captures)
    payload["capture_lock_passed"] = len(captures) == 760 and len(set(hashes)) == 760
    write_json(output, payload)
    return {**payload, "capture_manifest_sha256": sha256_file(output)}
