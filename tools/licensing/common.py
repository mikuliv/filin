"""Shared deterministic helpers for the repository licensing audit."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
HOLDER = "Руслан Покатилов"
BASELINE = "4948af7434c8e7b38731d8df8aae0b3360f2badf"
CANDIDATE = "65a3dd912d845bc1"
BACKEND_TREE = "04218a4eb01534950efd5f7d6390f1a575cacbc8"

UPSTREAM_STANDARD_TEXTS: dict[str, dict[str, str]] = {
    "LICENSE": {
        "sha256": "3f3d9e0024b1921b067d6f7f88deb4a60cbe7a78e76c64e3f1d7fc3b779b9d04",
        "document_kind": "standard_license_text", "upstream_name": "Mozilla Public License 2.0",
        "upstream_copyright_holder": "Mozilla Foundation and contributors",
        "license_expression": "MPL-2.0", "upstream_reference": "https://www.mozilla.org/MPL/2.0/",
    },
    "LICENSES/MPL-2.0.txt": {
        "sha256": "3f3d9e0024b1921b067d6f7f88deb4a60cbe7a78e76c64e3f1d7fc3b779b9d04",
        "document_kind": "standard_license_text", "upstream_name": "Mozilla Public License 2.0",
        "upstream_copyright_holder": "Mozilla Foundation and contributors",
        "license_expression": "MPL-2.0", "upstream_reference": "https://www.mozilla.org/MPL/2.0/",
    },
    "LICENSES/CC-BY-4.0.txt": {
        "sha256": "9ba9550ad48438d0836ddab3da480b3b69ffa0aac7b7878b5a0039e7ab429411",
        "document_kind": "standard_license_text", "upstream_name": "Creative Commons Attribution 4.0 International",
        "upstream_copyright_holder": "Creative Commons",
        "license_expression": "CC-BY-4.0", "upstream_reference": "https://creativecommons.org/licenses/by/4.0/legalcode",
    },
    "DCO.txt": {
        "sha256": "c33e3ea46847ac93235d1a6a7f7f58502514f75c1a374759d29015d681dd4129",
        "document_kind": "contributor_certificate_text", "upstream_name": "Developer Certificate of Origin 1.1",
        "upstream_copyright_holder": "The Linux Foundation and contributors",
        "license_expression": "LicenseRef-DCO-1.1", "upstream_reference": "https://developercertificate.org/",
    },
}

CODE_SUFFIXES = {".py", ".js", ".css", ".html", ".yml", ".yaml", ".json", ".toml", ".conf", ".example"}
DOC_SUFFIXES = {".md", ".rst"}
MODEL_SUFFIXES = {".onnx", ".pt", ".pth", ".joblib", ".pkl", ".pickle", ".safetensors", ".h5"}
DATA_SUFFIXES = {".pcap", ".pcapng", ".parquet", ".db", ".sqlite", ".sqlite3"}
ASSET_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".woff", ".woff2", ".ttf", ".otf"}
SECRET_RE = re.compile(r"(^|/)(\.env(?:\.(?!example$).*)?|id_rsa|id_ed25519|.*\.(?:pem|key|p12|pfx))$", re.I)


def run(*args: str, check: bool = True) -> str:
    process = subprocess.run(args, cwd=ROOT, text=True, encoding="utf-8", errors="replace", capture_output=True)
    if check and process.returncode:
        raise RuntimeError(f"command_failed:{' '.join(args)}\n{process.stderr.strip()}")
    return process.stdout


def git(*args: str, check: bool = True) -> str:
    return run("git", *args, check=check)


def tracked(include_untracked: bool = False) -> list[str]:
    args = ["ls-files", "-z"]
    if include_untracked:
        args += ["--cached", "--others", "--exclude-standard"]
    return sorted(x for x in git(*args).split("\0") if x)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def dump(path: str | Path, data: Any) -> None:
    target = ROOT / path if not isinstance(path, Path) or not path.is_absolute() else path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def load(path: str | Path) -> Any:
    target = ROOT / path if not isinstance(path, Path) or not path.is_absolute() else path
    return json.loads(target.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def protected_rows() -> list[dict[str, Any]]:
    from tools.docs.documentation_v2 import build_protected_set
    return build_protected_set(ROOT)


@lru_cache(maxsize=1)
def protected_paths() -> set[str]:
    return {row["path"].replace("\\", "/") for row in protected_rows()}


def is_generated(path: str) -> bool:
    return path.startswith(("docs/audit/", "docs/licensing/", "licensing/", "sbom/")) and path.endswith((".json", ".md"))


def classify(path: str) -> dict[str, Any]:
    p = path.replace("\\", "/")
    suffix = Path(p).suffix.lower()
    name = Path(p).name
    frozen = p in protected_paths()
    generated = is_generated(p)
    if p in UPSTREAM_STANDARD_TEXTS:
        meta = UPSTREAM_STANDARD_TEXTS[p]
        file_type = "policy_text" if p == "DCO.txt" else "license_text"
        return record(file_type, "upstream_license", meta["upstream_copyright_holder"],
                      meta["license_expression"], frozen, True, generated,
                      ["source-core", "laboratory-source"], ownership="upstream_standard_text",
                      extra={"project_authored": False, "upstream_standard_text": True,
                             "included_for_compliance": True, "text_modification_allowed": False,
                             "document_kind": meta["document_kind"], "upstream_name": meta["upstream_name"],
                             "upstream_reference": meta["upstream_reference"]})
    if SECRET_RE.search(p):
        return record("secret_or_runtime", "excluded_unresolved", "", "LicenseRef-Excluded-Secret", frozen, False, generated, [], True)
    if suffix in MODEL_SUFFIXES:
        return record("model_binary", "generated_policy", HOLDER, "LicenseRef-Separate-License-Required", frozen, False, generated, [], False)
    if suffix in DATA_SUFFIXES or (suffix == ".csv" and (p.startswith("datasets/") or "/data/" in p)):
        return record("dataset", "generated_policy", HOLDER, "LicenseRef-Separate-License-Required", frozen, False, generated, [], False)
    if suffix in ASSET_SUFFIXES:
        return record("static_asset", "reuse_toml", HOLDER, "CC-BY-4.0", frozen, False, generated, ["source-core", "laboratory-source"])
    if suffix in DOC_SUFFIXES or name in {"NOTICE", "AUTHORS", "COPYRIGHT"}:
        return record("documentation", "reuse_toml", HOLDER, "CC-BY-4.0", frozen, False, generated, ["source-core", "laboratory-source"])
    if suffix in CODE_SUFFIXES or name.startswith("Dockerfile") or name in {"LICENSE", ".gitignore"} or suffix in {"", ".txt", ".sha256", ".sensor-capture"}:
        return record("source_or_configuration", "reuse_toml", HOLDER, "MPL-2.0", frozen, False, generated, ["source-core", "laboratory-source"])
    return record("other", "generated_policy", HOLDER, "MPL-2.0", frozen, False, generated, ["source-core", "laboratory-source"])


def record(file_type: str, assignment: str, holder: str, license_expression: str, frozen: bool,
           third_party: bool, generated: bool, profiles: list[str], review: bool = False,
           ownership: str | None = None, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = {"file_type": file_type, "ownership": ownership or ("third_party_component" if third_party else "project_owned"),
            "copyright_holder": holder, "license_expression": license_expression,
            "assignment_source": assignment, "frozen": frozen, "third_party": third_party,
            "generated": generated, "project_authored": not third_party,
            "upstream_standard_text": False, "included_for_compliance": False,
            "text_modification_allowed": not frozen and not third_party,
            "distribution_profiles": profiles, "review_required": review}
    payload.update(extra or {})
    return payload


def result(tool: str, errors: Iterable[dict[str, Any] | str], details: dict[str, Any] | None = None) -> dict[str, Any]:
    normalized = [e if isinstance(e, dict) else {"code": str(e)} for e in errors]
    return {"schema_version": "filin_licensing_validation_v1", "tool": tool,
            "passed": not normalized, "errors": normalized, "details": details or {}}


def finish(tool: str, errors: Iterable[dict[str, Any] | str], details: dict[str, Any] | None, strict: bool,
           output: str | None = None) -> int:
    payload = result(tool, errors, details)
    if output:
        dump(output, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 1 if strict and not payload["passed"] else 0


def parser(description: str) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--strict", action="store_true")
    p.add_argument("--root", type=Path, default=ROOT)
    return p


def forbidden_text(value: str) -> list[str]:
    findings: list[str] = []
    if re.search(r"[A-Z]:[\\/]", value) or "/Users/" in value or "/home/" in value:
        findings.append("absolute_local_path")
    if re.search(r"(?i)(api[_-]?key|token|password)\s*[:=]\s*[^\s,}\"]{8,}", value):
        findings.append("secret_in_artifact")
    return findings
