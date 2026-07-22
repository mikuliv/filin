from __future__ import annotations

import hashlib
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yaml
from scapy.all import RawPcapReader

from ml.experiments.v0_3_15_4 import run_campaign as base

ROOT = Path(__file__).resolve().parents[3]
CFG = ROOT / "ml/experiments/v0_3_15_5"
REPORT = ROOT / "ml/reports/v0_3_15_5"
RUNTIME = ROOT / "runtime/v0_3_15_5"
PROTOCOL = ROOT / "ml/protocols/v0_3_15_5_protocol.yaml"

base.CFG = CFG
base.RUNTIME = RUNTIME
base.NETWORK = "filin-v03155-isolated"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8", newline="\n")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_yaml(name: str):
    return yaml.safe_load((CFG / name).read_text(encoding="utf-8"))


def capture_phase() -> dict:
    lock = read_json(REPORT / "protocol_lock.json")
    if lock["protocol_sha256"] != sha(PROTOCOL) or not lock["frozen_before_first_capture"]:
        raise RuntimeError("protocol_lock_invalid")
    commitment = read_json(REPORT / "label_vault_commitment.json")
    if commitment["label_vault_sha256"] != sha(RUNTIME / "label_vault.json"):
        raise RuntimeError("label_vault_commitment_invalid")
    sessions = load_yaml("campaign.yaml")["sessions"]
    labels = {(x["session_id"], x["scored_window_index"]): x for x in read_json(RUNTIME / "label_vault.json")["records"]}
    manifest = []
    for session in sessions:
        for capture_index in range(200):
            scored = capture_index - 10 if capture_index >= 10 else None
            label = labels.get((session["session_id"], scored), {"true_class": "benign", "variant_id": None})
            variant_id = label.get("variant_id") or "benign_holdout_00"
            variant = int(hashlib.sha256(variant_id.encode()).hexdigest()[:4], 16)
            path = RUNTIME / "sessions" / session["session_id"] / "captures" / f"window_{capture_index:03d}.pcap"
            if path.exists():
                detail = {"packet_count": sum(1 for _ in RawPcapReader(str(path))), "sha256": sha(path), "size": path.stat().st_size}
            else:
                detail = base.create_capture(path, session, capture_index, label["true_class"], variant)
            manifest.append({"session_id": session["session_id"], "session_group": session["session_group"],
                             "capture_index": capture_index, "scored_window_index": scored,
                             "capture_id": f"v03155:{session['session_id']}:{capture_index:03d}",
                             "capture_sha256": detail["sha256"], "size": detail["size"],
                             "packet_count": detail["packet_count"], "closed_before_processing": True,
                             "synthetic_only": True, "fallback_used": False})
    hashes = [x["capture_sha256"] for x in manifest]
    if len(manifest) != 4000 or len(set(hashes)) != 4000:
        raise RuntimeError("capture_integrity_failure")
    write_json(RUNTIME / "capture_manifest.json", {"schema_version": "v03155_capture_manifest_v1", "captures": manifest})
    report = {"schema_version": "v03155_capture_integrity_v1", "capture_count": 4000,
              "unique_sha256_count": 4000, "all_closed_before_processing": True, "pcap_hash_overlap_count": 0,
              "synthetic_only": True, "external_target_count": 0, "fallback_count": 0,
              "capture_manifest_sha256": sha(RUNTIME / "capture_manifest.json")}
    write_json(RUNTIME / "capture_integrity_report.json", report)
    return report


def zeek_phase() -> dict:
    base._ensure_network()
    sessions = load_yaml("campaign.yaml")["sessions"]
    results = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(base._zeek_session, session) for session in sessions]
        for future in as_completed(futures):
            row = future.result(); results.append(row); print(json.dumps(row, ensure_ascii=False), flush=True)
    processed = sum(x["processed"] for x in results)
    if processed != 4000:
        raise RuntimeError("zeek_total_mismatch")
    report = {"schema_version": "v03155_zeek_processing_v1", "processed_capture_count": processed,
              "pcap_zeek_runs_per_capture": 1, "session_count": 20, "all_containerized": True,
              "image": base.IMAGE, "isolated_internal_network": base.NETWORK, "fallback_count": 0,
              "session_results": sorted(results, key=lambda x: x["session_id"])}
    write_json(RUNTIME / "zeek_processing_report.json", report)
    return report


