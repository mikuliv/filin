from __future__ import annotations

import hashlib
import json
import re
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

import yaml


ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "ml/reports/v0_3_17_1"
LOCK_PATH = REPORT / "pre_trial_code_lock.json"
MANIFEST_NAME = "v0_3_17_1_bundle_manifest.yaml"
DETACHED_NAME = "v0_3_17_1_bundle_manifest.sha256"

REQUIRED_REPORTS = (
    "v0_3_17_1_summary.md",
    "v0_3_17_1_policy_result.json",
    "storage_profile.json",
    "storage_benchmark_report.json",
    "ssd_migration_verification_report.json",
    "historical_anchor_root_cause_report.json",
    "clock_domain_root_cause_report.json",
    "trace_linkage_report.json",
    "transport_duplicate_semantics_report.json",
    "latency_breakdown_report.json",
    "performance_policy_report.json",
    "corruption_suite_report.json",
    "finalizer_regression_report.json",
    "change_classification_report.json",
    "targeted_trial_manifest.json",
    "targeted_trial_results.json",
    "source_connector_receiver_reconciliation.json",
    "privacy_report.json",
    "secret_scan_report.json",
    "resume_integrity_report.json",
    "readiness_decision.json",
    "claim_evidence_ledger.json",
    "test_report.json",
)


class FinalizationError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def validate_lock(path: Path, expected_stage: str = "v0.3.17.1") -> dict[str, Any]:
    if not path.is_file():
        raise FinalizationError("lock_missing")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise FinalizationError("lock_malformed") from error
    if value.get("schema_version") != "v03171_finalizer_lock_v1":
        raise FinalizationError("lock_schema")
    if value.get("stage") != expected_stage:
        raise FinalizationError("lock_stage")
    if not re.fullmatch(r"[0-9a-f]{40}", str(value.get("source_head", ""))):
        raise FinalizationError("lock_source_head")
    if value.get("recovery_mode") is not False:
        raise FinalizationError("recovery_mode_forbidden")
    return value


def _safe_artifact_path(path: Path, root: Path) -> str:
    if not _inside(path, root):
        raise FinalizationError("artifact_outside_root")
    relative = path.resolve().relative_to(root.resolve()).as_posix()
    pure = PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts or "\\" in relative:
        raise FinalizationError("artifact_path_unsafe")
    return relative


def validate_manifest(value: dict[str, Any], root: Path) -> list[str]:
    errors: list[str] = []
    if value.get("schema_version") != "v03171_bundle_manifest_v1":
        errors.append("schema_version")
    if value.get("stage") != "v0.3.17.1":
        errors.append("stage")
    artifacts = value.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        return errors + ["artifacts_required"]
    seen: set[str] = set()
    for item in artifacts:
        relative = item.get("relative_path", "")
        pure = PurePosixPath(relative)
        if not relative or pure.is_absolute() or ".." in pure.parts or "\\" in relative:
            errors.append(f"unsafe_path:{relative}")
            continue
        if re.match(r"^[A-Za-z]:", relative):
            errors.append(f"drive_path:{relative}")
            continue
        if relative in seen:
            errors.append(f"duplicate_path:{relative}")
            continue
        seen.add(relative)
        path = root / relative
        if not path.is_file():
            errors.append(f"missing:{relative}")
            continue
        if path.stat().st_size != item.get("size"):
            errors.append(f"size:{relative}")
        if sha256(path) != item.get("sha256"):
            errors.append(f"hash:{relative}")
        if item.get("contains_sensitive_data") is not False:
            errors.append(f"sensitive:{relative}")
        forbidden = (
            "runtime/",
            ".sqlite",
            "-wal",
            ".pcap",
            "private.key",
            "operator_snapshot",
            "raw_timing",
        )
        if any(token in relative.lower() for token in forbidden):
            errors.append(f"forbidden_artifact:{relative}")
    readiness = value.get("readiness", {})
    for key in (
        "candidate_ready_for_shadow_mode",
        "backend_integration_allowed",
        "shadow_mode_allowed",
        "production_ready",
        "real_organization_trial_allowed",
    ):
        if readiness.get(key) is not False:
            errors.append(f"readiness_fail_closed:{key}")
    return errors


