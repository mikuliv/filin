"""Полный canonical capture manifest v0.3.10 до prediction."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
import yaml

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def build(root: Path, run_ids: list[str], output: Path, expected_count: int = 360) -> dict:
    entries, seen_paths = [], set()
    for run_id in run_ids:
        run_root = root / "lab/output/runs" / run_id
        capture_root = run_root / "captures"
        if not capture_root.is_dir() or (run_root / "sensor").resolve() == capture_root.resolve():
            raise ValueError(f"Canonical captures/ отсутствует: {run_id}")
        manifest = yaml.safe_load((run_root / "scenario_manifest.yaml").read_text(encoding="utf-8"))
        by_sequence = {int(row["run_sequence"]): row["execution_id"] for row in manifest["scenarios"]}
        paths = sorted(capture_root.rglob("*.pcap"), key=lambda path: path.relative_to(capture_root).as_posix())
        if len(paths) != 60:
            raise ValueError(f"Run {run_id} должен содержать 60 PCAP в captures/")
        for path in paths:
            relative = path.relative_to(root).as_posix()
            if relative in seen_paths or path.stat().st_size <= 0:
                raise ValueError("Обнаружен повторный путь или пустой PCAP")
            seen_paths.add(relative)
            try:
                sequence = int(path.stem)
            except ValueError as error:
                raise ValueError(f"PCAP не связан с marker interval: {relative}") from error
            if sequence not in by_sequence:
                raise ValueError(f"PCAP не связан с execution: {relative}")
            entries.append({"run_id": run_id, "canonical_relative_path": relative, "size_bytes": path.stat().st_size,
                            "sha256": sha256(path), "marker_sequence": sequence, "execution_id": by_sequence[sequence]})
    if len(entries) != expected_count or len({item["sha256"] for item in entries}) != expected_count:
        raise ValueError(f"Capture manifest требует {expected_count} уникальных hashes")
    payload = {"canonical_capture_root": "captures/", "forbidden_fallback_used": False,
               "capture_hash_count": len(entries), "capture_hashes_complete": True,
               "capture_paths_canonical": True, "capture_marker_mapping_complete": True, "captures": entries}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {**payload, "capture_manifest_sha256": sha256(output)}
