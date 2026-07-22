from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
STATUS = ROOT / "docs/status/project-status.yaml"
CORE_DOCS = [ROOT / name for name in ("README.md", "docs/status.md", "docs/current-capabilities.md", "docs/roadmap.md")]
REQUIRED = CORE_DOCS + [
    ROOT / "docs/experiments/v0_3_14.md", ROOT / "docs/experiments/v0_3_14_errata.md",
    ROOT / "docs/experiments/v0_3_15.md", ROOT / "docs/experiments/v0_3_15_1.md",
    ROOT / "docs/experiments/v0_3_15_2.md",
    ROOT / "docs/experiments/v0_3_15_3.md", ROOT / "docs/experiments/v0_3_15_4_proposed.md",
    ROOT / "docs/contracts/index.md", ROOT / "docs/methodology/index.md",
    ROOT / "ml/reports/v0_3_15_1/v0_3_14_claim_reassessment.json",
    ROOT / "ml/reports/v0_3_15_1/v0_3_15_revalidation.json",
    ROOT / "ml/reports/v0_3_15_2/v0_3_15_2_policy_result.json",
    ROOT / "ml/reports/v0_3_15_3/v0_3_15_3_policy_result.json",
]


def version_key(value: str) -> tuple[int, ...]:
    return tuple(int(part) for part in value.removeprefix("v").split("."))


def markdown_links(path: Path):
    text = path.read_text(encoding="utf-8")
    for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", text):
        if "://" in target or target.startswith("#"):
            continue
        clean = target.split("#", 1)[0]
        if clean:
            yield (path.parent / clean).resolve()


def history_versions(text: str) -> list[str]:
    match = re.search(r"<!-- stage-history:start -->(.*?)<!-- stage-history:end -->", text, re.S)
    return re.findall(r"v\d+\.\d+(?:\.\d+)*", match.group(1)) if match else []


def validate() -> dict:
    errors = []
    status = yaml.safe_load(STATUS.read_text(encoding="utf-8"))
    expected = {
        "current_completed_stage": "v0.3.15.3", "current_candidate": "v0.3.11",
        "latest_independent_model_holdout": "v0.3.13", "latest_runtime_trial": "v0.3.15.2",
        "latest_corrective_audit": "v0.3.15.1", "latest_regression_analysis": "v0.3.15.3", "production_ready": False, "shadow_mode_ready": False,
        "backend_integration_ready": False, "automatic_enforcement_ready": False,
    }
    for key, value in expected.items():
        if status.get(key) != value: errors.append(f"status_mismatch:{key}")
    versions = [row["version"] for row in status.get("stages", [])]
    orders = [row["chronological_order"] for row in status.get("stages", [])]
    if versions != sorted(versions, key=version_key) or orders != sorted(orders) or len(set(orders)) != len(orders):
        errors.append("stage_order_invalid")
    for path in REQUIRED:
        if not path.is_file(): errors.append("required_document_missing:" + str(path.relative_to(ROOT)))
    for path in [item for item in REQUIRED if item.suffix == ".md" and item.is_file()]:
        for target in markdown_links(path):
            try: target.relative_to(ROOT)
            except ValueError: errors.append("link_escapes_repository:" + str(path.relative_to(ROOT))); continue
            if not target.exists(): errors.append("broken_link:" + str(path.relative_to(ROOT)) + "->" + str(target))
    combined = "\n".join(path.read_text(encoding="utf-8") for path in CORE_DOCS if path.exists())
    forbidden = {
        "stale_negative_v0312": r"актив(?:ен|на|но)\s+отрицатель\w*\s+v0\.3\.12",
        "v0313_prohibited": r"v0\.3\.13\s+(?:запрещ[её]н|не разреш[её]н)",
        "production_ready_claim": r"production[- ]ready\s*[:=]?\s*(?:true|да)",
        "backend_ready_claim": r"backend(?: integration)?[- ]ready\s*[:=]?\s*(?:true|да)",
    }
    for code, pattern in forbidden.items():
        if re.search(pattern, combined, re.I): errors.append(code)
    for path in (ROOT / "README.md", ROOT / "docs/roadmap.md"):
        if path.exists():
            found = history_versions(path.read_text(encoding="utf-8"))
            if not found or found != sorted(found, key=version_key): errors.append("chronology_invalid:" + str(path.relative_to(ROOT)))
    errata = ROOT / "docs/experiments/v0_3_14_errata.md"
    revalidation = ROOT / "docs/experiments/v0_3_15_1.md"
    if (ROOT / "docs/experiments/v0_3_14.md").is_file() and "v0_3_14_errata.md" not in (ROOT / "docs/experiments/v0_3_14.md").read_text(encoding="utf-8"):
        errors.append("v0314_errata_link_missing")
    if (ROOT / "docs/experiments/v0_3_15.md").is_file() and "v0_3_15_1.md" not in (ROOT / "docs/experiments/v0_3_15.md").read_text(encoding="utf-8"):
        errors.append("v0315_revalidation_link_missing")
    policy_path = ROOT / "ml/reports/v0_3_15_2/v0_3_15_2_policy_result.json"
    if policy_path.is_file():
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
        if not policy.get("v03152_prospective_runtime_trial_passed") and status.get("blocked_stage") != "v0.3.16": errors.append("negative_trial_must_block_v0316")
    if "v0.3.15.2" not in versions: errors.append("v03152_stage_missing")
    policy153_path = ROOT / "ml/reports/v0_3_15_3/v0_3_15_3_policy_result.json"
    if policy153_path.is_file():
        policy153 = json.loads(policy153_path.read_text(encoding="utf-8"))
        if status.get("next_allowed_stage") != "v0.3.15.4": errors.append("next_stage_policy_mismatch")
        if policy153.get("selected_next_cycle_track") != "Track E — mixed redevelopment": errors.append("selected_track_mismatch")
        if any(policy153.get(key) is not False for key in ("candidate_ready_for_v0_3_16_staging_connector_readiness", "candidate_ready_for_shadow_mode", "sensor_ready_for_backend_integration", "production_ready")): errors.append("v03153_readiness_mismatch")
    if "v0.3.15.3" not in versions: errors.append("v03153_stage_missing")
    if status.get("latest_corrective_audit") != "v0.3.15.1": errors.append("latest_corrective_audit_changed")
    if status.get("current_candidate") != "v0.3.11": errors.append("frozen_candidate_changed")
    return {"valid": not errors, "error_count": len(errors), "errors": errors, "checked_stage_count": len(versions), "status_source": str(STATUS.relative_to(ROOT)).replace("\\", "/")}


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--strict", action="store_true"); parser.parse_args()
    result = validate(); print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