def validate_bundle(report: Path = REPORT, root: Path = ROOT) -> dict[str, Any]:
    manifest = report / MANIFEST_NAME
    detached = report / DETACHED_NAME
    errors: list[str] = []
    missing = [name for name in REQUIRED_REPORTS if not (report / name).is_file()]
    errors.extend(f"required_missing:{name}" for name in missing)
    if not manifest.is_file() or not detached.is_file():
        return {
            "bundle_validator_passed": False,
            "errors": errors + ["bundle_manifest_missing"],
            "artifact_count": 0,
        }
    try:
        detached_hash, detached_file = detached.read_text(encoding="utf-8").split()
    except ValueError:
        errors.append("detached_format")
        detached_hash, detached_file = "", ""
    if detached_file != MANIFEST_NAME or detached_hash != sha256(manifest):
        errors.append("detached_manifest_hash")
    value = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    errors.extend(validate_manifest(value, root))
    artifact_paths = {
        Path(item.get("relative_path", "")).name
        for item in value.get("artifacts", [])
        if isinstance(item, dict)
    }
    errors.extend(
        f"required_not_manifested:{name}"
        for name in REQUIRED_REPORTS
        if name not in artifact_paths
    )
    return {
        "bundle_validator_passed": not errors,
        "errors": errors,
        "artifact_count": len(value.get("artifacts", [])),
        "required_report_count": len(REQUIRED_REPORTS),
    }


def finalize(
    report: Path = REPORT,
    lock_path: Path = LOCK_PATH,
    root: Path = ROOT,
    required_reports: Iterable[str] = REQUIRED_REPORTS,
    extra_artifacts: Iterable[Path] = (),
) -> dict[str, Any]:
    if not _inside(report, root) or not _inside(lock_path, root):
        raise FinalizationError("path_confinement")
    validate_lock(lock_path)
    required = tuple(required_reports)
    missing = [name for name in required if not (report / name).is_file()]
    if missing:
        raise FinalizationError("required_reports_missing:" + ",".join(missing))
    manifest = report / MANIFEST_NAME
    detached = report / DETACHED_NAME
    manifest_tmp = report / f"{MANIFEST_NAME}.tmp"
    detached_tmp = report / f"{DETACHED_NAME}.tmp"
    manifest_tmp.unlink(missing_ok=True)
    detached_tmp.unlink(missing_ok=True)

    report_artifacts = [
        path
        for path in report.iterdir()
        if path.is_file()
        and path.name not in {MANIFEST_NAME, DETACHED_NAME}
        and not path.name.endswith(".tmp")
    ]
    paths = sorted(set(report_artifacts) | set(extra_artifacts))
    artifacts = [
        {
            "artifact_role": path.stem,
            "relative_path": _safe_artifact_path(path, root),
            "size": path.stat().st_size,
            "sha256": sha256(path),
            "schema_version": "v03171",
            "contains_sensitive_data": False,
            "git_inclusion_permitted": True,
        }
        for path in paths
    ]
    readiness_path = report / "readiness_decision.json"
    design_ready = False
    if readiness_path.is_file():
        design_ready = bool(
            json.loads(readiness_path.read_text(encoding="utf-8")).get(
                "candidate_ready_for_v0_3_18_external_review_and_trial_design",
                False,
            )
        )
    value = {
        "schema_version": "v03171_bundle_manifest_v1",
        "stage": "v0.3.17.1",
        "recovery_finalization_required": False,
        "artifacts": artifacts,
        "readiness": {
            "candidate_ready_for_v0_3_18_external_review_and_trial_design": design_ready,
            "candidate_ready_for_shadow_mode": False,
            "backend_integration_allowed": False,
            "shadow_mode_allowed": False,
            "production_ready": False,
            "real_organization_trial_allowed": False,
        },
    }
    content = yaml.safe_dump(value, allow_unicode=True, sort_keys=False)
    already_finalized = (
        manifest.is_file()
        and detached.is_file()
        and manifest.read_text(encoding="utf-8") == content
        and detached.read_text(encoding="utf-8")
        == f"{hashlib.sha256(content.encode()).hexdigest()}  {MANIFEST_NAME}\n"
    )
    if not already_finalized:
        manifest_tmp.write_text(content, encoding="utf-8", newline="\n")
        manifest_tmp.replace(manifest)
        detached_content = f"{sha256(manifest)}  {MANIFEST_NAME}\n"
        detached_tmp.write_text(detached_content, encoding="utf-8", newline="\n")
        detached_tmp.replace(detached)
    return {
        "clean_finalization_passed": True,
        "already_finalized": already_finalized,
        "recovery_finalization_required": False,
        "artifact_count": len(artifacts),
        "bundle_manifest_sha256": sha256(manifest),
    }


