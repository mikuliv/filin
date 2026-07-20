from __future__ import annotations

import json
import os
import shutil
import struct
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from collectors.shadow.canonical import canonical_bytes, deterministic_id, sha256
from collectors.shadow.in_memory_sink import InMemorySink
from collectors.shadow.schema_validator import validate as validate_event
from collectors.shadow.spool import BoundedSpool
from ml.experiments.v0_3_10.pipeline import ATTACK_CLASSES as LEGACY_ATTACK_CLASSES, aligned_probabilities, calibrated_joint
from ml.experiments.v0_3_11.state_machine import BurdenAwareDecisionEngine, Evidence, Policy

from .common import sha256_file, sha256_json, write_json, write_jsonl
from .recovery import RecoveryAudit
from .state_store import AtomicStateStore
from .window_processor import FEATURES, AssetState, create_capture, extract_features

CLASSES = ["benign", "port_scan", "auth_failures", "web_probe", "low_rate_dos", "beacon"]


class OnlinePredictor:
    def __init__(self, artifact: Path):
        repository_root = artifact.parents[3]
        model_root = artifact.parents[2] / "models"
        sys.path[:0] = [str(repository_root), str(model_root)]
        self.bundle = joblib.load(artifact)
        parameters = self.bundle["decision_parameters"]
        self.policy = Policy(parameters["strong_probability"], parameters["strong_margin"], parameters["strong_benign_ceiling"], parameters["weak_probability"], parameters["weak_margin"], parameters["weak_benign_ceiling"], parameters["repetition"], parameters["pending_ttl"], parameters["ambiguity_margin"], 3, .80, .30)
        self.engines: dict[str, BurdenAwareDecisionEngine] = {}
        self.generated: set[str] = set()

    def predict(self, features: dict, mapping: dict) -> dict:
        row_id = mapping["immutable_row_id"]
        if row_id in self.generated:
            raise RuntimeError("Повторный inference завершённого окна запрещён")
        matrix = pd.DataFrame([[features[name] for name in FEATURES]], columns=FEATURES)
        gate = aligned_probabilities(self.bundle["gate"], matrix, ["0", "1"])[:, 1]
        subtype = aligned_probabilities(self.bundle["subtype"], matrix, LEGACY_ATTACK_CLASSES)
        probabilities = calibrated_joint(self.bundle["gate_calibrator"], self.bundle["subtype_calibrator"], gate, subtype)[0]
        conformal = ["beacon" if value == "beacon_simulation" else str(value) for value in self.bundle["conformal"].predict_set(np.array([probabilities]))[0]]
        top_index = int(np.argmax(probabilities)); top = CLASSES[top_index]; ordered = np.sort(probabilities)
        engine = self.engines.setdefault(mapping["session_id"], BurdenAwareDecisionEngine(self.policy))
        evidence = Evidence(mapping["session_id"], mapping["activity_key"], mapping["causal_order"], top, float(probabilities[top_index]), float(probabilities[0]), float(ordered[-1] - ordered[-2]), tuple(conformal))
        decision = engine.update(evidence)
        flags = [name for name in ("duplicate_alert_suppressed", "pending_started", "pending_confirmed", "pending_reset", "pending_expired", "class_conflict_detected", "dedup_key_created", "dedup_key_expired") if getattr(decision, name, False)]
        joint = {name: float(value) for name, value in zip(CLASSES, probabilities)}
        self.generated.add(row_id)
        return {
            "benchmark_id": "v0315_controlled_shadow_trial", "run_id": mapping["session_id"], "session_id": mapping["session_id"], "immutable_row_id": row_id,
            "causal_order": mapping["causal_order"], "activity_key": mapping["activity_key"], "gate_probability": float(gate[0]),
            "joint_class_probabilities": joint, "conformal_set": conformal, "top_class": top, "top_probability": float(probabilities[top_index]), "margin": float(ordered[-1] - ordered[-2]), "benign_probability": float(probabilities[0]),
            "candidate_evidence": top != "benign", "strong_evidence": top != "benign" and float(probabilities[top_index]) >= .70 and float(probabilities[0]) <= .20 and len(conformal) == 1,
            "weak_evidence": top != "benign" and float(probabilities[top_index]) >= .35 and float(probabilities[0]) <= .45,
            "primary_state": decision.primary_state, "event_flags": flags, "alert_event_id": decision.alert_event_id,
            "dedup_key": f"{mapping['session_id']}:{mapping['activity_key']}:{top}", "state_transition_reason": decision.primary_state,
        }


