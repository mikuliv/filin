"""Строгая проверка фактического итогового отчёта v0.3.11."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml


SECTIONS = (
    "Причина нового цикла", "Научная гипотеза", "Ограничения старых datasets", "Protocol freeze",
    "Data access policy", "Hardware profile", "Performance baseline", "Resource profile", "Training campaign",
    "Prospective validation campaign", "Episode design", "Variable episode length", "Feature schema",
    "Fixed HGB architecture", "Calibration", "Mondrian conformal", "Diagnostic support",
    "Burden-aware state taxonomy", "Strong path", "Weak path", "Pre-alert pending", "Post-alert continuation",
    "Duplicate suppression", "Review states", "Unresolved pending", "Structural policy reachability",
    "Nested grouped selection", "Policy grid", "Selected candidate", "Candidate freeze", "Validation capture lock",
    "Validation lock", "Candidate integrity", "No-fit audit", "Immutable prediction", "Closed-set metrics",
    "Calibration metrics", "Conformal metrics", "Strong-path metrics", "Weak-path metrics", "Burden metrics",
    "Alert-emission metrics", "Episode metrics", "Detection latency", "Per-run metrics", "Per-group metrics",
    "Per-class metrics", "Benign variant metrics", "Controls", "Drift", "Interpretation", "Bootstrap intervals",
    "HGB compute profile", "Policy evaluator performance", "CPU utilization", "RAM utilization",
    "GPU applicability", "Checkpoint and resume", "Policy result", "Readiness", "Ограничения",
    "Следующий этап", "Вывод",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", required=True)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    summary = Path(args.summary).resolve()
    root = Path(__file__).resolve().parents[2]
    text = summary.read_text(encoding="utf-8")
    missing = [name for name in SECTIONS if f"## {name}" not in text]
    empty = [name for name in SECTIONS if not text.split(f"## {name}", 1)[1].split("\n## ", 1)[0].strip()]
    required_files = {
        "protocol_freeze": root / "ml/reports/v0_3_11/protocol_freeze.json",
        "selection": root / "ml/reports/v0_3_11/candidate_selection.json",
        "evaluation": root / "ml/reports/v0_3_11/validation_evaluation.json",
        "flags": root / "ml/reports/v0_3_11/result_flags.json",
        "resources": root / "ml/reports/v0_3_11/resource_summary.json",
        "policy_check": root / "ml/reports/v0_3_11/policy_evaluator_check.json",
        "prediction": root / "ml/reports/v0_3_11/validation_predictions.json",
        "capture": root / "ml/reports/v0_3_11/validation_capture_manifest.json",
        "candidate": root / "ml/experiments/v0_3_11/frozen_candidate_manifest.yaml",
        "validation_lock": root / "ml/experiments/v0_3_11/validation_lock_manifest.yaml",
    }
    absent = [name for name, path in required_files.items() if not path.exists()]
    tokens = ("792", "396", "720", "360", "240", "120", "gpu_acceleration_used",
              "candidate_ready_for_v0_3_12_regression", "candidate_ready_for_shadow_mode",
              "sensor_ready_for_backend_integration", "strict resume", "CPU", "RAM")
    missing_tokens = [token for token in tokens if token not in text]
    if not absent:
        freeze = json.loads(required_files["protocol_freeze"].read_text(encoding="utf-8"))
        candidate = yaml.safe_load(required_files["candidate"].read_text(encoding="utf-8"))
        lock = yaml.safe_load(required_files["validation_lock"].read_text(encoding="utf-8"))
        prediction_sha = __import__("hashlib").sha256(required_files["prediction"].read_bytes()).hexdigest()
        candidate_manifest_sha = __import__("hashlib").sha256(required_files["candidate"].read_bytes()).hexdigest()
        validation_lock_sha = __import__("hashlib").sha256(required_files["validation_lock"].read_bytes()).hexdigest()
        dynamic = [freeze["combined_sha256"], *freeze["files"].values(), candidate["candidate_artifact_sha256"],
                   candidate_manifest_sha, validation_lock_sha, lock["ordered_row_mapping_sha256"], prediction_sha]
        missing_tokens.extend(value for value in dynamic if value and value not in text)
    result = {"summary": str(summary), "sections": len(SECTIONS), "missing_sections": missing,
              "empty_sections": empty, "missing_files": absent, "missing_facts": missing_tokens,
              "valid": not (missing or empty or absent or missing_tokens)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.strict and not result["valid"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
