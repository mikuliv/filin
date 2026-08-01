from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .capture import validate_capture_set
from .contracts import CAMPAIGN_SCHEMA, load_json, validate_campaign, validate_scenario
from .freeze import environment_lock, freeze_candidate_preview, freeze_preview
from .freeze_candidate import FREEZE_CANDIDATE_SCHEMA, candidate_summary, freeze_candidate_proxy_risks, validate_freeze_candidate
from .image_lock import compare_oci_archives, image_lock_blockers, validate_image_lock
from .parameter_verification import observations_from_zeek, verify_parameters
from .pipeline import COMPOSE, compose_config, run_technical_smoke
from .planning import plan_campaign, proxy_risks, validate_counterfactuals, validate_infrastructure_profiles, validate_split

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CAMPAIGN = Path(__file__).with_name("config") / "technical_campaign.json"
DEFAULT_FREEZE_CANDIDATE = Path(__file__).with_name("config") / "freeze_candidate_campaign.json"
DEFAULT_ACCEPTANCE_CRITERIA = Path(__file__).with_name("config") / "acceptance_criteria.json"
DEFAULT_IMAGE_LOCK = Path(__file__).with_name("config") / "image_lock.json"


def _emit(value: Any, json_output: bool) -> None:
    if json_output:
        print(json.dumps(value, ensure_ascii=False, sort_keys=True))
    elif isinstance(value, str):
        print(value)
    else:
        print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Safe planning tools for independent network validation infrastructure.")
    root.add_argument("--json", action="store_true", dest="json_output")
    commands = root.add_subparsers(dest="command", required=True)
    for name in ("validate-config", "plan-campaign", "validate-counterfactuals", "validate-split"):
        item = commands.add_parser(name)
        item.add_argument("--campaign", default=str(DEFAULT_CAMPAIGN))
    candidate = commands.add_parser("validate-freeze-candidate")
    candidate.add_argument("--campaign", default=str(DEFAULT_FREEZE_CANDIDATE))
    risks = commands.add_parser("inspect-proxy-risks")
    risks.add_argument("--campaign", default=str(DEFAULT_FREEZE_CANDIDATE))
    images = commands.add_parser("inspect-image-lock")
    images.add_argument("--image-lock", default=str(DEFAULT_IMAGE_LOCK))
    reproducibility = commands.add_parser("verify-image-reproducibility")
    reproducibility.add_argument("--left", required=True); reproducibility.add_argument("--right", required=True)
    preview = commands.add_parser("build-freeze-preview")
    preview.add_argument("--campaign", default=str(DEFAULT_FREEZE_CANDIDATE))
    preview.add_argument("--acceptance-criteria", default=str(DEFAULT_ACCEPTANCE_CRITERIA))
    preview.add_argument("--image-lock", default=str(DEFAULT_IMAGE_LOCK))
    commands.add_parser("render-compose")
    commands.add_parser("inspect-environment")
    parameter = commands.add_parser("validate-parameter-contract")
    parameter.add_argument("--scenario", required=True); parameter.add_argument("--zeek-dir", required=True)
    capture = commands.add_parser("validate-capture-manifest")
    capture.add_argument("--manifest", required=True); capture.add_argument("--dataset-root", required=True); capture.add_argument("--executions", required=True)
    capture.add_argument("--markers")
    smoke = commands.add_parser("run-technical-smoke")
    smoke.add_argument("--confirm-disposable", action="store_true"); smoke.add_argument("--output-dir", required=True)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "render-compose":
        _emit(compose_config(), args.json_output); return 0
    if args.command == "inspect-environment":
        _emit(environment_lock(ROOT, {}), args.json_output); return 0
    if args.command == "run-technical-smoke":
        _emit(run_technical_smoke(args.confirm_disposable, Path(args.output_dir)), args.json_output); return 0
    if args.command == "validate-parameter-contract":
        scenario = load_json(Path(args.scenario)); validate_scenario(scenario); _emit(verify_parameters(scenario, observations_from_zeek(Path(args.zeek_dir))), args.json_output); return 0
    if args.command == "validate-capture-manifest":
        manifests = load_json(Path(args.manifest)); executions = load_json(Path(args.executions)); markers = load_json(Path(args.markers)) if args.markers else None; validate_capture_set(manifests, Path(args.dataset_root), executions, markers); _emit({"valid": True, "capture_count": len(manifests)}, args.json_output); return 0
    if args.command == "validate-freeze-candidate":
        campaign = load_json(Path(args.campaign)); _emit(candidate_summary(campaign), args.json_output); return 0
    if args.command == "inspect-proxy-risks":
        campaign = load_json(Path(args.campaign))
        if campaign.get("schema_version") == FREEZE_CANDIDATE_SCHEMA:
            risks = freeze_candidate_proxy_risks(campaign)
        elif campaign.get("schema_version") == CAMPAIGN_SCHEMA:
            validate_campaign(campaign); risks = proxy_risks(campaign)
        else:
            raise ValueError("unsupported campaign schema")
        _emit({"valid": not any(row["severity"] == "error" for row in risks), "warning_count": len(risks), "risks": risks}, args.json_output); return 0
    if args.command == "inspect-image-lock":
        value = load_json(Path(args.image_lock)); validate_image_lock(value, ROOT); _emit({"valid": True, "blockers": image_lock_blockers(value), "image_lock": value}, args.json_output); return 0
    if args.command == "verify-image-reproducibility":
        _emit(compare_oci_archives(Path(args.left), Path(args.right)), args.json_output); return 0
    campaign = load_json(Path(args.campaign))
    if args.command == "validate-config":
        validate_campaign(campaign); validate_infrastructure_profiles(campaign["infrastructure_profiles"]); validate_counterfactuals(campaign); validate_split(campaign["split_policy"]["fixture_assignments"], campaign["split_policy"]); _emit({"valid": True, "experiment_started": False}, args.json_output)
    elif args.command == "plan-campaign":
        _emit(plan_campaign(campaign), args.json_output)
    elif args.command == "validate-counterfactuals":
        validate_campaign(campaign); validate_counterfactuals(campaign); _emit({"valid": True, "pair_count": len(campaign["counterfactual_pairs"])}, args.json_output)
    elif args.command == "validate-split":
        validate_campaign(campaign); validate_split(campaign["split_policy"]["fixture_assignments"], campaign["split_policy"]); _emit({"valid": True}, args.json_output)
    elif args.command == "build-freeze-preview":
        env = environment_lock(ROOT, {})
        if campaign.get("schema_version") == FREEZE_CANDIDATE_SCHEMA:
            preview = freeze_candidate_preview(campaign, load_json(Path(args.acceptance_criteria)), load_json(Path(args.image_lock)), env, env["source_git_commit"], ROOT)
        else:
            preview = freeze_preview(campaign, env, hashlib.sha256(COMPOSE.read_bytes()).hexdigest(), env["source_git_commit"])
        _emit(preview, args.json_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