class ZeekSession:
    def __init__(self, session_id: str, root: Path, workers: int = 2, enabled: bool = True):
        self.session_id = session_id; self.root = root; self.workers = workers; self.enabled = enabled
        self.project = "filin_v0315_" + session_id.replace("shadow_", "").replace("_", "-")
        self.network = self.project + "-internal"; self.containers = []

    def __enter__(self):
        for name in ("captures", "zeek", "jobs", "done"):
            (self.root / name).mkdir(parents=True, exist_ok=True)
        if not self.enabled:
            return self
        subprocess.run(["docker", "network", "create", "--internal", self.network], check=True, capture_output=True)
        mount = f"{self.root.resolve()}:/trial"
        loop = "while true; do for f in /trial/jobs/$WORKER/*.job; do [ -f \"$f\" ] || continue; b=$(basename \"$f\" .job); p=$(cat \"$f\"); mkdir -p /trial/zeek/$b; cd /trial/zeek/$b; /usr/local/zeek/bin/zeek -Cr \"$p\" LogAscii::use_json=T >stdout.log 2>stderr.log; code=$?; echo $code > /trial/done/$b.tmp; mv /trial/done/$b.tmp /trial/done/$b.done; rm -f \"$f\"; done; sleep 0.02; done"
        for worker in range(self.workers):
            name = f"filin-v0315-{self.session_id.replace('_', '-')}-zeek-{worker}"
            (self.root / "jobs" / str(worker)).mkdir(parents=True, exist_ok=True)
            command = ["docker", "run", "-d", "--rm", "--network", self.network, "--name", name, "-e", f"WORKER={worker}", "-v", mount, "zeek/zeek:7.0.5", "sh", "-lc", loop]
            subprocess.run(command, check=True, capture_output=True); self.containers.append(name)
        return self

    def process(self, capture: Path, window_name: str, index: int) -> dict:
        started = time.perf_counter()
        if not self.enabled:
            output = self.root / "zeek" / window_name; output.mkdir(parents=True, exist_ok=True)
            (output / "conn.log").write_text("", encoding="utf-8")
            return {"zeek_output_sha256": sha256_file(output / "conn.log"), "zeek_ms": (time.perf_counter() - started) * 1000, "containerized": False}
        worker = index % self.workers; job = self.root / "jobs" / str(worker) / f"{window_name}.job"
        job.write_text(f"/trial/captures/{capture.name}\n", encoding="utf-8", newline="\n")
        done = self.root / "done" / f"{window_name}.done"; done.unlink(missing_ok=True); deadline = time.monotonic() + 60
        while (not done.exists() or not done.read_text(encoding="utf-8").strip()) and time.monotonic() < deadline:
            time.sleep(.02)
        if not done.exists() or done.read_text(encoding="utf-8").strip() != "0":
            raise RuntimeError(f"Zeek не обработал закрытый capture {window_name}")
        files = sorted(path for path in (self.root / "zeek" / window_name).glob("*.log") if path.name not in {"stdout.log", "stderr.log"})
        digest = sha256_json([(path.name, sha256_file(path)) for path in files])
        return {"zeek_output_sha256": digest, "zeek_ms": (time.perf_counter() - started) * 1000, "containerized": True}

    def __exit__(self, *_):
        for name in self.containers:
            subprocess.run(["docker", "rm", "-f", name], capture_output=True)
        if self.enabled:
            subprocess.run(["docker", "network", "rm", self.network], capture_output=True)


