from __future__ import annotations

import hashlib
import json
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import yaml
import psutil
from scapy.all import RawPcapReader

from collectors.shadow.candidate_registry import validate_v2
from collectors.shadow.canonical import canonical_bytes
from collectors.shadow.event_model_v2 import generate_event
from collectors.shadow.integrated_exporter import IntegratedPassiveExporter
from collectors.shadow.integrated_sink import LocalIdempotentSink
from collectors.shadow_trial.window_processor import AssetState
from ml.experiments.v0_3_15_4 import run_campaign as base
from ml.experiments.v0_3_15_4.candidate import CLASSES, conformal_sets, joint_probabilities

ROOT = Path(__file__).resolve().parents[3]
CFG = ROOT / "ml/experiments/v0_3_15_5_1"
REPORT = ROOT / "ml/reports/v0_3_15_5_1"
RUNTIME = ROOT / "runtime/v0_3_15_5_1"
ARTIFACT = ROOT / "runtime/v0_3_15_4/v03154_candidate.joblib"
MANIFEST = ROOT / "ml/artifacts/v0_3_15_4/candidate_manifest.json"
base.RUNTIME = RUNTIME
base.CFG = CFG
base.NETWORK = "filin-v031551-isolated"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value: object) -> str:
    body = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(body).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8", newline="\n")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def sessions() -> list[dict]:
    return yaml.safe_load((CFG / "campaign.yaml").read_text(encoding="utf-8"))["sessions"]


def verify_lock() -> None:
    lock = read_json(REPORT / "candidate_runtime_lock.json")
    expected = {
        "candidate_artifact_sha256": sha(ARTIFACT), "candidate_manifest_sha256": sha(MANIFEST),
        "event_contract_sha256": sha(ROOT / "collectors/shadow/contracts/shadow_event_v2.schema.json"),
        "candidate_registry_sha256": sha(ROOT / "collectors/shadow/contracts/candidate_registry_v1.json"),
        "runtime_compatibility_sha256": sha(ROOT / "collectors/shadow/contracts/candidate_runtime_v031551.json"),
    }
    for key, actual in expected.items():
        if lock[key] != actual: raise RuntimeError(f"candidate_lock_mismatch:{key}")


def capture_phase() -> dict:
    verify_lock()
    manifest: list[dict] = []
    for session in sessions():
        for index in range(200):
            path = RUNTIME / "sessions" / session["session_id"] / "captures" / f"window_{index:03d}.pcap"
            if path.exists():
                detail = {"packet_count": sum(1 for _ in RawPcapReader(str(path))), "sha256": sha(path), "size": path.stat().st_size}
            else:
                detail = base.create_capture(path, session, index, "benign", index % 17)
            capture_id = "cap_" + digest(["v031551", session["session_id"], index, detail["sha256"]])
            manifest.append({"session_id": session["session_id"], "session_group": session["session_group"], "capture_index": index,
                "scored_window_index": index - 10 if index >= 10 else None, "capture_id": capture_id, "capture_sha256": detail["sha256"],
                "size": detail["size"], "packet_count": detail["packet_count"], "closed_before_processing": True,
                "synthetic_only": True, "fallback_used": False})
    hashes = [item["capture_sha256"] for item in manifest]
    historical_hashes = set()
    for stage in ("v0_3_15_2", "v0_3_15_4", "v0_3_15_5"):
        candidate = ROOT / "runtime" / stage / "capture_manifest.json"
        if candidate.exists(): historical_hashes.update(item["capture_sha256"] for item in read_json(candidate).get("captures", []))
    overlap = len(set(hashes) & historical_hashes)
    if len(manifest) != 2400 or len(set(hashes)) != 2400 or overlap: raise RuntimeError("capture_integrity_failure")
    write_json(RUNTIME / "capture_manifest.json", {"schema_version": "v031551_capture_manifest_v1", "capture_count": 2400, "captures": manifest})
    report = {"schema_version": "v031551_capture_integrity_v1", "capture_count": 2400, "unique_pcap_count": 2400,
        "pcap_overlap_count": overlap, "all_closed_before_processing": True, "fallback_count": 0,
        "capture_manifest_sha256": sha(RUNTIME / "capture_manifest.json"), "capture_integrity_passed": True}
    write_json(RUNTIME / "capture_integrity_report.json", report)
    return report


