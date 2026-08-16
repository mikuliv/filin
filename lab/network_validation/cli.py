from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from .capture import validate_capture_set
from .contracts import CAMPAIGN_SCHEMA, digest, load_json, validate_campaign, validate_scenario
from .execution_package import (
    audit_execution_readiness,
    build_execution_package_preview,
    inspect_label_boundary,
    inspect_run_plan,
    validate_execution_package_preview,
)
from .freeze import environment_lock, freeze_candidate_preview, freeze_preview, official_freeze_payload, validate_official_freeze, write_official_freeze
from .freeze_candidate import FREEZE_CANDIDATE_SCHEMA, candidate_summary, freeze_candidate_proxy_risks, validate_freeze_candidate
from .image_lock import compare_oci_archives, image_lock_blockers, validate_image_lock
from .parameter_verification import observations_from_zeek, verify_parameters
from .phase1_execution_package import (
    OFFICIAL_PACKAGE_PATH as DEFAULT_OFFICIAL_EXECUTION_PACKAGE,
    audit_preflight as audit_phase1_preflight,
    build_candidate_preview as build_phase1_candidate_preview,
    inspect_label_boundary as inspect_phase1_label_boundary,
    inspect_run_plan as inspect_phase1_run_plan,
    materialize_execution_inputs,
    validate_candidate_preview as validate_phase1_candidate_preview,
    validate_official_package,
    write_official_package,
)
from .pipeline import COMPOSE, compose_config, run_factor_orthogonality_smoke, run_technical_smoke
from .planning import plan_campaign, proxy_risks, validate_counterfactuals, validate_infrastructure_profiles, validate_split
from .operational_initialization import (
    audit_initialization_contracts,
    validate_ledger_contract,
    validate_mapping_contract,
)
from .superseding_execution_package import (
    OFFICIAL_PACKAGE_V2_PATH,
    build_preview as build_superseding_package_preview,
    validate_official_package as validate_superseding_execution_package,
    write_official_package as write_superseding_execution_package,
)
from .superseding_freeze import (
    OFFICIAL_PATH as DEFAULT_SUPERSEDING_FREEZE,
    materialize_inputs,
    validate_inputs as validate_superseding_inputs,
    validate_official as validate_official_superseding_freeze,
    write_official as write_official_superseding_freeze,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CAMPAIGN = Path(__file__).with_name("config") / "technical_campaign.json"
DEFAULT_FREEZE_CANDIDATE = Path(__file__).with_name("config") / "freeze_candidate_campaign.json"
DEFAULT_ACCEPTANCE_CRITERIA = Path(__file__).with_name("config") / "acceptance_criteria.json"
DEFAULT_IMAGE_LOCK = Path(__file__).with_name("config") / "image_lock.json"
DEFAULT_OFFICIAL_FREEZE = Path(__file__).with_name("freeze") / "official_freeze.json"


def _resolved_environment(image_lock: dict[str, Any], source_git_commit: str | None = None) -> dict[str, Any]:
    by_name = {row["logical_name"]: row for row in image_lock["images"]}
    images = {
        "zeek": by_name["zeek"]["platform_manifest_digest"],
        "client": by_name["common_client"]["platform_manifest_digest"],
        "targets": {
            "target_a": by_name["target_a"]["platform_manifest_digest"],
            "target_b": by_name["target_b"]["platform_manifest_digest"],
        },
    }
    value = environment_lock(ROOT, images)
    if source_git_commit is not None:
        value["source_git_commit"] = source_git_commit
        value["dirty_working_tree"] = False
        value["canonical_digest"] = digest({key: item for key, item in value.items() if key != "canonical_digest"})
    return value


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
    create = commands.add_parser("create-official-freeze")
    create.add_argument("--campaign", default=str(DEFAULT_FREEZE_CANDIDATE))
    create.add_argument("--acceptance-criteria", default=str(DEFAULT_ACCEPTANCE_CRITERIA))
    create.add_argument("--image-lock", default=str(DEFAULT_IMAGE_LOCK))
    create.add_argument("--output", default=str(DEFAULT_OFFICIAL_FREEZE))
    create.add_argument("--confirm-official-freeze", action="store_true")
    official = commands.add_parser("validate-official-freeze")
    official.add_argument("--campaign", default=str(DEFAULT_FREEZE_CANDIDATE))
    official.add_argument("--acceptance-criteria", default=str(DEFAULT_ACCEPTANCE_CRITERIA))
    official.add_argument("--image-lock", default=str(DEFAULT_IMAGE_LOCK))
    official.add_argument("--freeze", default=str(DEFAULT_OFFICIAL_FREEZE))
    for name in ("audit-execution-readiness", "build-execution-package-preview", "inspect-run-plan"):
        item = commands.add_parser(name)
        item.add_argument("--campaign", default=str(DEFAULT_FREEZE_CANDIDATE))
        item.add_argument("--acceptance-criteria", default=str(DEFAULT_ACCEPTANCE_CRITERIA))
        item.add_argument("--image-lock", default=str(DEFAULT_IMAGE_LOCK))
        item.add_argument("--freeze", default=str(DEFAULT_OFFICIAL_FREEZE))
    package = commands.add_parser("validate-execution-package")
    package.add_argument("--package")
    package.add_argument("--campaign", default=str(DEFAULT_FREEZE_CANDIDATE))
    package.add_argument("--acceptance-criteria", default=str(DEFAULT_ACCEPTANCE_CRITERIA))
    package.add_argument("--image-lock", default=str(DEFAULT_IMAGE_LOCK))
    package.add_argument("--freeze", default=str(DEFAULT_OFFICIAL_FREEZE))
    commands.add_parser("materialize-execution-package-inputs")
    preflight = commands.add_parser("audit-execution-preflight")
    preflight.add_argument("--package", default=str(DEFAULT_OFFICIAL_EXECUTION_PACKAGE))
    create_package = commands.add_parser("create-official-execution-package")
    create_package.add_argument("--output", default=str(DEFAULT_OFFICIAL_EXECUTION_PACKAGE))
    create_package.add_argument("--confirm-official-package", action="store_true")
    commands.add_parser("inspect-label-boundary")
    commands.add_parser("render-compose")
    commands.add_parser("inspect-environment")
    parameter = commands.add_parser("validate-parameter-contract")
    parameter.add_argument("--scenario", required=True); parameter.add_argument("--zeek-dir", required=True)
    capture = commands.add_parser("validate-capture-manifest")
    capture.add_argument("--manifest", required=True); capture.add_argument("--dataset-root", required=True); capture.add_argument("--executions", required=True)
    capture.add_argument("--markers")
    smoke = commands.add_parser("run-technical-smoke")
    smoke.add_argument("--confirm-disposable", action="store_true"); smoke.add_argument("--output-dir", required=True)
    orthogonality = commands.add_parser("run-factor-orthogonality-smoke")
    orthogonality.add_argument("--confirm-disposable", action="store_true"); orthogonality.add_argument("--output-dir", required=True)
    orthogonality.add_argument("--diagnostic-first-only", action="store_true")
    commands.add_parser("materialize-superseding-inputs")
    commands.add_parser("validate-superseding-inputs")
    create_superseding = commands.add_parser("create-official-superseding-freeze")
    create_superseding.add_argument("--output", default=str(DEFAULT_SUPERSEDING_FREEZE))
    create_superseding.add_argument("--confirm-official-freeze", action="store_true")
    validate_superseding = commands.add_parser("validate-official-superseding-freeze")
    validate_superseding.add_argument("--freeze", default=str(DEFAULT_SUPERSEDING_FREEZE))
    commands.add_parser("audit-initialization-contract")
    commands.add_parser("inspect-ledger-contract")
    commands.add_parser("inspect-mapping-contract")
    superseding_preview = commands.add_parser("build-superseding-execution-package-preview")
    superseding_preview.add_argument("--operational-contracts-commit")
    validate_package_v2 = commands.add_parser("validate-superseding-execution-package")
    validate_package_v2.add_argument("--package", default=str(OFFICIAL_PACKAGE_V2_PATH))
    create_package_v2 = commands.add_parser("create-official-superseding-execution-package")
    create_package_v2.add_argument("--output", default=str(OFFICIAL_PACKAGE_V2_PATH))
    create_package_v2.add_argument("--operational-contracts-commit")
    create_package_v2.add_argument("--confirm-official-package", action="store_true")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "render-compose":
        _emit(compose_config(), args.json_output); return 0
    if args.command == "inspect-environment":
        _emit(environment_lock(ROOT, {}), args.json_output); return 0
    if args.command == "run-technical-smoke":
        _emit(run_technical_smoke(args.confirm_disposable, Path(args.output_dir)), args.json_output); return 0
    if args.command == "run-factor-orthogonality-smoke":
        _emit(run_factor_orthogonality_smoke(args.confirm_disposable, Path(args.output_dir), args.diagnostic_first_only), args.json_output); return 0
    if args.command == "materialize-superseding-inputs":
        _emit(materialize_inputs(), args.json_output); return 0
    if args.command == "validate-superseding-inputs":
        _emit(validate_superseding_inputs(), args.json_output); return 0
    if args.command == "create-official-superseding-freeze":
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
        if dirty:
            raise ValueError("official superseding freeze requires a clean working tree")
        source = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
        created_at = subprocess.run(["git", "show", "-s", "--format=%cI", source], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
        value = write_official_superseding_freeze(Path(args.output), source, created_at, args.confirm_official_freeze)
        _emit({"official_superseding_freeze_created": True, "official_superseding_freeze": value}, args.json_output); return 0
    if args.command == "validate-official-superseding-freeze":
        value = validate_official_superseding_freeze(load_json(Path(args.freeze)))
        _emit({"superseding_freeze_valid": True, "execution_protocol_complete": True, "scientific_campaign_started": False, "scientific_pass_allowed": False, "production_approval": False, "official_superseding_freeze": value}, args.json_output); return 0
    if args.command == "audit-initialization-contract":
        _emit(audit_initialization_contracts(), args.json_output); return 0
    if args.command == "inspect-ledger-contract":
        _emit(validate_ledger_contract(), args.json_output); return 0
    if args.command == "inspect-mapping-contract":
        _emit(validate_mapping_contract(), args.json_output); return 0
    if args.command == "build-superseding-execution-package-preview":
        source = args.operational_contracts_commit or subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
        _emit(build_superseding_package_preview(source), args.json_output); return 0
    if args.command == "validate-superseding-execution-package":
        value = validate_superseding_execution_package(Path(args.package))
        _emit({"official_superseding_execution_package_valid": True, "official_superseding_execution_package": value}, args.json_output); return 0
    if args.command == "create-official-superseding-execution-package":
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
        if dirty:
            raise ValueError("official superseding execution package requires a clean working tree")
        source = args.operational_contracts_commit or subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
        created_at = subprocess.run(
            ["git", "show", "-s", "--format=%cI", source], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
        value = write_superseding_execution_package(Path(args.output), source, created_at, args.confirm_official_package)
        _emit({"official_superseding_execution_package_created": True, "official_superseding_execution_package": value}, args.json_output); return 0
    if args.command == "materialize-execution-package-inputs":
        _emit(materialize_execution_inputs(), args.json_output); return 0
    if args.command == "build-execution-package-preview":
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
        source = "unresolved_until_commit" if dirty else subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
        value = build_phase1_candidate_preview(source)
        validate_phase1_candidate_preview(value)
        _emit(value, args.json_output); return 0
    if args.command == "inspect-run-plan":
        _emit(inspect_phase1_run_plan(), args.json_output); return 0
    if args.command == "inspect-label-boundary":
        _emit(inspect_phase1_label_boundary(), args.json_output); return 0
    if args.command == "validate-execution-package":
        if args.package:
            value = validate_official_package(load_json(Path(args.package)))
            _emit({
                "official_execution_package_valid": True,
                "phase": "data_collection",
                "execution_plan_complete": True,
                "scientific_campaign_started": False,
                "labels_created": False,
                "model_required": False,
                "runtime_preflight_required": True,
                "official_execution_package": value,
            }, args.json_output)
        else:
            value = build_phase1_candidate_preview("unresolved_until_commit")
            validate_phase1_candidate_preview(value)
            _emit(value, args.json_output)
        return 0
    if args.command == "audit-execution-preflight":
        _emit(audit_phase1_preflight(load_json(Path(args.package))), args.json_output); return 0
    if args.command == "create-official-execution-package":
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
        if dirty:
            raise ValueError("official execution package requires a clean working tree")
        source = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
        created_at = subprocess.run(["git", "show", "-s", "--format=%cI", source], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
        value = write_official_package(Path(args.output), source, created_at, args.confirm_official_package)
        _emit({"official_execution_package_created": True, "official_execution_package": value}, args.json_output); return 0
    if args.command == "validate-parameter-contract":
        scenario = load_json(Path(args.scenario)); validate_scenario(scenario); _emit(verify_parameters(scenario, observations_from_zeek(Path(args.zeek_dir))), args.json_output); return 0
    if args.command == "validate-capture-manifest":
        manifests = load_json(Path(args.manifest)); executions = load_json(Path(args.executions)); markers = load_json(Path(args.markers)) if args.markers else None; validate_capture_set(manifests, Path(args.dataset_root), executions, markers); _emit({"valid": True, "capture_count": len(manifests)}, args.json_output); return 0
    if args.command in {"audit-execution-readiness"}:
        campaign = load_json(Path(args.campaign)); criteria = load_json(Path(args.acceptance_criteria)); image_lock = load_json(Path(args.image_lock)); official_freeze = load_json(Path(args.freeze))
        source = official_freeze.get("source_git_sha", "")
        result = subprocess.run(["git", "cat-file", "-e", f"{source}^{{commit}}"], cwd=ROOT, capture_output=True, check=False)
        if result.returncode:
            raise ValueError("official freeze source Git SHA does not exist")
        environment = _resolved_environment(image_lock, source)
        validate_official_freeze(official_freeze, campaign, criteria, image_lock, environment, source, ROOT)
        if args.command == "audit-execution-readiness":
            value = audit_execution_readiness(campaign, official_freeze)
        else:
            value = build_execution_package_preview(campaign, official_freeze)
            validate_execution_package_preview(value)
        _emit(value, args.json_output); return 0
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
    if args.command in {"create-official-freeze", "validate-official-freeze"}:
        campaign = load_json(Path(args.campaign)); criteria = load_json(Path(args.acceptance_criteria)); image_lock = load_json(Path(args.image_lock))
        if args.command == "create-official-freeze":
            if _command := subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip():
                raise ValueError(f"official freeze requires a clean working tree: {_command}")
            source = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
            created_at = subprocess.run(["git", "show", "-s", "--format=%cI", source], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
            environment = _resolved_environment(image_lock)
            preview = freeze_candidate_preview(campaign, criteria, image_lock, environment, source, ROOT)
            value = official_freeze_payload(preview, environment, image_lock, source, created_at)
            write_official_freeze(Path(args.output), value, confirmed=args.confirm_official_freeze)
            _emit({"official_freeze_created": True, "path": str(Path(args.output)), "official_freeze": value}, args.json_output); return 0
        value = load_json(Path(args.freeze)); source = value.get("source_git_sha", "")
        result = subprocess.run(["git", "cat-file", "-e", f"{source}^{{commit}}"], cwd=ROOT, capture_output=True, check=False)
        if result.returncode:
            raise ValueError("official freeze source Git SHA does not exist")
        environment = _resolved_environment(image_lock, source)
        validate_official_freeze(value, campaign, criteria, image_lock, environment, source, ROOT)
        _emit({"official_freeze_valid": True, "seal_allowed": True, "scientific_pass_allowed": False, "production_approval": value["production_approval"], "official_freeze": value}, args.json_output); return 0
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
        image_lock = load_json(Path(args.image_lock)) if hasattr(args, "image_lock") else None
        env = _resolved_environment(image_lock) if image_lock is not None else environment_lock(ROOT, {})
        if campaign.get("schema_version") == FREEZE_CANDIDATE_SCHEMA:
            preview = freeze_candidate_preview(campaign, load_json(Path(args.acceptance_criteria)), load_json(Path(args.image_lock)), env, env["source_git_commit"], ROOT)
        else:
            preview = freeze_preview(campaign, env, hashlib.sha256(COMPOSE.read_bytes()).hexdigest(), env["source_git_commit"])
        _emit(preview, args.json_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
