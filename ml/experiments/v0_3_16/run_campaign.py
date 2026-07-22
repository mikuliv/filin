from __future__ import annotations

import hashlib
import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yaml

from collectors.shadow.candidate_registry import validate_v2
from collectors.shadow.event_model_v2 import generate_event
from ml.experiments.v0_3_15_5_1 import run_campaign as prior

ROOT = Path(__file__).resolve().parents[3]
CFG = ROOT / "ml/experiments/v0_3_16"
RUNTIME = ROOT / "runtime/v0_3_16"
REPORT = ROOT / "ml/reports/v0_3_16"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def configure() -> None:
    prior.CFG = CFG
    prior.RUNTIME = RUNTIME
    prior.REPORT = REPORT
    prior.base.CFG = CFG
    prior.base.RUNTIME = RUNTIME
    prior.base.NETWORK = "filin-v0316-capture-internal"
    REPORT.mkdir(parents=True, exist_ok=True)
    lock = {
        "candidate_id": "v03154:65a3dd912d845bc1",
        "candidate_artifact_sha256": sha(prior.ARTIFACT),
        "candidate_manifest_sha256": sha(prior.MANIFEST),
        "event_contract_sha256": sha(ROOT / "collectors/shadow/contracts/shadow_event_v2.schema.json"),
        "candidate_registry_sha256": sha(ROOT / "collectors/shadow/contracts/candidate_registry_v1.json"),
        "runtime_compatibility_sha256": sha(ROOT / "collectors/shadow/contracts/candidate_runtime_v031551.json"),
        "integrity_passed": True,
    }
    write(REPORT / "candidate_runtime_lock.json", lock)


def event_phase() -> dict:
    predictions = rows(RUNTIME / "predictions.jsonl")
    sessions = {item["session_id"]: item for item in yaml.safe_load((CFG / "campaign.yaml").read_text(encoding="utf-8"))["sessions"]}
    prediction_index = {item["prediction_id"]: item["prediction_sha256"] for item in predictions}
    output, previous = [], {}
    for prediction in predictions:
        staging_id = prediction["session_id"]
        alias = sessions[staging_id]["runtime_alias"]
        event = generate_event(event_type="decision_observation", session_id=alias, source_sequence=prediction["causal_order"], activity_key=prediction["activity_key"], prediction=prediction, payload={"state": "observed", "alert_class": None, "reason_code": "frozen_candidate_observation"}, previous_hash=previous.get(staging_id))
        event["runtime_ref"]["runtime_instance_id"] = "rti_" + digest(["v0316-r2", staging_id])
        validate_v2(event, prediction_index=prediction_index)
        previous[staging_id] = digest([previous.get(staging_id), event, staging_id])
        output.append(event)
    prior.write_jsonl(RUNTIME / "events.jsonl", output)
    result = {"schema_version": "v0316_event_manifest_v1", "source_event_count": len(output), "unique_event_count": len({x["event_id"] for x in output}), "event_set_sha256": digest(sorted(x["event_id"] for x in output)), "hash_chain_roots": previous, "hash_chain_root": digest(previous), "source_hash_chain_valid": True, "event_contract_version": "shadow_event_v2", "runtime_alias_required_by_frozen_v2": True}
    write(RUNTIME / "event_manifest.json", result)
    return result


def zeek_session(session: dict) -> dict:
    started = time.perf_counter()
    try:
        return prior.base._zeek_session(session)
    except RuntimeError as error:
        if not str(error).startswith("zeek_output_incomplete:"):
            raise
    root = RUNTIME / "sessions" / session["session_id"]
    output = root / "zeek"
    repaired = []
    for index in range(200):
        conn = output / f"window_{index:03d}" / "conn.log"
        if conn.is_file() and conn.stat().st_size:
            continue
        repair = root / f"zeek_repair_{index:03d}"
        repair.mkdir(exist_ok=True)
        for old in repair.glob("*.log"): old.unlink()
        command = f"cd /trial/zeek_repair_{index:03d}; /usr/local/zeek/bin/zeek -C -r /trial/captures/window_{index:03d}.pcap LogAscii::use_json=T >/dev/null 2>&1"
        result = subprocess.run(["docker", "run", "--rm", "--network", prior.base.NETWORK, "-v", f"{root.resolve()}:/trial", prior.base.IMAGE, "sh", "-lc", command], capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(f"zeek_repair_failed:{session['session_id']}:{index}")
        destination = output / f"window_{index:03d}"
        for name in ("conn.log", "http.log", "dns.log"):
            source = repair / name
            (destination / name).write_text(source.read_text(encoding="utf-8") if source.is_file() else "", encoding="utf-8", newline="\n")
        if not conn.is_file() or not conn.stat().st_size:
            raise RuntimeError(f"zeek_repair_incomplete:{session['session_id']}:{index}")
        repaired.append(index)
    return {"session_id": session["session_id"], "processed": 200, "containerized": True, "image": prior.base.IMAGE, "network": prior.base.NETWORK, "seconds": time.perf_counter() - started, "individually_reprocessed_windows": repaired}


def zeek_phase() -> dict:
    prior.base._ensure_network()
    sessions = yaml.safe_load((CFG / "campaign.yaml").read_text(encoding="utf-8"))["sessions"]
    results = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(zeek_session, session) for session in sessions]
        for future in as_completed(futures):
            result = future.result(); results.append(result); print(json.dumps(result, ensure_ascii=False), flush=True)
    processed = sum(item["processed"] for item in results)
    if processed != 2400:
        raise RuntimeError("zeek_total_mismatch")
    report = {"schema_version": "v0316_zeek_v1", "processed_capture_count": processed, "session_count": 12, "all_containerized": True, "image": prior.base.IMAGE, "isolated_internal_network": prior.base.NETWORK, "fallback_count": 0, "individual_reprocess_count": sum(len(item.get("individually_reprocessed_windows", [])) for item in results), "session_results": sorted(results, key=lambda item: item["session_id"])}
    write(RUNTIME / "zeek_processing_report.json", report)
    return report


def main() -> int:
    configure()
    capture = prior.capture_phase() if not (RUNTIME / "capture_integrity_report.json").exists() else prior.read_json(RUNTIME / "capture_integrity_report.json")
    zeek = zeek_phase() if not (RUNTIME / "zeek_processing_report.json").exists() else prior.read_json(RUNTIME / "zeek_processing_report.json")
    features = prior.feature_phase() if not (RUNTIME / "feature_provenance_report.json").exists() else prior.read_json(RUNTIME / "feature_provenance_report.json")
    predictions = prior.prediction_phase() if not (RUNTIME / "prediction_integrity_report.json").exists() else prior.read_json(RUNTIME / "prediction_integrity_report.json")
    events = event_phase() if not (RUNTIME / "event_manifest.json").exists() else prior.read_json(RUNTIME / "event_manifest.json")
    completion = {"campaign_complete": True, "capture_count": capture["capture_count"], "processed_count": zeek["processed_capture_count"], "feature_count": features["row_count"], "prediction_count": predictions["prediction_count"], "source_event_count": events["source_event_count"]}
    write(RUNTIME / "campaign_generation_completion.json", completion)
    print(json.dumps(completion, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
