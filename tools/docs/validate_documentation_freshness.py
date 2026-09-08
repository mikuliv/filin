"""Проверяет актуальность документации относительно последнего пакета Phase 1."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.docs.documentation_v2 import (  # noqa: E402
    ROOT,
    build_protected_set,
    document_metadata,
    phase1_facts,
    tracked_markdown,
)
from tools.docs.validate_documentation_v2 import validate_inventory  # noqa: E402


CURRENT_PAGES = (
    "README.md",
    "docs/index.md",
    "docs/status/current-status.md",
    "docs/architecture/overview.md",
    "docs/research/independent-network-validation.md",
)
V04_CURRENT_PAGES = (
    "docs/getting-started/overview.md",
    "docs/status/laboratory-track-history.md",
    "docs/architecture/reconstruction-and-analysis-track.md",
    "docs/architecture/current-vs-historical.md",
)


def v04_facts(root: Path = ROOT) -> dict:
    data = yaml.safe_load((root / "docs/status/v0_4_track.yaml").read_text(encoding="utf-8"))
    return {
        "latest_completed_stage": data["latest_completed_stage"],
        "allowed_next_stage": data["allowed_next_stage"],
    }


def v04_stale_findings(text: str, facts: dict) -> list[str]:
    latest = re.escape(str(facts["latest_completed_stage"]))
    next_stage = re.escape(str(facts["allowed_next_stage"]))
    findings = []
    if re.search(r"(?:последн\w*|заверш[её]н\w*)[^\n.]{0,80}v0\.4\.4", text, re.IGNORECASE):
        findings.append("stale_v04_latest_completed")
    if re.search(r"(?:следующ\w*|допустим\w*)[^\n.]{0,80}v0\.4\.5", text, re.IGNORECASE):
        findings.append("stale_v04_next_allowed")
    if not re.search(latest, text):
        findings.append("v04_latest_marker_missing")
    if not re.search(next_stage, text):
        findings.append("v04_next_marker_missing")
    return sorted(set(findings))


def counterfactual_findings(text: str, pair_count: int) -> list[str]:
    findings = []
    if re.search(r"24\s+(?:контрфактуальн\w*\s+)?пар[^.\n]{0,160}technical_campaign\.json", text, re.IGNORECASE):
        findings.append("wrong_counterfactual_source")
    if not re.search(rf"\b{pair_count}\s+(?:контрфактуальн\w*\s+)?пар", text, re.IGNORECASE):
        findings.append("counterfactual_count_missing")
    if "superseding_freeze_campaign.json" not in text:
        findings.append("counterfactual_source_missing")
    return sorted(set(findings))


def status_semantic_findings(status: dict, label_contract: dict) -> list[str]:
    network = status.get("independent_network_validation", {})
    report = network.get("historical_operational_report", {})
    findings = []
    attempts = int(report.get("attempt_count", 0))
    retry_limit = int(report.get("retry_limit", 2))
    if attempts >= retry_limit:
        if not report.get("retry_limit_exhausted"):
            findings.append("v4_retry_exhaustion_missing")
        if network.get("package_execution_allowed_after_per_session_preflight"):
            findings.append("v4_preflight_allowed_after_retry_exhaustion")
    sequence = network.get("label_unlock_sequence", {})
    if sequence.get("contract_prerequisites") != label_contract.get("unlock_prerequisites"):
        findings.append("label_unlock_prerequisites_mismatch")
    if sequence.get("then") != ["labels_unlocked", "scientific_metrics_calculated"]:
        findings.append("label_metrics_order_mismatch")
    return sorted(set(findings))


def stale_findings(text: str, facts: dict) -> list[str]:
    """Ищет устаревшее состояние относительно фактического плана."""
    expected_count = int(facts["scenario_template_count"])
    findings: list[str] = []
    for match in re.finditer(r"(?<!по )\b(\d+)\s+(?:сценар(?:иев|ия|иям|ий)|шаблон(?:ов|а)?|(?:scenario\s+)?templates?)\b", text, flags=re.IGNORECASE):
        line_start = text.rfind("\n", 0, match.start()) + 1
        line_end = text.find("\n", match.end())
        line = text[line_start:line_end if line_end >= 0 else len(text)]
        if "technical_campaign.json" in line:
            continue
        if int(match.group(1)) != expected_count:
            findings.append("stale_phase1_scenario_count")
    if re.search(r"\bfuture\s+independent\s+network\s+validation\b", text, flags=re.IGNORECASE):
        findings.append("stale_future_protocol_claim")
    if re.search(r"\bscientific_campaign_started\s*[:=]\s*true\b", text, flags=re.IGNORECASE):
        findings.append("unqualified_started_claim")
    return sorted(set(findings))


def validate(root: Path = ROOT) -> list[str]:
    inventory_path = root / "docs/audit/documentation_inventory_v2.json"
    if not inventory_path.is_file():
        return ["inventory_missing"]
    data = json.loads(inventory_path.read_text(encoding="utf-8"))
    recorded = {row["path"] for row in data.get("documents", []) if isinstance(row, dict) and "path" in row}
    markdown = tracked_markdown(root)
    actual = {path.relative_to(root).as_posix() for path in markdown}
    errors: list[str] = []
    if recorded != actual:
        errors.append("inventory_stale")
    errors.extend(validate_inventory(root, markdown))

    facts = phase1_facts(root)
    laboratory_facts = v04_facts(root)
    required_markers = (
        facts["package_id"],
        str(facts["scenario_template_count"]),
        str(facts["execution_unit_count"]),
        str(facts["feature_count"]),
    )
    protected = {row["path"] for row in build_protected_set(root)}
    for relative in CURRENT_PAGES:
        path = root / relative
        if not path.is_file():
            errors.append(f"current_page_missing:{relative}")
            continue
        text = path.read_text(encoding="utf-8")
        for marker in required_markers:
            if marker not in text:
                errors.append(f"current_marker_missing:{relative}:{marker}")

    for relative in V04_CURRENT_PAGES:
        path = root / relative
        if not path.is_file():
            errors.append(f"current_page_missing:{relative}")
            continue
        errors.extend(f"{code}:{relative}" for code in v04_stale_findings(path.read_text(encoding="utf-8"), laboratory_facts))

    campaign = json.loads((root / "lab/network_validation/config/superseding_freeze_campaign.json").read_text(encoding="utf-8"))
    method = (root / "docs/research/independent-network-validation.md").read_text(encoding="utf-8")
    errors.extend(f"{code}:docs/research/independent-network-validation.md" for code in counterfactual_findings(method, len(campaign["counterfactual_pairs"])))

    status = yaml.safe_load((root / "docs/status/project-status.yaml").read_text(encoding="utf-8"))
    label_contract = json.loads((root / "lab/network_validation/execution/label_vault_contract.json").read_text(encoding="utf-8"))
    errors.extend(f"{code}:docs/status/project-status.yaml" for code in status_semantic_findings(status, label_contract))

    for path in markdown:
        relative = path.relative_to(root).as_posix()
        if relative in protected:
            continue
        metadata = document_metadata(path, root)
        if metadata.get("lifecycle") not in {"current", "generated", "redirect"} and not relative.endswith("README.md"):
            continue
        text = path.read_text(encoding="utf-8")
        errors.extend(f"{code}:{relative}" for code in stale_findings(text, facts))
    return sorted(set(errors))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    parser.parse_args()
    errors = validate()
    print(json.dumps({"valid": not errors, "errors": errors}, ensure_ascii=False, indent=2))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
