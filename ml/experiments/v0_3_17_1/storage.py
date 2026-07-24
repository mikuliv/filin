from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
MAX_BENCHMARK_BYTES = 1 << 30


def _resolved(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()


def _throughput_mib_per_second(byte_count: int, duration_seconds: float) -> float:
    return round(byte_count / (1 << 20) / max(duration_seconds, 1e-9), 3)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


@dataclass(frozen=True)
class StorageLayout:
    workspace: Path
    runtime: Path

    @classmethod
    def from_environment(cls, environment: dict[str, str] | None = None) -> "StorageLayout":
        values = os.environ if environment is None else environment
        workspace = _resolved(values.get("FILIN_WORKSPACE", ROOT))
        runtime = _resolved(values.get("FILIN_RUNTIME_ROOT", workspace / "runtime" / "v0_3_17_1"))
        if runtime == runtime.parent:
            raise ValueError("runtime_root_must_not_be_volume_root")
        return cls(workspace=workspace, runtime=runtime)

    def path(self, role: str) -> Path:
        allowed = {
            "audit",
            "targeted_trial",
            "pcap",
            "zeek",
            "features",
            "predictions",
            "sensor",
            "connector",
            "receiver",
            "operator",
            "traces",
            "metrics",
            "bundles",
            "corruption",
            "temp",
            "cache",
        }
        if role not in allowed:
            raise KeyError(f"unknown_storage_role:{role}")
        return self.runtime / role

    def prepare(self) -> None:
        for role in (
            "audit",
            "targeted_trial",
            "pcap",
            "zeek",
            "features",
            "predictions",
            "sensor",
            "connector",
            "receiver",
            "operator",
            "traces",
            "metrics",
            "bundles",
            "corruption",
            "temp",
            "cache",
        ):
            self.path(role).mkdir(parents=True, exist_ok=True)
        (self.path("cache") / "pycache").mkdir(parents=True, exist_ok=True)
        (self.path("cache") / "pip").mkdir(parents=True, exist_ok=True)

    def process_environment(self) -> dict[str, str]:
        return {
            "FILIN_WORKSPACE": str(self.workspace),
            "FILIN_RUNTIME_ROOT": str(self.runtime),
            "TEMP": str(self.path("temp")),
            "TMP": str(self.path("temp")),
            "PYTHONPYCACHEPREFIX": str(self.path("cache") / "pycache"),
            "PIP_CACHE_DIR": str(self.path("cache") / "pip"),
        }

    def sanitized_profile(self) -> dict[str, Any]:
        return {
            "schema_version": "v03171_storage_layout_v1",
            "workspace_token": "${FILIN_WORKSPACE}",
            "runtime_token": "${FILIN_RUNTIME_ROOT}",
            "roles": {
                role: f"${{FILIN_RUNTIME_ROOT}}/{role}"
                for role in (
                    "audit",
                    "targeted_trial",
                    "pcap",
                    "zeek",
                    "features",
                    "predictions",
                    "sensor",
                    "connector",
                    "receiver",
                    "operator",
                    "traces",
                    "metrics",
                    "bundles",
                    "corruption",
                    "temp",
                    "cache",
                )
            },
            "global_temp_modified": False,
            "global_docker_data_root_modified": False,
        }


def run_storage_benchmark(layout: StorageLayout, *, max_bytes: int = 128 << 20) -> dict[str, Any]:
    if max_bytes <= 0 or max_bytes > MAX_BENCHMARK_BYTES:
        raise ValueError("benchmark_size_out_of_bounds")
    layout.prepare()
    benchmark_root = layout.path("temp") / "storage-benchmark-v03171"
    if benchmark_root.exists():
        raise FileExistsError("benchmark_workspace_already_exists")
    benchmark_root.mkdir(parents=True)
    sequential = benchmark_root / "sequential.bin"
    sync_file = benchmark_root / "sync-writes.bin"
    database = benchmark_root / "transactions.sqlite"
    small_root = benchmark_root / "small-files"
    block = bytes((index % 251 for index in range(1 << 20)))
    try:
        started = time.perf_counter()
        with sequential.open("wb", buffering=0) as handle:
            remaining = max_bytes
            while remaining:
                chunk = block[: min(len(block), remaining)]
                handle.write(chunk)
                remaining -= len(chunk)
            os.fsync(handle.fileno())
        sequential_write_seconds = time.perf_counter() - started

        started = time.perf_counter()
        sequential_digest = hashlib.sha256()
        with sequential.open("rb", buffering=0) as handle:
            while chunk := handle.read(1 << 20):
                sequential_digest.update(chunk)
        sequential_read_seconds = time.perf_counter() - started

        sync_write_count = 256
        sync_payload = b"S" * 4096
        started = time.perf_counter()
        with sync_file.open("wb", buffering=0) as handle:
            for _ in range(sync_write_count):
                handle.write(sync_payload)
                os.fsync(handle.fileno())
        sync_write_seconds = time.perf_counter() - started

        connection = sqlite3.connect(database)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("CREATE TABLE samples(id INTEGER PRIMARY KEY, payload BLOB NOT NULL)")
        transaction_count = 250
        started = time.perf_counter()
        for index in range(transaction_count):
            connection.execute("INSERT INTO samples(payload) VALUES (?)", (f"sample-{index}".encode(),))
            connection.commit()
        sqlite_transaction_seconds = time.perf_counter() - started
        started = time.perf_counter()
        checkpoint_row = connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        sqlite_checkpoint_seconds = time.perf_counter() - started
        connection.close()

        small_root.mkdir()
        small_file_count = 1000
        started = time.perf_counter()
        small_digest = hashlib.sha256()
        for index in range(small_file_count):
            payload = hashlib.sha256(f"v03171-{index}".encode()).digest() * 32
            path = small_root / f"{index:05d}.bin"
            path.write_bytes(payload)
            small_digest.update(path.read_bytes())
        small_file_seconds = time.perf_counter() - started

        report = {
            "schema_version": "v03171_storage_benchmark_v1",
            "stage": "v0.3.17.1",
            "storage_profile_id": "samsung_860_evo_ntfs_v03171",
            "benchmark_scope": "project_scoped_non_product_metric",
            "prospective_ssd_profile": True,
            "direct_hdd_comparison_performed": False,
            "maximum_temporary_bytes": MAX_BENCHMARK_BYTES,
            "temporary_bytes_requested": max_bytes,
            "sequential_write_mib_per_second": _throughput_mib_per_second(
                max_bytes, sequential_write_seconds
            ),
            "sequential_read_mib_per_second": _throughput_mib_per_second(
                max_bytes, sequential_read_seconds
            ),
            "sequential_sha256": sequential_digest.hexdigest(),
            "sync_write_count": sync_write_count,
            "sync_writes_per_second": round(sync_write_count / max(sync_write_seconds, 1e-9), 3),
            "sqlite_transaction_count": transaction_count,
            "sqlite_transactions_per_second": round(
                transaction_count / max(sqlite_transaction_seconds, 1e-9), 3
            ),
            "sqlite_wal_checkpoint_seconds": round(sqlite_checkpoint_seconds, 6),
            "sqlite_wal_checkpoint_result": list(checkpoint_row or ()),
            "small_file_count": small_file_count,
            "small_files_per_second": round(small_file_count / max(small_file_seconds, 1e-9), 3),
            "small_file_aggregate_sha256": small_digest.hexdigest(),
            "temporary_artifacts_removed": True,
        }
    finally:
        shutil.rmtree(benchmark_root, ignore_errors=False)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-bytes", type=int, default=128 << 20)
    args = parser.parse_args()
    layout = StorageLayout.from_environment()
    report = run_storage_benchmark(layout, max_bytes=args.max_bytes)
    _write_json(args.output, report)


if __name__ == "__main__":
    main()