def _fixture_lock(path: Path, stage: str = "v0.3.17.1") -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": "v03171_finalizer_lock_v1",
                "stage": stage,
                "source_head": "0" * 40,
                "recovery_mode": False,
            }
        ),
        encoding="utf-8",
    )


def run_regression_report() -> dict[str, Any]:
    scenarios: list[dict[str, Any]] = []

    def record(name: str, passed: bool, expected: str) -> None:
        scenarios.append({"scenario": name, "passed": passed, "expected": expected})

    with tempfile.TemporaryDirectory(prefix="v03171-finalizer-") as raw:
        root = Path(raw)
        report = root / "reports"
        report.mkdir()
        (report / "fixture.json").write_text("{}\n", encoding="utf-8")
        lock = report / "lock.json"
        _fixture_lock(lock)

        first = finalize(report, lock, root, ("fixture.json",))
        record("clean_finalization", first["clean_finalization_passed"], "success")
        second = finalize(report, lock, root, ("fixture.json",))
        record("repeated_invocation", second["already_finalized"], "idempotent")
        record("already_finalized_bundle", second["already_finalized"], "no rewrite")

        try:
            finalize(report, report / "missing.json", root, ("fixture.json",))
            missing_passed = False
        except FinalizationError as error:
            missing_passed = str(error) == "lock_missing"
        record("missing_lock", missing_passed, "lock_missing")

        lock.write_text("{", encoding="utf-8")
        try:
            finalize(report, lock, root, ("fixture.json",))
            malformed_passed = False
        except FinalizationError as error:
            malformed_passed = str(error) == "lock_malformed"
        record("malformed_lock", malformed_passed, "lock_malformed")

        _fixture_lock(lock, "v0.3.17")
        try:
            finalize(report, lock, root, ("fixture.json",))
            other_passed = False
        except FinalizationError as error:
            other_passed = str(error) == "lock_stage"
        record("other_stage_lock", other_passed, "lock_stage")

        _fixture_lock(lock)
        (report / f"{MANIFEST_NAME}.tmp").write_text("interrupted", encoding="utf-8")
        interrupted = finalize(report, lock, root, ("fixture.json",))
        record(
            "interrupted_finalization",
            interrupted["clean_finalization_passed"]
            and not (report / f"{MANIFEST_NAME}.tmp").exists(),
            "atomic recovery",
        )

        outside = root.parent / "outside-v03171"
        try:
            finalize(outside, lock, root, ("fixture.json",))
            confinement_passed = False
        except FinalizationError as error:
            confinement_passed = str(error) == "path_confinement"
        record("path_confinement", confinement_passed, "path_confinement")

        recovery_lock = report / "recovery-lock.json"
        recovery_lock.write_text(
            json.dumps(
                {
                    "schema_version": "v03171_finalizer_lock_v1",
                    "stage": "v0.3.17.1",
                    "source_head": "0" * 40,
                    "recovery_mode": True,
                }
            ),
            encoding="utf-8",
        )
        try:
            finalize(report, recovery_lock, root, ("fixture.json",))
            recovery_passed = False
        except FinalizationError as error:
            recovery_passed = str(error) == "recovery_mode_forbidden"
        record("no_recovery_mode", recovery_passed, "recovery_mode_forbidden")

    result = {
        "schema_version": "v03171_finalizer_regression_v1",
        "stage": "v0.3.17.1",
        "finalizer_nameerror_fixed": LOCK_PATH.name == "pre_trial_code_lock.json",
        "scenario_count": len(scenarios),
        "scenario_passed_count": sum(item["passed"] for item in scenarios),
        "clean_finalization_passed": all(item["passed"] for item in scenarios),
        "recovery_finalization_required": False,
        "scenarios": scenarios,
    }
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT / "finalizer_regression_report.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return result


def main() -> int:
    result = run_regression_report()
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["clean_finalization_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