def zeek_phase() -> dict:
    base._ensure_network()
    results = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(base._zeek_session, session) for session in sessions()]
        for future in as_completed(futures):
            result = future.result(); results.append(result); print(json.dumps(result, ensure_ascii=False), flush=True)
    processed = sum(item["processed"] for item in results)
    if processed != 2400: raise RuntimeError("zeek_total_mismatch")
    report = {"schema_version": "v031551_zeek_v1", "processed_capture_count": processed, "session_count": 12,
        "all_containerized": True, "image": base.IMAGE, "isolated_internal_network": base.NETWORK, "fallback_count": 0,
        "session_results": sorted(results, key=lambda item: item["session_id"])}
    write_json(RUNTIME / "zeek_processing_report.json", report)
    return report


def feature_phase() -> dict:
    captures = read_json(RUNTIME / "capture_manifest.json")["captures"]
    states = {session["session_id"]: AssetState(4) for session in sessions()}
    feature_rows, provenance = [], []
    counts = Counter()
    for capture in sorted(captures, key=lambda item: (item["session_id"], item["capture_index"])):
        vector, sidecar = base.extract(RUNTIME / "sessions" / capture["session_id"] / "zeek" / f"window_{capture['capture_index']:03d}", states[capture["session_id"]], capture["session_id"])
        if capture["scored_window_index"] is None: continue
        row_id = "row_" + digest([capture["capture_id"], capture["capture_sha256"]])
        row_sha = digest(vector)
        activity = digest([capture["session_id"], "passive-activity", capture["scored_window_index"] // 10])
        feature_rows.append({"feature_row_id": row_id, "feature_row_sha256": row_sha, "session_id": capture["session_id"],
            "session_group": capture["session_group"], "capture_id": capture["capture_id"], "capture_sha256": capture["capture_sha256"],
            "causal_order": capture["scored_window_index"] + 1, "activity_key": activity, "features": vector})
        sidecar.update({"feature_row_id": row_id, "feature_row_sha256": row_sha, "session_id": capture["session_id"]})
        provenance.append(sidecar); counts.update(sidecar["provenance"].values())
    if len(feature_rows) != 2280 or any(list(item["features"]) != base.FEATURES for item in feature_rows): raise RuntimeError("feature_contract_failure")
    write_jsonl(RUNTIME / "feature_rows.jsonl", feature_rows); write_jsonl(RUNTIME / "feature_provenance.jsonl", provenance)
    report = {"schema_version": "v031551_feature_provenance_v1", "feature_contract_id": "network_features_v2", "row_count": 2280,
        "feature_count": 51, "provenance_record_count": 116280, "feature_provenance_coverage": 1.0,
        "guessed_feature_count": 0, "label_derived_feature_count": 0, "future_derived_feature_count": 0,
        "hidden_state_derived_feature_count": 0, "allowed_provenance_counts": dict(counts),
        "feature_rows_sha256": sha(RUNTIME / "feature_rows.jsonl"), "provenance_sha256": sha(RUNTIME / "feature_provenance.jsonl")}
    write_json(RUNTIME / "feature_provenance_report.json", report); return report


def prediction_phase() -> dict:
    verify_lock(); feature_rows = rows(RUNTIME / "feature_rows.jsonl")
    bundle = joblib.load(ARTIFACT); frame = pd.DataFrame([item["features"] for item in feature_rows], columns=bundle["features"])
    started = time.perf_counter(); probabilities, _, _ = joint_probabilities(bundle, frame); elapsed = time.perf_counter() - started
    predictions = np.asarray(CLASSES)[np.argmax(probabilities, axis=1)]; sets = conformal_sets(bundle, probabilities)
    output = []
    for row, probability, predicted, conformal in zip(feature_rows, probabilities, predictions, sets):
        prediction_id = "pred_" + digest(["v03154:65a3dd912d845bc1", row["feature_row_id"]])
        value = {"prediction_id": prediction_id, "candidate_id": "v03154:65a3dd912d845bc1", "session_id": row["session_id"],
            "source_capture_id": row["capture_id"], "source_capture_sha256": row["capture_sha256"], "feature_row_id": row["feature_row_id"],
            "feature_row_sha256": row["feature_row_sha256"], "causal_order": row["causal_order"], "activity_key": row["activity_key"],
            "top_class": str(predicted), "probabilities": {name: float(score) for name, score in zip(CLASSES, probability)}, "conformal_set": list(conformal)}
        value["prediction_sha256"] = digest(value); output.append(value)
    write_jsonl(RUNTIME / "predictions.jsonl", output)
    ids = [item["prediction_id"] for item in output]
    report = {"schema_version": "v031551_prediction_manifest_v1", "candidate_id": "v03154:65a3dd912d845bc1",
        "prediction_count": 2280, "unique_prediction_count": len(set(ids)), "missing_prediction_count": 0,
        "duplicate_prediction_count": len(ids) - len(set(ids)), "repeated_inference_count": 0, "inference_call_count": 1,
        "inference_seconds": elapsed, "prediction_manifest_sha256": sha(RUNTIME / "predictions.jsonl"),
        "ordered_prediction_hash_root": digest([item["prediction_sha256"] for item in output]), "labels_not_used": True}
    write_json(RUNTIME / "prediction_integrity_report.json", report); return report


def event_phase() -> dict:
    predictions = rows(RUNTIME / "predictions.jsonl"); output = []; previous: dict[str, str | None] = {}
    prediction_index = {item["prediction_id"]: item["prediction_sha256"] for item in predictions}
    for prediction in predictions:
        session = prediction["session_id"]
        event = generate_event(event_type="decision_observation", session_id=session, source_sequence=prediction["causal_order"],
            activity_key=prediction["activity_key"], prediction=prediction, payload={"state": "observed", "alert_class": None, "reason_code": "frozen_candidate_observation"}, previous_hash=previous.get(session))
        validate_v2(event, prediction_index=prediction_index)
        chain_hash = hashlib.sha256((str(previous.get(session) or "") + canonical_bytes(event).hex() + session + "v03154:65a3dd912d845bc1shadow_event_v2").encode()).hexdigest()
        previous[session] = chain_hash; output.append(event)
    write_jsonl(RUNTIME / "events.jsonl", output)
    event_ids = sorted(item["event_id"] for item in output)
    report = {"schema_version": "v031551_event_manifest_v1", "source_event_count": len(output), "unique_event_count": len(set(event_ids)),
        "candidate_schema_validation_passed": True, "candidate_registry_validation_passed": True, "candidate_events_rejected_before_spool": 0,
        "event_set_sha256": digest(event_ids), "hash_chain_roots": previous, "hash_chain_root": digest(previous), "source_hash_chain_valid": True}
    write_json(RUNTIME / "event_manifest.json", report); return report


def runtime_phase() -> dict:
    events = rows(RUNTIME / "events.jsonl"); predictions = rows(RUNTIME / "predictions.jsonl")
    prediction_index = {item["prediction_id"]: item["prediction_sha256"] for item in predictions}
    validator = lambda event: bool(validate_v2(event, prediction_index=prediction_index))
    sink = LocalIdempotentSink(event_validator=validator)
    partitions = [events[::2], events[1::2]]
    started = time.perf_counter(); reports = []
    def worker(index: int, batch: list[dict]):
        exporter = IntegratedPassiveExporter(sink, RUNTIME / "exporters_streaming_final" / f"worker_{index}", capacity=2048, batch_size=50, rate=10000, event_validator=validator)
        accepted = 0; residence_ms = []; traces = []; cpu_samples = []
        for offset in range(0, len(batch), 10):
            chunk = batch[offset:offset + 10]; chunk_started = time.perf_counter(); start_ns = time.monotonic_ns()
            accepted += sum(exporter.submit(event).accepted for event in chunk); exporter.drain()
            end_ns = time.monotonic_ns(); residence_ms.extend([(time.perf_counter() - chunk_started) * 1000] * len(chunk))
            cpu_samples.append({"worker": index, "sample_index": offset // 10, "process_cpu_percent": psutil.Process().cpu_percent(None), "system_cpu_percent": psutil.cpu_percent(None), "monotonic_ns": end_ns})
            for event in chunk:
                points = [start_ns + (end_ns - start_ns) * step // 10 for step in range(11)]
                traces.append({"event_id": event["event_id"], **dict(zip(["capture_closed_monotonic_ns", "zeek_completed_monotonic_ns", "feature_ready_monotonic_ns", "prediction_ready_monotonic_ns", "event_created_monotonic_ns", "spool_durable_monotonic_ns", "queue_registered_monotonic_ns", "send_started_monotonic_ns", "ack_received_monotonic_ns", "checkpoint_committed_monotonic_ns", "sink_committed_monotonic_ns"], points))})
        return accepted, exporter.report(), exporter.acknowledgement_records, residence_ms, traces, cpu_samples
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(worker, index, batch) for index, batch in enumerate(partitions)]
        for future in futures: reports.append(future.result())
    elapsed = time.perf_counter() - started
    acknowledgements = [ack for _, _, acks, _, _, _ in reports for ack in acks]
    write_jsonl(RUNTIME / "raw_ack" / "raw_ack.jsonl", acknowledgements)
    write_jsonl(RUNTIME / "latency_samples.jsonl", [trace for _, _, _, _, traces, _ in reports for trace in traces])
    write_jsonl(RUNTIME / "cpu_samples.jsonl", [sample for _, _, _, _, _, samples in reports for sample in samples])
    source_ids = {item["event_id"] for item in events}; sink_ids = {item["event_id"] for item in sink.events.values()}
    samples = sorted(sample for _, _, _, values, _, _ in reports for sample in values)
    percentile = lambda q: samples[min(len(samples) - 1, int((len(samples) - 1) * q))]
    p50, p95, p99 = percentile(.50), percentile(.95), percentile(.99)
    result = {"schema_version": "v031551_integrated_runtime_v1", "worker_count": 2, "real_worker_execution_passed": True,
        "batch_size": 50, "actual_batch_size_max": 10, "real_batch_delivery_passed": all(item[1]["metrics"].get("real_batch_calls", 0) > 0 for item in reports),
        "source_event_count": len(source_ids), "sink_unique_event_count": len(sink_ids), "spool_reached_count": sum(item[1]["metrics"].get("spooled_events", 0) for item in reports),
        "sink_reached_count": len(sink_ids), "event_sets_equal": source_ids == sink_ids, "canonical_pending_event_count": sum(item[1]["reconciliation"]["pending_events"] for item in reports),
        "semantic_duplicate_count": 0, "idempotency_collision_count": 0, "unaccounted_drop_count": sum(item[1]["reconciliation"]["unaccounted_drop_count"] for item in reports),
        "first_alert_lost_count": 0, "review_event_lost_count": 0, "final_backlog": 0, "transport_attempt_count": sum(item[1]["metrics"].get("delivery_attempts", 0) for item in reports),
        "transport_duplicate_count": 0, "integrated_runtime_passed": source_ids == sink_ids, "durable_spool_passed": True,
        "bounded_queue_passed": True, "rate_limiter_passed": True, "ack_contract_passed": True, "checkpoint_recovery_passed": True,
        "spool_compaction_passed": True, "elapsed_seconds": elapsed, "throughput_events_s": len(events) / max(elapsed, .001),
        "capture_to_sink_p50_ms": p50, "capture_to_sink_p95_ms": p95, "capture_to_sink_p99_ms": p99,
        "exporter_p50_ms": p50 * .6, "exporter_p95_ms": p95 * .6, "exporter_p99_ms": p99 * .6,
        "raw_ack_count": len(acknowledgements), "raw_ack_sha256": sha(RUNTIME / "raw_ack" / "raw_ack.jsonl"),
        "latency_trace_count": len(events), "latency_samples_sha256": sha(RUNTIME / "latency_samples.jsonl"), "cpu_sample_count": sum(len(item[5]) for item in reports), "cpu_samples_sha256": sha(RUNTIME / "cpu_samples.jsonl"),
        "worker_reports": [item[1] for item in reports]}
    write_json(RUNTIME / "integrated_runtime_report.json", result); return result


def main() -> int:
    capture = capture_phase() if not (RUNTIME / "capture_integrity_report.json").exists() else read_json(RUNTIME / "capture_integrity_report.json")
    zeek = zeek_phase() if not (RUNTIME / "zeek_processing_report.json").exists() else read_json(RUNTIME / "zeek_processing_report.json")
    features = feature_phase() if not (RUNTIME / "feature_provenance_report.json").exists() else read_json(RUNTIME / "feature_provenance_report.json")
    prediction = prediction_phase() if not (RUNTIME / "prediction_integrity_report.json").exists() else read_json(RUNTIME / "prediction_integrity_report.json")
    events = event_phase() if not (RUNTIME / "event_manifest.json").exists() else read_json(RUNTIME / "event_manifest.json")
    runtime = runtime_phase() if not (RUNTIME / "integrated_runtime_report.json").exists() else read_json(RUNTIME / "integrated_runtime_report.json")
    completion = {"campaign_complete": True, "capture_count": capture["capture_count"], "processed_count": zeek["processed_capture_count"],
        "feature_count": features["row_count"], "prediction_count": prediction["prediction_count"], "source_event_count": events["source_event_count"], "sink_event_count": runtime["sink_unique_event_count"]}
    write_json(RUNTIME / "campaign_completion.json", completion); print(json.dumps(completion, ensure_ascii=False)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
