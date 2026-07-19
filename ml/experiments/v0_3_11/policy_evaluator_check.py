"""Проверка детерминизма burden-aware evaluator при 1 и 8 workers."""
from __future__ import annotations

import hashlib
import json
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import joblib
import pandas as pd

from ml.experiments.v0_3_11.nested_selection import evaluate


def _canonical(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _run_one(payload: tuple[list[dict], object, object, dict]) -> dict:
    rows, probabilities, conformal, parameters = payload
    result = evaluate(pd.DataFrame(rows), probabilities, conformal, parameters)
    result.pop("decisions", None)
    return result


def check(grouped_artifact: Path, policy_candidates: Path, output: Path) -> dict:
    grouped = joblib.load(grouped_artifact)
    candidates = json.loads(policy_candidates.read_text(encoding="utf-8"))
    parameters = [item["parameters"] for item in candidates[:12]]
    if len(parameters) != 12:
        raise RuntimeError("Для environment check требуется ровно 12 policy candidates")
    rows = grouped["rows"].to_dict("records")
    payloads = [(rows, grouped["probabilities"], grouped["oof"].get("conformal"), p) for p in parameters]

    # В старом grouped artifact conformal хранится отдельно не всегда: восстанавливаем
    # его из candidate bundle вызывающей стороной через дополнительное поле.
    if payloads[0][2] is None:
        conformal = grouped.get("conformal")
        if conformal is None:
            raise RuntimeError("Grouped artifact не содержит frozen conformal evaluator")
        payloads = [(rows, grouped["probabilities"], conformal, p) for p in parameters]

    started = time.perf_counter()
    serial = [_run_one(item) for item in payloads]
    serial_seconds = time.perf_counter() - started
    started = time.perf_counter()
    with ProcessPoolExecutor(max_workers=8) as pool:
        parallel = list(pool.map(_run_one, payloads))
    parallel_seconds = time.perf_counter() - started
    serial_hashes = [_canonical(item) for item in serial]
    parallel_hashes = [_canonical(item) for item in parallel]
    report = {
        "candidate_count": 12,
        "serial_workers": 1,
        "parallel_workers": 8,
        "serial_seconds": serial_seconds,
        "parallel_seconds": parallel_seconds,
        "speedup": serial_seconds / max(parallel_seconds, 1e-9),
        "serial_hashes": serial_hashes,
        "parallel_hashes": parallel_hashes,
        "policy_parallel_equivalence_passed": serial_hashes == parallel_hashes,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if not report["policy_parallel_equivalence_passed"]:
        raise RuntimeError("Результаты policy evaluator различаются для workers=1 и workers=8")
    return report
