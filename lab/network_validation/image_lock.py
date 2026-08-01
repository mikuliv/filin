from __future__ import annotations

import hashlib
import json
import re
import tarfile
from datetime import datetime
from pathlib import Path
from typing import Any

from .contracts import ContractError, digest

IMAGE_LOCK_SCHEMA = "network_validation_portable_image_lock_v2"
DIGEST_PREFIX = "sha256:"
LOCAL_IMAGES = {"common_client", "target_a", "target_b", "sensor_capture"}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_inputs_manifest(root: Path, relative_paths: list[str]) -> list[dict[str, Any]]:
    rows = []
    for relative in sorted(set(relative_paths)):
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts:
            raise ContractError("build input path must be repository-relative")
        lowered = path.as_posix().lower()
        if any(part in {".git", "__pycache__", ".pytest_cache", "runtime", "coverage"} for part in path.parts) or path.suffix.lower() in {".pyc", ".pcap", ".oci"} or "zeek" in lowered and path.suffix.lower() == ".log":
            raise ContractError("forbidden build input")
        actual = root / path
        if not actual.is_file():
            raise ContractError(f"build input missing: {relative}")
        data = actual.read_bytes()
        rows.append({"path": path.as_posix(), "sha256": _sha(data), "size": len(data)})
    return rows


def build_inputs_digest(root: Path, relative_paths: list[str]) -> str:
    return digest(build_inputs_manifest(root, relative_paths))


def _valid_digest(value: Any, *, unresolved: bool = True) -> bool:
    return (unresolved and value == "unresolved") or isinstance(value, str) and len(value) == 71 and value.startswith(DIGEST_PREFIX) and all(character in "0123456789abcdef" for character in value[7:])


def _valid_repo_digest(value: Any, *, unresolved: bool = True) -> bool:
    if unresolved and value == "unresolved":
        return True
    if not isinstance(value, str) or "@" not in value:
        return False
    repository, value_digest = value.rsplit("@", 1)
    return bool(repository) and _valid_digest(value_digest, unresolved=False)


def image_lock_identity(value: dict[str, Any]) -> dict[str, Any]:
    identity = json.loads(json.dumps(value))
    identity.pop("canonical_digest", None)
    identity.pop("checked_at", None)
    for image in identity.get("images", []):
        image.pop("verified_at", None)
    return identity