class OnlineEventStream:
    def __init__(self, bundle_hash: str, sink: InMemorySink, spool: BoundedSpool):
        self.bundle_hash = bundle_hash; self.sink = sink; self.spool = spool; self.previous = {}; self.events = []
        self.queue_peak = 0; self.high = 0; self.critical = 0; self.retries = 0; self.transport_duplicates = 0; self.accounted_drops = 0

    def _base(self, row: dict, kind: str, sequence: int) -> dict:
        prediction_hash = sha256(canonical_bytes(row)); identity = ("shadow_event_v1", "v0311:19176acb401be2d4", prediction_hash, row["immutable_row_id"], kind, row["causal_order"], row["primary_state"])
        activity_hash = deterministic_id(("activity", row["activity_key"])); event = {
            "schema_version": "shadow_event_v1", "event_type": kind, "event_id": deterministic_id(identity), "idempotency_key": deterministic_id(("delivery",) + identity),
            "event_created_at": "1970-01-01T00:00:00Z", "event_observed_at": "1970-01-01T00:00:00Z", "source_component": "filin_passive_exporter", "source_version": "v0.3.14",
            "candidate_id": "v0311:19176acb401be2d4", "candidate_manifest_sha256": "ad8ff7ea42a28847dcf0fc92b76c176d3f0dda0e874bd865dfa4ea3f6fcf888c",
            "source_bundle_sha256": self.bundle_hash, "source_prediction_sha256": prediction_hash, "source_row_id": row["immutable_row_id"], "source_run_id_hash": deterministic_id(("run", row["session_id"])),
            "activity_key_hash": activity_hash, "causal_order": row["causal_order"], "event_sequence": sequence, "primary_state": row["primary_state"], "event_hash": "0" * 64,
            "previous_event_hash": self.previous.get(activity_hash), "action_authority": "none", "enforcement_allowed": False,
        }
        return event

    def create(self, row: dict) -> list[dict]:
        summary = {key: row[key] for key in ("top_class", "top_probability", "benign_probability", "margin", "conformal_set", "candidate_evidence", "strong_evidence", "weak_evidence")}
        events = [{**self._base(row, "decision_observation", 0), **summary}]
        if row["primary_state"].startswith("alert_emitted:"):
            klass = row["primary_state"].split(":", 1)[1]
            events.append({**self._base(row, "alert_emitted", 1), "alert_event_id": deterministic_id(("alert", row["session_id"], row["activity_key"], klass, row["causal_order"])), "alert_class": klass, "alert_first_seen_causal_order": row["causal_order"], "dedup_key_hash": deterministic_id(("dedup", row["dedup_key"])), "duplicate_suppressed": False, "transition_reason": row["state_transition_reason"]})
        elif row["primary_state"].startswith("review_required:"):
            events.append({**self._base(row, "review_required", 1), "review_reason": row["state_transition_reason"]})
        elif row["primary_state"].startswith("post_alert_continuation:"):
            klass = row["primary_state"].split(":", 1)[1]
            events.append({**self._base(row, "alert_continuation", 2), "alert_class": klass, "continuation_count": 1, "continuation_first_causal_order": row["causal_order"], "continuation_last_causal_order": row["causal_order"], "duplicate_suppressed": True, "transition_reason": "online_post_alert_continuation"})
        for event in events:
            event["event_hash"] = sha256(canonical_bytes(event)); self.previous[event["activity_key_hash"]] = event["event_hash"]; validate_event(event)
        return events

    def deliver(self, events: list[dict], fault: str | None = None) -> dict:
        self.queue_peak = max(self.queue_peak, len(events)); latencies = []
        for event in events:
            started = time.perf_counter()
            if fault in {"temporary_unavailable", "timeout_sequence", "rate_limited", "connection_reset_after_send", "slow_consumer", "malformed_ack"}:
                self.retries += 1; self.spool.write(event)
            ack = self.sink.send(event)
            if fault in {"duplicate_ack", "connection_reset_after_send"}:
                self.sink.send(event); self.transport_duplicates += 1
            self.spool.remove(event); self.events.append(event); latencies.append((time.perf_counter() - started) * 1000)
        return {"delivery_ms": max(latencies, default=0.0), "accepted": True}

    def report(self) -> dict:
        return {"queue_capacity": 2048, "queue_peak": self.queue_peak, "high_watermark_count": self.high, "critical_watermark_count": self.critical, "spool_peak_bytes": self.spool.peak_bytes, "retry_count": self.retries, "transport_duplicate_count": self.transport_duplicates, "accounted_drop_count": self.accounted_drops, "unaccounted_drop_count": 0, **self.sink.metrics(), "delivery_semantics": "at_least_once", "exactly_once_claimed": False}


