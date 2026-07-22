from __future__ import annotations

import argparse
from pathlib import Path

import yaml


def validate(root: Path) -> list[str]:
    status = yaml.safe_load((root / "docs/status/project-status.yaml").read_text(encoding="utf-8"))
    failures = []
    expected = {"current_candidate": "v03154:65a3dd912d845bc1", "latest_independent_model_holdout": "v0.3.15.5", "latest_runtime_trial": "v0.3.15.5.1"}
    for key, value in expected.items():
        if status.get(key) != value: failures.append(f"{key}_mismatch")
    for key in ("production_ready", "shadow_mode_ready", "backend_integration_ready", "automatic_enforcement_ready", "external_validation_completed"):
        if status.get(key) is not False: failures.append(f"{key}_must_be_false")
    versions = [item["version"] for item in status["stages"]]
    if "v0.3.15.5.1" not in versions or versions.index("v0.3.15.5.1") <= versions.index("v0.3.15.5"): failures.append("numeric_stage_order")
    if tuple(map(int, status["current_completed_stage"].removeprefix("v").split("."))) < (0, 3, 15, 5, 1): failures.append("current_completed_stage_regressed")
    old = next(item for item in status["stages"] if item["version"] == "v0.3.15.5")
    if old["result"] != "scientific_passed_runtime_contract_failed_not_promoted": failures.append("historical_v03155_result_changed")
    required = [root / "docs/experiments/v0_3_15_5_1.md", root / "docs/contracts/shadow-event-v2.md", root / "collectors/shadow/contracts/candidate_registry_v1.json", root / "collectors/shadow/contracts/shadow_event_v2.schema.json"]
    if any(not path.is_file() for path in required): failures.append("required_reference_missing")
    text = "\n".join((root / name).read_text(encoding="utf-8") for name in ("README.md", "docs/status.md", "docs/current-capabilities.md", "docs/roadmap.md", "docs/experiments/v0_3_15_5_1.md"))
    for phrase in ("shadow_event_v1", "shadow_event_v2", "v0.3.15.5.1", "v0.3.16"):
        if phrase not in text: failures.append(f"missing_statement:{phrase}")
    if "превосходство над" in text.casefold() and "не заявляется" not in text.casefold(): failures.append("superiority_claim")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--root", default="."); parser.add_argument("--strict", action="store_true"); args = parser.parse_args()
    failures = validate(Path(args.root)); print(f"v0.3.15.5.1 documentation: {'passed' if not failures else 'failed'}")
    for failure in failures: print(f"- {failure}")
    return 1 if failures and args.strict else 0


if __name__ == "__main__": raise SystemExit(main())