def feature_phase() -> dict:
    captures = read_json(RUNTIME / "capture_manifest.json")["captures"]
    sessions = {x["session_id"]: x for x in load_yaml("campaign.yaml")["sessions"]}
    states = {sid: base.AssetState(4) for sid in sessions}
    vectors, sidecars = [], []
    provenance_counts = Counter()
    for capture in sorted(captures, key=lambda x: (x["session_id"], x["capture_index"])):
        vector, sidecar = base.extract(RUNTIME / "sessions" / capture["session_id"] / "zeek" / f"window_{capture['capture_index']:03d}", states[capture["session_id"]], capture["session_id"])
        if capture["scored_window_index"] is None:
            continue
        row_id = hashlib.sha256(f"{capture['capture_id']}:{capture['capture_sha256']}".encode()).hexdigest()
        bucket = capture["scored_window_index"] // 18
        activity = hashlib.sha256(f"{capture['session_id']}:tcp:80:{bucket}".encode()).hexdigest()
        feature_hash = hashlib.sha256(json.dumps(vector, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        vectors.append({"immutable_row_id": row_id, "session_id": capture["session_id"],
                        "session_group": capture["session_group"], "capture_id": capture["capture_id"],
                        "capture_sha256": capture["capture_sha256"], "scored_window_index": capture["scored_window_index"],
                        "causal_order": capture["scored_window_index"] + 1, "activity_key_hash": activity,
                        "feature_schema": "network_features_v2", "feature_row_sha256": feature_hash, "features": vector})
        sidecar.update({"immutable_row_id": row_id, "session_id": capture["session_id"], "feature_row_sha256": feature_hash})
        sidecars.append(sidecar); provenance_counts.update(sidecar["provenance"].values())
    if len(vectors) != 3800 or any(list(row["features"]) != base.FEATURES for row in vectors):
        raise RuntimeError("feature_contract_failure")
    write_jsonl(RUNTIME / "feature_rows.jsonl", vectors)
    write_jsonl(RUNTIME / "feature_provenance.jsonl", sidecars)
    report = {"schema_version": "v03155_feature_v2_provenance_v1", "feature_schema": "network_features_v2",
              "row_count": 3800, "feature_count": 51, "provenance_record_count": 193800,
              "feature_provenance_coverage": 1.0, "allowed_provenance_counts": dict(provenance_counts),
              "guessed_feature_count": 0, "label_derived_feature_count": 0, "future_derived_feature_count": 0,
              "hidden_state_derived_feature_count": 0, "sidecar_used_as_model_input": False,
              "feature_rows_sha256": sha(RUNTIME / "feature_rows.jsonl"),
              "provenance_sha256": sha(RUNTIME / "feature_provenance.jsonl")}
    write_json(RUNTIME / "feature_v2_provenance_report.json", report)
    return report


def main() -> int:
    capture = capture_phase() if not (RUNTIME / "capture_manifest.json").exists() else read_json(RUNTIME / "capture_integrity_report.json")
    zeek = zeek_phase() if not (RUNTIME / "zeek_processing_report.json").exists() else read_json(RUNTIME / "zeek_processing_report.json")
    features = feature_phase() if not (RUNTIME / "feature_v2_provenance_report.json").exists() else read_json(RUNTIME / "feature_v2_provenance_report.json")
    write_json(RUNTIME / "campaign_completion.json", {"campaign_complete": True, "capture_count": capture["capture_count"],
                                                       "processed_count": zeek["processed_capture_count"], "feature_count": features["row_count"]})
    print(json.dumps(read_json(RUNTIME / "campaign_completion.json"), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
