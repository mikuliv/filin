from __future__ import annotations

import json
import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
REQUIRED = (
    ROOT / "README.md",
    ROOT / "docs/status.md",
    ROOT / "docs/current-capabilities.md",
    ROOT / "docs/roadmap.md",
    ROOT / "docs/experiments.md",
    ROOT / "docs/experiments/v0_3_17_1.md",
    ROOT / "docs/contracts/runtime_timing_trace_v2.md",
    ROOT / "ml/protocols/index.md",
    ROOT / "ml/reports/index.md",
)


def validate() -> dict:
    errors: list[str] = []
    for path in REQUIRED:
        if not path.is_file():
            errors.append(f"missing:{path.relative_to(ROOT).as_posix()}")
    texts = {
        path.relative_to(ROOT).as_posix(): path.read_text(encoding="utf-8")
        for path in REQUIRED
        if path.is_file()
    }
    combined = "\n".join(texts.values()).casefold()
    required_semantics = {
        "historical_v0317_negative": ("v0.3.17", "отрицатель"),
        "corrective_stage": ("v0.3.17.1", "corrective"),
        "ssd_profile_changed": ("ssd", "напрямую"),
        "targeted_duration": ("45", "минут"),
        "no_automatic_endurance": ("четырёхчас", "не"),
        "timing_contract": ("runtime_timing_trace_v2",),
        "production_prohibited": ("production", "запрещ"),
        "backend_prohibited": ("backend integration", "запрещ"),
        "shadow_prohibited": ("shadow mode", "запрещ"),
    }
    for name, tokens in required_semantics.items():
        if not all(token in combined for token in tokens):
            errors.append(f"semantic_missing:{name}")
    for name, text in texts.items():
        if re.search(r"\b[A-Za-z]:[\\/]", text):
            errors.append(f"absolute_local_path:{name}")
    forbidden = (
        r"production[_ ]ready\s*[:=]\s*true",
        r"shadow[_ ]mode[_ ]allowed\s*[:=]\s*true",
        r"backend[_ ]integration[_ ]allowed\s*[:=]\s*true",
    )
    for pattern in forbidden:
        if re.search(pattern, combined):
            errors.append(f"forbidden_claim:{pattern}")
    status_path = ROOT / "docs/status/project-status.yaml"
    policy_path = ROOT / "ml/reports/v0_3_17_1/v0_3_17_1_policy_result.json"
    if status_path.is_file() and policy_path.is_file():
        status = yaml.safe_load(status_path.read_text(encoding="utf-8"))
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
        if status.get("current_completed_stage") != "v0.3.17.1":
            errors.append("status_current_stage")
        if (
            status.get(
                "candidate_ready_for_v0_3_18_external_review_and_trial_design"
            )
            != policy.get(
                "candidate_ready_for_v0_3_18_external_review_and_trial_design"
            )
        ):
            errors.append("status_readiness_mismatch")
    return {
        "passed": not errors,
        "errors": errors,
        "document_count": len(texts),
    }


def main() -> int:
    result = validate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
