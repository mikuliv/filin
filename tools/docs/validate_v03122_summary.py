"""Strict consistency validator for the runtime v0.3.12.2 summary."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "ml/reports/v0_3_12_2"


def load(name: str):
    return json.loads((REPORT / name).read_text(encoding="utf-8"))


def validate(summary_path: Path) -> list[str]:
    errors: list[str] = []
    if not summary_path.is_file():
        return [f"summary does not exist: {summary_path}"]
    text = summary_path.read_text(encoding="utf-8")
    required_sections = (
        "Protocol freeze", "Benchmark registry", "Scientific coverage policy",
        "Historical read-only guard", "No-fit audit", "Regression bundle validation",
        "v0.3.8 input lock", "v0.3.8 immutable prediction", "Combined prediction manifest",
        "Causal-order invariance", "v0.3.8 window metrics", "v0.3.8 stateful metrics",
        "v0.3.8 episode metrics", "Calibration regression", "Conformal regression",
        "Non-inferiority", "Cross-benchmark aggregate", "Performance profile",
        "Checkpoint and resume", "Regression policy result", "Readiness for v0.3.13",
        "Ограничения", "Следующий этап", "Вывод",
    )
    for section in required_sections:
        if f"## {section}" not in text:
            errors.append(f"missing section: {section}")

    freeze = load("protocol_freeze.json")
    integrity = load("frozen_integrity_audit.json")
    lock = load("v038_input_lock.json")
    coverage = load("evaluation_coverage.json")
    nofit = load("no_fit_audit.json")
    policy = load("v0_3_12_2_policy_result.json")
    resume = load("resume_audit.json")
    bundles = load("regression_bundle_validation.json")
    combined = load("combined_prediction_manifest.json")

    for value in (
        freeze["combined_protocol_sha256"], freeze["hashes"]["registry"],
        freeze["hashes"]["coverage"], integrity["actual"]["candidate_artifact"],
        integrity["actual"]["candidate_manifest"], lock["input_lock_sha256"],
    ):
        if value not in text:
            errors.append(f"summary omits frozen hash: {value}")
    if lock["scored_row_count"] != 216 or lock["feature_count"] != 51:
        errors.append("v0.3.8 input lock counts are invalid")
    if coverage["scientific_denominator"] != 3 or coverage["scientific_bundle_evaluated_count"] != 3:
        errors.append("scientific denominator/evaluated count is not 3/3")
    if coverage["legacy_unavailable_affects_pass_fail"]:
        errors.append("legacy unavailable bundles affect pass/fail")
    for short in ("v038", "v039", "v0310"):
        invariant = load(f"{short}_causal_invariance.json")
        if not invariant["causal_order_invariance_passed"] or invariant["profile_count"] != 6:
            errors.append(f"causal invariance failed: {short}")
    expected = {"v039": {"1": 29, "2": 1, "3": 0, "4": 0}, "v0310": {"1": 60, "2": 0, "3": 0, "4": 0}}
    for short, counts in expected.items():
        episode = load(f"{short}_metrics.json")["episode"]
        if episode["alert_window_counts"] != counts or episode["detection_by_second_window"] != 1.0:
            errors.append(f"causal positive control failed: {short}")
    legacy = load("legacy_physical_order_control.json")
    if legacy["v039"]["alert_counts"] != {"1": 12, "2": 10, "3": 8} or legacy["v0310"]["alert_counts"] != {"1": 23, "2": 21, "3": 16}:
        errors.append("legacy physical-order control mismatch")
    zero_counters = ("fit_call_count", "partial_fit_call_count", "fit_transform_call_count", "calibration_fit_call_count", "conformal_fit_call_count", "threshold_selection_call_count", "feature_selection_call_count", "candidate_replacement_count", "docker_campaign_call_count", "zeek_processing_call_count", "feature_extraction_call_count")
    for key in zero_counters:
        if nofit[key] != 0:
            errors.append(f"non-zero no-fit counter: {key}")
    if (nofit["v0.3.8_prediction_generation_count"], nofit["v0.3.9_prediction_generation_count"], nofit["v0.3.10_prediction_generation_count"]) != (1, 0, 0):
        errors.append("prediction generation counters mismatch")
    if not resume["strict_resume_passed"] or resume["v038_prediction_repeated"]:
        errors.append("strict resume audit failed")
    if not bundles["all_valid"] or len(combined["predictions"]) != 3:
        errors.append("regression bundle or combined manifest validation failed")
    if not policy["v03122_regression_completed"] or not policy["v03122_regression_passed"] or not policy["candidate_ready_for_v0_3_13_blind_holdout"]:
        errors.append("v0.3.12.2 readiness is not positive")
    if policy["candidate_ready_for_shadow_mode"] or policy["sensor_ready_for_backend_integration"]:
        errors.append("summary policy illegally enables shadow/backend")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    path = args.summary if args.summary.is_absolute() else ROOT / args.summary
    errors = validate(path)
    if errors:
        print("v0.3.12.2 summary validation errors:")
        for error in errors:
            print(f"- {error}")
        return 1 if args.strict else 0
    print("v0.3.12.2 summary validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
