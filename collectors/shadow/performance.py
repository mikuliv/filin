from __future__ import annotations

import os
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import psutil

from .canonical import canonical_bytes
from .integrated_exporter import IntegratedPassiveExporter
from .integrated_sink import LocalIdempotentSink
from .schema_validator import validate


def _percentile(values: list[float], p: float) -> float:
    rows = sorted(values)
    return rows[min(len(rows) - 1, int((len(rows) - 1) * p))]


class ResourceMonitor:
    def __init__(self, interval: float = 0.005):
        self.interval = interval
        self.samples: list[dict] = []
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        process = psutil.Process(os.getpid())
        process.cpu_percent(None)
        while not self.stop_event.wait(self.interval):
            self.samples.append({"cpu": process.cpu_percent(None), "rss_mb": process.memory_info().rss / 2**20})

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_args):
        self.stop_event.set()
        self.thread.join()


def run_profile(events: list[dict], root: Path, *, workers: int, batch_size: int, repetitions: int = 3) -> dict:
    runs = []
    for repetition in range(repetitions):
        run_root = root / f"w{workers}-b{batch_size}-r{repetition}"
        sink = LocalIdempotentSink()
        exporter = IntegratedPassiveExporter(sink, run_root, batch_size=batch_size, rate=1_000_000)
        validation_ms = []
        worker_ids = set()
        barrier = threading.Barrier(workers) if workers > 1 else None

        def prepare(event):
            started = time.perf_counter()
            worker_ids.add(threading.get_ident())
            if barrier and len(worker_ids) <= workers:
                try:
                    barrier.wait(timeout=1)
                except threading.BrokenBarrierError:
                    pass
            validate(event)
            canonical_bytes(event)
            return event, (time.perf_counter() - started) * 1000

        started = time.perf_counter()
        with ResourceMonitor() as monitor:
            with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="passive-export") as pool:
                prepared = list(pool.map(prepare, events))
            for event, latency in prepared:
                validation_ms.append(latency)
                exporter.submit(event)
            exporter.drain()
        elapsed = time.perf_counter() - started
        report = exporter.report()
        cpu = [row["cpu"] for row in monitor.samples] or [0.0]
        rss = [row["rss_mb"] for row in monitor.samples] or [psutil.Process().memory_info().rss / 2**20]
        runs.append({
            "elapsed_seconds": elapsed,
            "throughput_events_per_second": len(events) / elapsed,
            "schema_validation_p95_ms": _percentile(validation_ms, .95),
            "cpu_average_percent": statistics.mean(cpu),
            "cpu_p95_percent": _percentile(cpu, .95),
            "peak_rss_mb": max(rss),
            "sample_count": len(monitor.samples),
            "actual_worker_thread_count": len(worker_ids),
            "batch_calls": sink.batch_calls,
            "real_batch_calls": report["metrics"].get("real_batch_calls", 0),
            "queue_peak": report["queue_peak"],
            "spool_peak_bytes": report["spool_peak_bytes"],
            "unaccounted_drop_count": report["reconciliation"]["unaccounted_drop_count"],
            "sink_unique_events": len(sink.events),
        })
    return {
        "workers": workers,
        "batch_size": batch_size,
        "repetitions": repetitions,
        "runs": runs,
        "median_throughput_events_per_second": statistics.median(row["throughput_events_per_second"] for row in runs),
        "p95_cpu_percent": max(row["cpu_p95_percent"] for row in runs),
        "peak_rss_mb": max(row["peak_rss_mb"] for row in runs),
        "real_worker_pool": all(row["actual_worker_thread_count"] == workers for row in runs),
        "real_batch_delivery": batch_size == 1 or all(row["real_batch_calls"] > 0 for row in runs),
        "reconciled": all(row["unaccounted_drop_count"] == 0 and row["sink_unique_events"] == len(events) for row in runs),
    }