def validate_image_lock(value: dict[str, Any], root: Path | None = None) -> dict[str, Any]:
    required = {"schema_version", "checked_at", "source_git_commit", "source_tree_clean", "dirty_working_tree", "platform", "build_tool_version", "images", "canonical_digest"}
    if set(value) != required or value["schema_version"] != IMAGE_LOCK_SCHEMA or value["platform"] != "linux/amd64":
        raise ContractError("image lock fields mismatch")
    if not isinstance(value["dirty_working_tree"], bool) or not isinstance(value["source_tree_clean"], bool) or not isinstance(value["images"], list):
        raise ContractError("image lock types mismatch")
    try:
        datetime.fromisoformat(value["checked_at"].replace("Z", "+00:00"))
    except (AttributeError, ValueError) as error:
        raise ContractError("invalid image lock timestamp") from error
    if not re.fullmatch(r"[a-f0-9]{40}", str(value["source_git_commit"])) or not isinstance(value["build_tool_version"], str) or not value["build_tool_version"]:
        raise ContractError("invalid image lock provenance")
    image_fields = {
        "logical_name", "source_type", "source", "repository", "tag", "platform",
        "dockerfile_path", "build_inputs", "build_inputs_digest", "source_git_commit",
        "build_context", "source_tree_clean", "base_image_repo_digest", "base_image_platform_manifest_digest",
        "repo_digest", "oci_index_digest", "platform_manifest_digest", "config_digest",
        "local_image_id", "layer_digests", "requirements_lock_digest",
        "reproducibility_build_count", "runtime_config", "reproducibility_evidence",
        "verification_method", "verification_status", "verified_at", "blocker",
    }
    names = set()
    for image in value["images"]:
        if set(image) != image_fields or image["logical_name"] in names or image["platform"] != value["platform"]:
            raise ContractError("invalid image lock entry")
        names.add(image["logical_name"])
        if image["source_type"] not in {"registry", "oci_build"} or image["verification_status"] not in {"resolved_registry", "resolved_reproducible", "unresolved_daemon_unavailable", "unresolved_non_reproducible"}:
            raise ContractError("invalid image lock status")
        try:
            datetime.fromisoformat(image["verified_at"].replace("Z", "+00:00"))
        except (AttributeError, ValueError) as error:
            raise ContractError("invalid image verification timestamp") from error
        if not isinstance(image["verification_method"], str) or not image["verification_method"]:
            raise ContractError("image verification method is missing")
        if image["dockerfile_path"] is not None:
            dockerfile = Path(image["dockerfile_path"])
            if dockerfile.is_absolute() or ".." in dockerfile.parts:
                raise ContractError("image Dockerfile path must be repository-relative")
        if any(Path(item).is_absolute() or ".." in Path(item).parts for item in image["build_inputs"]):
            raise ContractError("image build input path must be repository-relative")
        if image["build_context"] is not None and (Path(image["build_context"]).is_absolute() or ".." in Path(image["build_context"]).parts):
            raise ContractError("image build context must be repository-relative")
        if not isinstance(image["source_tree_clean"], bool) or not isinstance(image["reproducibility_build_count"], int):
            raise ContractError("invalid image reproducibility provenance")
        if not _valid_repo_digest(image["repo_digest"]):
            raise ContractError("invalid repository digest")
        for field in ("oci_index_digest", "platform_manifest_digest", "config_digest", "local_image_id"):
            if not _valid_digest(image[field]):
                raise ContractError(f"invalid image digest field: {field}")
        if any(not _valid_digest(item, unresolved=False) for item in image["layer_digests"]):
            raise ContractError("invalid layer digest")
        if image["requirements_lock_digest"] != "not_applicable" and not _valid_digest(image["requirements_lock_digest"], unresolved=False):
            raise ContractError("invalid requirements lock digest")
        if image["verification_status"] == "resolved_reproducible" and (image["platform_manifest_digest"] == "unresolved" or image["config_digest"] == "unresolved" or not image["layer_digests"]):
            raise ContractError("resolved image lacks OCI digests")
        if image["verification_status"].startswith("unresolved_") and not image["blocker"]:
            raise ContractError("unresolved image lacks blocker")
        if image["verification_status"].startswith("resolved_") and image["blocker"] is not None:
            raise ContractError("resolved image must not carry a blocker")
        if image["source_type"] == "registry":
            if image["repository"] is None or image["tag"] is None or image["build_inputs_digest"] != "not_applicable" or image["source_git_commit"] is not None or image["build_context"] is not None:
                raise ContractError("registry image provenance is invalid")
            if image["verification_status"] == "resolved_registry" and (not _valid_repo_digest(image["repo_digest"], unresolved=False) or not _valid_digest(image["platform_manifest_digest"], unresolved=False) or not _valid_digest(image["config_digest"], unresolved=False)):
                raise ContractError("resolved registry image lacks portable identity")
            if image["verification_status"] == "resolved_registry" and (image["source"] != f"{image['repository']}:{image['tag']}" or image["repo_digest"].rsplit("@", 1)[0] != image["repository"] or image["repo_digest"].rsplit("@", 1)[1] != image["oci_index_digest"]):
                raise ContractError("registry repository, tag, and index identity disagree")
            if image["local_image_id"] != "unresolved":
                raise ContractError("registry identity must not be inferred from a local image ID")
            if image["reproducibility_build_count"] != 0 or image["reproducibility_evidence"] or image["base_image_repo_digest"] != "not_applicable" or image["base_image_platform_manifest_digest"] != "not_applicable":
                raise ContractError("registry image reproducibility fields are invalid")
        elif image["repository"] is not None or image["tag"] is not None or image["verification_status"] == "resolved_registry" or not re.fullmatch(r"[a-f0-9]{40}", str(image["source_git_commit"])):
            raise ContractError("local image source identity is invalid")
        elif image["verification_status"] == "resolved_reproducible":
            if image["reproducibility_build_count"] < 2 or not image["source_tree_clean"] or not _valid_repo_digest(image["base_image_repo_digest"], unresolved=False) or not _valid_digest(image["base_image_platform_manifest_digest"], unresolved=False):
                raise ContractError("resolved image lacks reproducible source provenance")
            if len(image["reproducibility_evidence"]) != image["reproducibility_build_count"]:
                raise ContractError("resolved image build evidence count mismatch")
            expected = {key: image[key] for key in ("oci_index_digest", "platform_manifest_digest", "config_digest", "layer_digests")}
            expected["runtime_config"] = image["runtime_config"]
            if any(evidence != expected for evidence in image["reproducibility_evidence"]):
                raise ContractError("resolved image builds do not have identical portable identities")
        if root is not None and image["source_type"] == "oci_build":
            if build_inputs_digest(root, image["build_inputs"]) != image["build_inputs_digest"]:
                raise ContractError(f"stale build-inputs digest: {image['logical_name']}")
    if names != LOCAL_IMAGES | {"zeek"}:
        raise ContractError("image lock set is incomplete")
    if value["canonical_digest"] != digest(image_lock_identity(value)):
        raise ContractError("image lock canonical digest mismatch")
    return value


