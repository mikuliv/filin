"""Controlled benchmark существующего frozen policy evaluator."""
from __future__ import annotations
import argparse, json, os, time
from pathlib import Path
import psutil

from ml.performance.parallel_policy_evaluator import evaluate_policies
from ml.performance.resource_monitor import ResourceMonitor


def benchmark(root: Path, policies: Path, workers: int, reports: Path, resume: bool = False) -> dict:
    available = psutil.virtual_memory().available / 1024**3
    if available < 8:
        raise RuntimeError("Benchmark остановлен: свободно менее 8 ГБ RAM")
    before_swap = psutil.swap_memory().used
    trace = reports / f"resource_trace_workers_{workers}.jsonl"
    monitor = ResourceMonitor(os.getpid(), trace, interval=1.0).start()
    started = time.perf_counter()
    try:
        evaluation = evaluate_policies(root, policies, workers, reports / f"checkpoints_workers_{workers}", resume=resume)
    finally:
        resources = monitor.stop()
    elapsed = time.perf_counter() - started
    if psutil.swap_memory().used - before_swap > 1024**3:
        raise RuntimeError("Benchmark остановлен: swap вырос более чем на 1 ГБ")
    return {"workers": workers, "completed_policies": evaluation["policy_count"],
            "elapsed_seconds": elapsed, "policies_per_second": evaluation["policy_count"] / elapsed,
            "canonical_output_sha256": evaluation["canonical_output_sha256"],
            "source_hash": evaluation["source_hash"], "completed_now": evaluation["completed_now"],
            "resumed_count": evaluation["resumed_count"], "resources": resources,
            "evaluation": evaluation}


def main():
    p=argparse.ArgumentParser(); p.add_argument("--root", default="."); p.add_argument("--policies", required=True)
    p.add_argument("--workers", type=int, required=True); p.add_argument("--reports", required=True)
    p.add_argument("--resume", action="store_true"); p.add_argument("--output", required=True); a=p.parse_args()
    value=benchmark(Path(a.root).resolve(), Path(a.policies).resolve(), a.workers, Path(a.reports).resolve(), a.resume)
    Path(a.output).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__": main()
