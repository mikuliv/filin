"""Детерминированная multiprocessing-оценка frozen decision policies."""
from __future__ import annotations
import argparse, hashlib, json, os, time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import joblib

_CONTEXT = None

def canonical_bytes(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=True).encode("utf-8")

def sha256(value) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()

def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load_policy_records(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8")); records = []
    for family in ("strong", "weak", "final"):
        for index, record in enumerate(payload[family]):
            records.append({"evaluation_id": f"{family}:{index:03d}:{record['policy_id']}", "family": family,
                            "ordinal": len(records), "policy_id": record["policy_id"], "parameters": record["parameters"],
                            "original": record})
    return records

def _init(root_text: str):
    global _CONTEXT
    root = Path(root_text)
    from ml.experiments.v0_3_10.pipeline import calibrated_joint
    grouped = joblib.load(root / "ml/artifacts/v0_3_10/grouped_oof.joblib")
    bundle = joblib.load(root / "ml/artifacts/v0_3_10/frozen_candidate.joblib")
    probabilities = calibrated_joint(bundle["gate_calibrator"], bundle["subtype_calibrator"],
                                     grouped["oof"]["gate_oof"], grouped["oof"]["subtype_oof"])
    _CONTEXT = (grouped, bundle, probabilities)

def _evaluate(record: dict) -> dict:
    if record.get("parameters", {}).get("__force_worker_error__"):
        raise RuntimeError("Запрошена тестовая ошибка worker")
    from ml.experiments.v0_3_10.pipeline import evidence_decisions, operational_metrics
    from ml.experiments.v0_3_10.run_nested_decision_selection import evaluate, public
    from ml.audits.v0_3_10_1.pending_semantics_audit import reconstruct_frames
    grouped, bundle, probabilities = _CONTEXT
    metrics = public(evaluate(grouped["rows"], grouped["X"], probabilities, bundle["conformal"],
                              bundle["diagnostic_support"], record["parameters"]))
    decisions = evidence_decisions(grouped["rows"], probabilities, bundle["conformal"], bundle["diagnostic_support"],
                                   grouped["X"], record["parameters"])
    diagnostic = reconstruct_frames(grouped["rows"], decisions)
    result = {"evaluation_id": record["evaluation_id"], "ordinal": record["ordinal"], "family": record["family"],
              "policy_id": record["policy_id"], "input_hash": record["input_hash"],
              "metrics": metrics, "burden_aware": diagnostic}
    result["output_hash"] = sha256(result)
    return result

def _checkpoint_path(directory: Path, evaluation_id: str) -> Path:
    return directory / f"{hashlib.sha256(evaluation_id.encode()).hexdigest()}.json"

def _read_checkpoint(path: Path, input_hash: str):
    if not path.exists(): return None
    try: payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError): return None
    if payload.get("completed") is not True or payload.get("input_hash") != input_hash: return None
    result = payload.get("result")
    return result if result and result.get("output_hash") == sha256({k: v for k, v in result.items() if k != "output_hash"}) else None

def _write_checkpoint(path: Path, result: dict):
    path.parent.mkdir(parents=True, exist_ok=True); temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps({"completed": True, "input_hash": result["input_hash"], "result": result}, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)

def evaluate_policies(root: Path, policy_path: Path, workers: int, checkpoint_dir: Path,
                      resume: bool = False, progress=None) -> dict:
    if workers < 1: raise ValueError("workers должен быть положительным")
    for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[name] = "1"
    records = load_policy_records(policy_path)
    source = {"grouped_oof": sha256_file(root / "ml/artifacts/v0_3_10/grouped_oof.joblib"),
              "candidate_artifact": sha256_file(root / "ml/artifacts/v0_3_10/frozen_candidate.joblib"),
              "candidate_grid": sha256_file(policy_path),
              "policy_implementation": sha256_file(root / "ml/decision/v0310_minimal_promotion.py"),
              "resource_profile_version": "v03101-1"}
    source_hash = sha256(source)
    for record in records: record["input_hash"] = sha256({"source": source, "evaluation_id": record["evaluation_id"], "parameters": record["parameters"]})
    results, pending, resumed = [], [], 0
    for record in records:
        checkpoint = _checkpoint_path(checkpoint_dir, record["evaluation_id"])
        cached = _read_checkpoint(checkpoint, record["input_hash"]) if resume else None
        if cached is not None: results.append(cached); resumed += 1
        else: pending.append(record)
    started = time.perf_counter(); completed_now = 0
    def accept(record, result):
        nonlocal completed_now
        _write_checkpoint(_checkpoint_path(checkpoint_dir, record["evaluation_id"]), result)
        results.append(result); completed_now += 1
        if progress: progress(completed_now + resumed, len(records))
    if workers == 1:
        _init(str(root))
        for record in pending: accept(record, _evaluate(record))
    elif pending:
        with ProcessPoolExecutor(max_workers=workers, initializer=_init, initargs=(str(root),)) as pool:
            futures = {pool.submit(_evaluate, record): record for record in pending}
            for future in as_completed(futures): accept(futures[future], future.result())
    results.sort(key=lambda item: item["ordinal"])
    ordered_hash = sha256([{k: v for k, v in result.items() if k != "output_hash"} for result in results])
    return {"workers": workers, "source_hash": source_hash, "source_hashes": source, "policy_count": len(records),
            "completed_now": completed_now, "resumed_count": resumed, "elapsed_seconds": time.perf_counter() - started,
            "canonical_output_sha256": ordered_hash, "results": results}

def main():
    parser = argparse.ArgumentParser(description="Оценить frozen policies без fit")
    parser.add_argument("--root", default="."); parser.add_argument("--policies", required=True); parser.add_argument("--workers", type=int, required=True)
    parser.add_argument("--checkpoint-dir", required=True); parser.add_argument("--resume", action="store_true")
    parser.add_argument("--chunk-size", type=int, default=1); parser.add_argument("--progress-interval-seconds", type=float, default=5)
    parser.add_argument("--resource-log"); parser.add_argument("--output", required=True); args = parser.parse_args()
    result = evaluate_policies(Path(args.root).resolve(), Path(args.policies).resolve(), args.workers, Path(args.checkpoint_dir).resolve(), args.resume)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
if __name__ == "__main__": main()