def image_lock_blockers(value: dict[str, Any]) -> list[str]:
    validate_image_lock(value)
    blockers = []
    for image in value["images"]:
        if image["logical_name"] == "zeek":
            if image["verification_status"] != "resolved_registry" or image["repo_digest"] == "unresolved" or image["platform_manifest_digest"] == "unresolved" or image["config_digest"] == "unresolved":
                blockers.append("zeek_registry_identity")
        elif image["verification_status"] != "resolved_reproducible" or image["platform_manifest_digest"] == "unresolved":
            blockers.append(f"{image['logical_name']}_reproducibility")
    return blockers


def _read_tar_json(archive: Path, name: str) -> tuple[bytes, dict[str, Any]]:
    with tarfile.open(archive, "r:*") as source:
        member = source.getmember(name)
        handle = source.extractfile(member)
        if handle is None:
            raise ContractError(f"OCI member missing: {name}")
        data = handle.read()
    return data, json.loads(data)


def parse_oci_archive(archive: Path, platform: str = "linux/amd64") -> dict[str, Any]:
    index_bytes, index = _read_tar_json(archive, "index.json")
    os_name, architecture = platform.split("/", 1)
    descriptors = [item for item in index.get("manifests", []) if item.get("platform", {}).get("os") == os_name and item.get("platform", {}).get("architecture") == architecture]
    if len(descriptors) != 1:
        raise ContractError("OCI archive has no unique requested platform")
    manifest_digest = descriptors[0]["digest"]
    manifest_bytes, manifest = _read_tar_json(archive, f"blobs/sha256/{manifest_digest.split(':', 1)[1]}")
    if f"sha256:{_sha(manifest_bytes)}" != manifest_digest:
        raise ContractError("OCI manifest digest mismatch")
    config_digest = manifest["config"]["digest"]
    config_bytes, config = _read_tar_json(archive, f"blobs/sha256/{config_digest.split(':', 1)[1]}")
    if f"sha256:{_sha(config_bytes)}" != config_digest:
        raise ContractError("OCI config digest mismatch")
    if config.get("os") != os_name or config.get("architecture") != architecture:
        raise ContractError("OCI config platform mismatch")
    runtime = config.get("config", {})
    return {
        "oci_index_digest": f"sha256:{_sha(index_bytes)}",
        "platform_manifest_digest": manifest_digest,
        "config_digest": config_digest,
        "layer_digests": [item["digest"] for item in manifest["layers"]],
        "architecture": config["architecture"],
        "os": config["os"],
        "entrypoint": runtime.get("Entrypoint"),
        "command": runtime.get("Cmd"),
        "environment": runtime.get("Env", []),
        "labels": runtime.get("Labels") or {},
    }


def compare_oci_archives(left: Path, right: Path, platform: str = "linux/amd64") -> dict[str, Any]:
    first, second = parse_oci_archive(left, platform), parse_oci_archive(right, platform)
    compared_fields = (
        "oci_index_digest", "platform_manifest_digest", "config_digest", "layer_digests",
        "architecture", "os", "entrypoint", "command", "environment", "labels",
    )
    matched = all(first[field] == second[field] for field in compared_fields)
    return {"status": "resolved_reproducible" if matched else "unresolved_non_reproducible", "matched": matched, "first": first, "second": second}
