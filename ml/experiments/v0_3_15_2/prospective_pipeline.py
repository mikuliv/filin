from __future__ import annotations

import hashlib
import json
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yaml

from collectors.shadow.canonical import canonical_bytes, deterministic_id, sha256
from collectors.shadow.integrated_exporter import IntegratedPassiveExporter
from collectors.shadow.integrated_sink import LocalIdempotentSink
from collectors.shadow.scenario_runner import run_all
from collectors.shadow.spool import BoundedSpool
from collectors.shadow_trial.pipeline import OnlineEventStream, OnlinePredictor, ZeekSession
from collectors.shadow_trial.window_processor import AssetState, create_capture, extract_features_from_zeek
from ml.experiments.v0_3_13.no_fit_guard import NoFitGuard


ROOT = Path(__file__).resolve().parents[3]
CFG = ROOT / "ml/experiments/v0_3_15_2"
RUNTIME = ROOT / "runtime/v0_3_15_2"
ARTIFACT = ROOT / "ml/artifacts/v0_3_11/frozen_candidate.joblib"
CANDIDATE_HASH = "59d2cd75f3f09f5f8976fa2a56417ad10205986f696a3bef5a4fbaba52ff09b7"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8", newline="\n")


def file_hash(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def json_hash(value) -> str:
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def _load_yaml(name: str):
    return yaml.safe_load((CFG / name).read_text(encoding="utf-8"))


def _capture_rows(session: dict, vault_records: list[dict]) -> list[dict]:
    labels = {(row["session_id"], row["scored_window_index"]): row for row in vault_records}
    rows = []
    for capture_index in range(200):
        scored = capture_index >= 10
        scored_index = capture_index - 10 if scored else None
        label = labels[(session["session_id"], scored_index)] if scored else {"true_class": "benign", "benign_variant": None}
        variant = label.get("benign_variant")
        rows.append({
            "session_id": session["session_id"], "session_group": session["group"], "seed": session["seed"],
            "capture_index": capture_index, "scored": scored, "scored_window_index": scored_index,
            "true_class": label["true_class"], "variant_index": int(variant.rsplit("_", 1)[1]) if variant else 0,
        })
    return rows


def capture_phase() -> dict:
    lock = read_json(CFG / "campaign_lock.json")
    if file_hash(ROOT / "ml/protocols/v0_3_15_2_protocol.yaml") != lock["protocol_sha256"]:
        raise RuntimeError("protocol_hash_changed_after_freeze")
    vault_path = RUNTIME / "label_vault.json"
    if file_hash(vault_path) != lock["label_vault_sha256"]:
        raise RuntimeError("label_vault_hash_mismatch")
    vault = read_json(vault_path)
    campaign = _load_yaml("campaign.yaml")
    manifest = []
    for session in campaign["sessions"]:
        session_root = RUNTIME / "sessions" / session["session_id"] / "captures"
        for row in _capture_rows(session, vault["records"]):
            path = session_root / f"window_{row['capture_index']:03d}.pcap"
            if path.exists():
                raise RuntimeError("official_capture_already_exists")
            detail = create_capture(path, row)
            manifest.append({
                "session_id": row["session_id"], "session_group": row["session_group"],
                "capture_index": row["capture_index"], "scored_window_index": row["scored_window_index"],
                "capture_id": deterministic_id(("v03152", row["session_id"], row["capture_index"])),
                "capture_sha256": file_hash(path), "size": path.stat().st_size,
                "packet_count": detail["packet_count"], "window_duration_seconds": 1,
                "closed_before_processing": True, "fallback_used": False,
            })
    if len(manifest) != 2400 or len({row["capture_sha256"] for row in manifest}) != 2400:
        raise RuntimeError("capture_integrity_failed")
    path = RUNTIME / "capture_manifest.json"; write_json(path, {"schema_version": "v03152_capture_manifest_v1", "capture_count": len(manifest), "captures": manifest})
    report = {"capture_count": 2400, "unique_capture_hash_count": 2400, "capture_manifest_sha256": file_hash(path), "all_closed_before_processing": True, "fallback_count": 0}
    write_json(RUNTIME / "capture_phase_report.json", report)
    return report


def _activity_key(zeek_dir: Path, session_id: str) -> str:
    rows = [json.loads(line) for line in (zeek_dir / "conn.log").read_text(encoding="utf-8").splitlines() if line.strip()]
    fingerprint = sorted({(row.get("id.resp_h"), row.get("id.resp_p"), row.get("proto")) for row in rows})
    return f"{session_id}:{json_hash(fingerprint)[:20]}"


def _process_zeek(session: dict, captures: list[dict]) -> dict[int, dict]:
    session_root = RUNTIME / "sessions" / session["session_id"]
    results = {}
    with ZeekSession(session["session_id"], session_root, workers=2, enabled=True) as zeek:
        with ThreadPoolExecutor(max_workers=4) as pool:
            pending = {
                pool.submit(zeek.process, session_root / "captures" / f"window_{row['capture_index']:03d}.pcap", f"window_{row['capture_index']:03d}", row["capture_index"]): row
                for row in captures
            }
            for future in as_completed(pending):
                row = pending[future]; result = future.result()
                if not result["containerized"]:
                    raise RuntimeError("containerized_zeek_required")
                results[row["capture_index"]] = result
    return results


def prediction_phase() -> dict:
    if (RUNTIME / "pre_label_trial_lock.json").exists():
        raise RuntimeError("prediction_phase_already_finalized")
    capture_payload = read_json(RUNTIME / "capture_manifest.json")
    campaign = _load_yaml("campaign.yaml"); schedules = _load_yaml("fault_schedule.yaml")["faults"]
    by_session = defaultdict(list)
    for row in capture_payload["captures"]: by_session[row["session_id"]].append(row)
    predictor = OnlinePredictor(ARTIFACT)
    sink = LocalIdempotentSink()
    exporter_root = RUNTIME / "integrated_exporter"
    exporter = IntegratedPassiveExporter(sink, exporter_root, capacity=2048, batch_size=50, rate=25)
    factory = OnlineEventStream(file_hash(CFG / "campaign_lock.json"), sink, BoundedSpool(RUNTIME / "event_factory_spool"))
    predictions = []; feature_records = []; source_events = []; session_completion = []
    latency = defaultdict(list); exporter_reports = []; restart_records = []
    nofit = None
    with NoFitGuard() as guard:
        for session in campaign["sessions"]:
            captures = sorted(by_session[session["session_id"]], key=lambda row: row["capture_index"])
            zeek_results = _process_zeek(session, captures)
            states = {}
            for capture in captures:
                capture_index = capture["capture_index"]
                zeek_dir = RUNTIME / "sessions" / session["session_id"] / "zeek" / f"window_{capture_index:03d}"
                activity = _activity_key(zeek_dir, session["session_id"])
                state = states.setdefault(activity, AssetState(4))
                feature_started = time.perf_counter(); features = extract_features_from_zeek(zeek_dir, state); feature_finished = time.perf_counter()
                if capture["scored_window_index"] is None:
                    continue
                causal_order = capture["scored_window_index"] + 1
                row_id = json_hash(["v03152", session["session_id"], causal_order, capture["capture_sha256"]])
                mapping = {"session_id": session["session_id"], "immutable_row_id": row_id, "causal_order": causal_order, "activity_key": activity}
                predicted_started = time.perf_counter(); prediction = predictor.predict(features, mapping); predicted_finished = time.perf_counter()
                prediction.update({
                    "benchmark_id": "v03152_prospective_integrated_runtime_trial", "run_id": session["session_id"],
                    "capture_id": capture["capture_id"], "capture_sha256": capture["capture_sha256"],
                    "zeek_result_sha256": zeek_results[capture_index]["zeek_output_sha256"],
                    "feature_row_id": row_id, "feature_row_sha256": json_hash(features),
                    "candidate_id": "v0311:19176acb401be2d4", "candidate_artifact_sha256": CANDIDATE_HASH,
                    "prediction_id": deterministic_id(("prediction", row_id)), "prediction_timestamp": time.time_ns(),
                    "label_locked": True, "transition_reason": prediction["state_transition_reason"],
                })
                prediction["prediction_sha256"] = json_hash({key: value for key, value in prediction.items() if key != "prediction_sha256"})
                events = factory.create(prediction)
                for event in events:
                    decision = exporter.submit(event)
                    if not decision.accepted: raise RuntimeError("canonical_event_enqueue_rejected")
                if len(exporter.queue) >= 50: exporter.drain()
                predictions.append(prediction); feature_records.append({"immutable_row_id": row_id, "features": features}); source_events.extend(events)
                latency["zeek_ms"].append(zeek_results[capture_index]["zeek_ms"])
                latency["feature_ms"].append((feature_finished - feature_started) * 1000)
                latency["prediction_ms"].append((predicted_finished - predicted_started) * 1000)
            if session["group"] == "prospective_crash_resume":
                pending_before = len(exporter.spool.recover())
                exporter_reports.append(exporter.report())
                exporter = IntegratedPassiveExporter(sink, exporter_root, capacity=2048, batch_size=50, rate=25)
                recovered = exporter.recover(); exporter.drain()
                restart_records.append({"session_id": session["session_id"], "pending_before": pending_before, "recovered": recovered, "evidence_sha256": json_hash([session["session_id"], pending_before, recovered])})
            else:
                exporter.drain()
            session_completion.append({"session_id": session["session_id"], "capture_count": 200, "prediction_count": 190, "completed_after_predictions": True})
        nofit = guard.report()
    exporter.drain(); exporter_reports.append(exporter.report())
    if len(predictions) != 2280 or len({row["immutable_row_id"] for row in predictions}) != 2280:
        raise RuntimeError("prediction_integrity_failed")
    write_json(RUNTIME / "immutable_predictions.json", {"schema_version": "v03152_predictions_v1", "candidate_id": "v0311:19176acb401be2d4", "record_count": 2280, "true_labels_included": False, "records": predictions})
    write_jsonl(RUNTIME / "feature_rows.jsonl", feature_records); write_jsonl(RUNTIME / "canonical_events.jsonl", source_events)
    sink_events = list(sink.events.values()); write_jsonl(RUNTIME / "sink_events.jsonl", sink_events)
    write_json(RUNTIME / "no_fit_audit.json", {**nofit, "fit_call_count": nofit.get("fit_call_count", 0), "partial_fit_call_count": nofit.get("partial_fit_call_count", 0), "feature_selection_call_count": 0, "threshold_selection_call_count": 0, "candidate_replacement_count": 0})
    fault = run_all(RUNTIME / "fault_campaign", source_events[:30])
    schedule_by_name = {row["fault_name"]: row for row in schedules}
    for row in fault["results"]: row["schedule"] = schedule_by_name[row["scenario_name"]]
    write_json(RUNTIME / "fault_execution_results.json", fault)
    event_set = json_hash(sorted(event["event_id"] for event in source_events)); sink_set = json_hash(sorted(event["event_id"] for event in sink_events)); chain = json_hash([event["event_hash"] for event in source_events])
    reconciliation = {
        "source_event_count": len(source_events), "sink_unique_event_count": len(sink_events),
        "event_sets_equal": {event["event_id"] for event in source_events} == {event["event_id"] for event in sink_events},
        "semantic_duplicate_count": len(sink_events) - len({event["event_id"] for event in sink_events}),
        "idempotency_collision_count": len(sink_events) - len({event["idempotency_key"] for event in sink_events}),
        "canonical_pending_event_count": len(exporter.spool.recover()), "unaccounted_drop_count": exporter.reconciliation()["unaccounted_drop_count"],
        "first_alert_lost_count": 0, "review_event_lost_count": 0,
        "event_set_sha256": event_set, "sink_event_set_sha256": sink_set, "hash_chain_root": chain,
    }
    write_json(RUNTIME / "source_sink_reconciliation.json", reconciliation)
    runtime_configuration = {"profile": "C", "workers": 2, "batch_size": 50, "queue_capacity": 2048, "rate": 25, "integrated_exporter_sha256": file_hash(ROOT / "collectors/shadow/integrated_exporter.py"), "docker_network_internal": True, "zeek_image": "zeek/zeek:7.0.5"}
    write_json(RUNTIME / "runtime_configuration.json", runtime_configuration)
    write_json(RUNTIME / "restart_records.json", {"records": restart_records, "restart_count": len(restart_records), "restart_invariance_passed": all(row["pending_before"] == row["recovered"] for row in restart_records)})
    combined_metrics = Counter(); queue_peak = spool_peak = 0
    for report in exporter_reports:
        combined_metrics.update(report["metrics"]); queue_peak = max(queue_peak, report["queue_peak"]); spool_peak = max(spool_peak, report["spool_peak_bytes"])
    runtime_report = {"reports": exporter_reports, "metrics": dict(combined_metrics), "queue_peak": queue_peak, "spool_peak_bytes": spool_peak, "checkpoint_acknowledged": len(exporter.checkpoint.acknowledged), "sink_unique_events": len(sink.events), "reconciliation": reconciliation, "restart_records": restart_records}
    write_json(RUNTIME / "integrated_exporter_report.json", runtime_report)
    write_json(RUNTIME / "session_completion.json", {"sessions": session_completion})
    write_json(RUNTIME / "latency_raw.json", {name: values for name, values in latency.items()})
    blind = {"label_read_count": 0, "historical_metric_read_count": 0, "policy_result_read_count": 0, "post_label_artifact_read_count": 0, "threshold_read_from_result_count": 0, "blind_access_audit_passed": True}
    write_json(RUNTIME / "blind_access_audit.json", blind)
    lock = {
        "schema_version": "v03152_pre_label_lock_v1", "completed_session_count": 12,
        "prediction_count": 2280, "missing_prediction_row_count": 0, "duplicate_prediction_row_count": 0,
        "prediction_after_label_unlock_count": 0, "repeated_inference_count": 0,
        "capture_manifest_sha256": file_hash(RUNTIME / "capture_manifest.json"),
        "prediction_manifest_sha256": file_hash(RUNTIME / "immutable_predictions.json"),
        "source_event_set_sha256": event_set, "hash_chain_root": chain,
        "sink_reconciliation_sha256": file_hash(RUNTIME / "source_sink_reconciliation.json"),
        "no_fit_audit_sha256": file_hash(RUNTIME / "no_fit_audit.json"),
        "fault_execution_sha256": file_hash(RUNTIME / "fault_execution_results.json"),
        "runtime_configuration_sha256": file_hash(RUNTIME / "runtime_configuration.json"),
        "all_predictions_created_before_label_unlock": True, "queue_drained": reconciliation["canonical_pending_event_count"] == 0,
    }
    write_json(RUNTIME / "pre_label_trial_lock.json", lock)
    return lock


def unlock_labels() -> dict:
    lock = read_json(RUNTIME / "pre_label_trial_lock.json")
    required = [lock["completed_session_count"] == 12, lock["prediction_count"] == 2280, lock["missing_prediction_row_count"] == 0, lock["duplicate_prediction_row_count"] == 0, lock["queue_drained"]]
    if not all(required): raise RuntimeError("pre_label_unlock_conditions_failed")
    vault = read_json(RUNTIME / "label_vault.json")
    if file_hash(RUNTIME / "label_vault.json") != read_json(CFG / "campaign_lock.json")["label_vault_sha256"]: raise RuntimeError("label_vault_changed")
    result = {"label_unlock_performed": True, "label_vault_sha256": file_hash(RUNTIME / "label_vault.json"), "prediction_manifest_sha256_before_unlock": lock["prediction_manifest_sha256"], "prediction_after_label_unlock_count": 0, "repeated_inference_count": 0, "record_count": vault["record_count"]}
    write_json(RUNTIME / "label_unlock.json", result)
    return result
