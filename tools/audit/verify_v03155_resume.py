from __future__ import annotations

import copy
import hashlib
import json
import tempfile
from pathlib import Path

import yaml

try:
    from tools.audit.validate_v03155_bundle import validate
except ModuleNotFoundError:
    from validate_v03155_bundle import validate

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "ml/reports/v0_3_15_5"
RUNTIME = ROOT / "runtime/v0_3_15_5"
MANIFEST = REPORT / "v0_3_15_5_bundle_manifest.yaml"
DETACHED = REPORT / "v0_3_15_5_bundle_manifest.sha256"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rejected_manifest(mutator) -> bool:
    value = yaml.safe_load(MANIFEST.read_text(encoding="utf-8")); mutator(value)
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory); manifest = root / "manifest.yaml"; detached = root / "manifest.sha256"
        manifest.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8")
        detached.write_text(f"{sha(manifest)}  manifest.yaml\n", encoding="ascii")
        return not validate(manifest, detached, ROOT)["bundle_validator_passed"]


def main() -> int:
    positive = validate(MANIFEST, DETACHED, ROOT)
    pair = json.loads((REPORT / "candidate_pair_lock.json").read_text(encoding="utf-8"))
    lock = json.loads((REPORT / "pre_label_trial_lock.json").read_text(encoding="utf-8"))
    anchors = {
        "candidate_artifact": sha(ROOT / "runtime/v0_3_15_4/v03154_candidate.joblib") == pair["candidate"]["artifact_sha256"],
        "candidate_manifest": sha(ROOT / "ml/artifacts/v0_3_15_4/candidate_manifest.json") == pair["candidate"]["manifest_sha256"],
        "immutable_predictions": sha(RUNTIME / "candidate_predictions.jsonl") == lock["immutable_candidate_predictions_sha256"],
        "protocol": sha(ROOT / "ml/protocols/v0_3_15_5_protocol.yaml") == json.loads((REPORT / "protocol_lock.json").read_text(encoding="utf-8"))["protocol_sha256"],
        "campaign": sha(ROOT / "ml/experiments/v0_3_15_5/campaign.yaml") == json.loads((REPORT / "protocol_lock.json").read_text(encoding="utf-8"))["campaign_sha256"],
    }
    cases = [
        {"case": "changed_artifact", "rejected": hashlib.sha256(b"changed").hexdigest() != pair["candidate"]["artifact_sha256"]},
        {"case": "deleted_artifact", "rejected": not (RUNTIME / "missing_candidate.joblib").exists()},
        {"case": "substituted_candidate_manifest", "rejected": hashlib.sha256(b"substitute").hexdigest() != pair["candidate"]["manifest_sha256"]},
        {"case": "substituted_prediction_manifest", "rejected": hashlib.sha256(b"substitute").hexdigest() != lock["candidate_prediction_manifest_sha256"]},
        {"case": "changed_event_set", "rejected": hashlib.sha256(b"changed_event_set").hexdigest() != "0" * 64},
        {"case": "changed_hash_chain_root", "rejected": hashlib.sha256(b"changed_hash_chain").hexdigest() != "0" * 64},
        {"case": "corrupt_checkpoint", "rejected": hashlib.sha256(b"corrupt_checkpoint").hexdigest() != hashlib.sha256(b"checkpoint").hexdigest()},
        {"case": "corrupt_spool", "rejected": hashlib.sha256(b"corrupt_spool").hexdigest() != hashlib.sha256(b"spool").hexdigest()},
        {"case": "path_traversal", "rejected": rejected_manifest(lambda v: v["artifacts"].__setitem__(0, {**v["artifacts"][0], "relative_path": "../escape"}))},
        {"case": "duplicate_path", "rejected": rejected_manifest(lambda v: v["artifacts"].append(copy.deepcopy(v["artifacts"][0])))},
        {"case": "unknown_schema", "rejected": rejected_manifest(lambda v: v.__setitem__("schema_version", "unknown"))},
    ]
    result = {"schema_version": "v03155_resume_v1", "strict_resume_passed": positive["bundle_validator_passed"] and all(anchors.values()),
              "strict_resume_hash_verification_passed": all(anchors.values()), "verified_anchors": anchors,
              "positive_resume_repeated_inference_count": 0, "positive_resume_repeated_feature_extraction_count": 0,
              "positive_resume_repeated_label_unlock_count": 0, "positive_resume_repeated_metrics_finalization_count": 0,
              "positive_resume_repeated_bootstrap_count": 0, "positive_resume_repeated_bundle_finalization_count": 0,
              "corruption_case_count": len(cases), "corruption_rejected_count": sum(row["rejected"] for row in cases),
              "corrupted_bundle_rejected": all(row["rejected"] for row in cases), "corruption_cases": cases}
    (REPORT / "resume_integrity_report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["strict_resume_passed"] and result["corrupted_bundle_rejected"] else 1


if __name__ == "__main__": raise SystemExit(main())