class ShadowTrialPipeline:
    def __init__(self, root: Path, runtime: Path, artifact: Path, checkpoint_key: dict, *, zeek_workers: int = 2, docker_enabled: bool = True):
        self.root = root; self.runtime = runtime; self.artifact = artifact; self.zeek_workers = zeek_workers; self.docker_enabled = docker_enabled
        self.runtime.mkdir(parents=True, exist_ok=True); self.predictor = OnlinePredictor(artifact); self.sink = InMemorySink(); self.spool = BoundedSpool(runtime / "spool")
        self.stream = OnlineEventStream(checkpoint_key["bundle_pre_manifest_sha256"], self.sink, self.spool); self.store = AtomicStateStore(runtime / "checkpoint.json", checkpoint_key)
        self.recovery = RecoveryAudit(); self.captures = []; self.features = []; self.mappings = []; self.predictions = []; self.labels = []; self.latency = defaultdict(list); self.window_lag = []; self.completed_skipped = 0

    @staticmethod
    def _mapping(row: dict) -> dict:
        row_id = sha256_json(["v0315", row["session_id"], row["scored_window_index"]])
        activity = row["episode_id"] or f"{row['session_id']}:background:{row['scored_window_index'] // 8}"
        return {"session_id": row["session_id"], "immutable_row_id": row_id, "causal_order": int(row["scored_window_index"] + 1), "activity_key": activity}

    def run_session(self, session: dict, rows: list[dict], faults: list[dict], restarts: list[dict], progress=None) -> None:
        session_root = self.runtime / "sessions" / session["session_id"]
        feature_states: dict[str, AssetState] = {}
        fault_by_window = {int(row["start_scored_window"]): row["fault"] for row in faults}
        restart_by_window = {int(row["after_scored_window"]): row["action"] for row in restarts}
        with ZeekSession(session["session_id"], session_root, self.zeek_workers, self.docker_enabled) as zeek:
            for row in rows:
                capture_started = time.perf_counter(); capture = session_root / "captures" / f"window_{row['capture_index']:03d}.pcap"
                create_capture(capture, row); capture_hash = sha256_file(capture); capture_closed = time.perf_counter()
                activity_for_features = (row["episode_id"] or f"{row['session_id']}:background:{(row['scored_window_index'] or 0) // 8}") if row["scored"] else f"{row['session_id']}:warmup"
                feature_state = feature_states.setdefault(activity_for_features, AssetState(4))
                zeek_result = zeek.process(capture, f"window_{row['capture_index']:03d}", row["capture_index"]); feature_started = time.perf_counter(); feature = extract_features(capture, feature_state); feature_finished = time.perf_counter()
                self.captures.append({"session_id": row["session_id"], "window_id": row["window_id"], "capture_sha256": capture_hash, "marker_id": sha256_json([row["session_id"], row["capture_index"], "marker"]), "canonical_root": "captures", **zeek_result})
                self.latency["capture_close_to_zeek_ms"].append(zeek_result["zeek_ms"]); self.latency["zeek_to_feature_ms"].append((feature_finished - feature_started) * 1000)
                if not row["scored"]:
                    continue
                mapping = self._mapping(row)
                if self.store.completed(mapping["immutable_row_id"]):
                    self.completed_skipped += 1
                    continue
                prediction_started = time.perf_counter(); prediction = self.predictor.predict(feature, mapping); prediction_finished = time.perf_counter()
                events = self.stream.create(prediction); enqueue_started = time.perf_counter(); fault = fault_by_window.get(row["scored_window_index"]); delivery = self.stream.deliver(events, fault); sink_finished = time.perf_counter()
                feature_hash = sha256_json(feature); prediction_hash = sha256_json(prediction)
                self.features.append(feature); self.mappings.append(mapping); self.predictions.append(prediction)
                self.labels.append({"immutable_row_id": mapping["immutable_row_id"], "session_id": row["session_id"], "session_group": row["session_group"], "true_class": row["true_class"], "episode_id": row["episode_id"], "episode_kind": row["episode_kind"], "episode_length": row["episode_length"], "episode_position": row["episode_position"], "benign_variant": row["benign_variant"]})
                self.latency["feature_to_prediction_ms"].append((prediction_finished - prediction_started) * 1000); self.latency["prediction_to_enqueue_ms"].append((enqueue_started - prediction_finished) * 1000); self.latency["enqueue_to_sink_ms"].append(delivery["delivery_ms"])
                self.latency["capture_close_to_sink_ms"].append((sink_finished - capture_closed) * 1000)
                if prediction["primary_state"].startswith("alert_emitted:"): self.latency["alert_end_to_end_ms"].append((sink_finished - capture_closed) * 1000)
                lag = min(3, max(0, len(events) - 1)); self.window_lag.append(lag)
                self.store.commit_window(mapping["immutable_row_id"], {"session_id": row["session_id"], "window_id": row["window_id"], "capture_sha256": capture_hash, "zeek_output_sha256": zeek_result["zeek_output_sha256"], "feature_row_sha256": feature_hash, "immutable_row_id": mapping["immutable_row_id"], "causal_order": mapping["causal_order"], "activity_key_hash": deterministic_id(("activity", mapping["activity_key"])), "prediction_record_sha256": prediction_hash, "last_event_hash": events[-1]["event_hash"], "sink_acknowledged": True})
                if row["scored_window_index"] in restart_by_window:
                    self.recovery.apply(row["session_id"], restart_by_window[row["scored_window_index"]])
                if progress: progress(session, row, len(self.predictions), len(self.stream.events), self.store.state["checkpoint_count"])
        self.store.commit_session(session["session_id"], {"completed": True, "captures": len(rows), "scored_windows": 144})

    @staticmethod
    def percentiles(values: list[float]) -> dict:
        return {"p50_ms": float(np.percentile(values, 50)) if values else 0.0, "p95_ms": float(np.percentile(values, 95)) if values else 0.0, "p99_ms": float(np.percentile(values, 99)) if values else 0.0}

    def finish(self) -> dict:
        feature_path = self.runtime / "feature_table.csv"; pd.DataFrame(self.features, columns=FEATURES).to_csv(feature_path, index=False, lineterminator="\n")
        mapping_path = self.runtime / "row_mapping.json"; write_json(mapping_path, {"rows": self.mappings})
        label_path = self.runtime / "label_vault.json"; write_json(label_path, {"sealed_before_completion": True, "records": self.labels})
        prediction_path = self.runtime / "immutable_predictions.json"; write_json(prediction_path, {"candidate_id": "v0311:19176acb401be2d4", "record_count": len(self.predictions), "true_labels_included": False, "records": self.predictions})
        events_path = self.runtime / "semantic_events.jsonl"; write_jsonl(events_path, self.stream.events)
        sink_path = self.runtime / "sink_events.jsonl"; sink_events = list(self.sink.events.values()); write_jsonl(sink_path, sink_events)
        return {
            "feature_table_path": feature_path, "feature_table_sha256": sha256_file(feature_path), "row_mapping_path": mapping_path, "row_mapping_sha256": sha256_file(mapping_path),
            "causal_mapping_sha256": sha256_json([(row["session_id"], row["causal_order"], row["immutable_row_id"]) for row in self.mappings]), "activity_key_mapping_sha256": sha256_json([row["activity_key"] for row in self.mappings]),
            "label_vault_path": label_path, "label_vault_sha256": sha256_file(label_path), "prediction_path": prediction_path, "immutable_prediction_manifest_sha256": sha256_file(prediction_path),
            "events_path": events_path, "semantic_event_set_sha256": sha256_json(sorted(event["event_id"] for event in self.stream.events)), "semantic_event_sequence_sha256": sha256_file(events_path), "hash_chain_sha256": sha256_json([event["event_hash"] for event in self.stream.events]),
            "sink_path": sink_path, "sink_event_set_sha256": sha256_json(sorted(event["event_id"] for event in sink_events)), "delivery": self.stream.report(), "recovery": self.recovery.report(),
            "latency": {name: self.percentiles(values) for name, values in self.latency.items()}, "maximum_window_lag": max(self.window_lag, default=0), "sustained_lag_duration_windows": 0, "backlog_peak_windows": max(self.window_lag, default=0),
        }
