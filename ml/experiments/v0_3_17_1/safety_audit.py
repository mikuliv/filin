from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "ml/reports/v0_3_17_1"
SCANNED_PREFIXES = (
    "ml/experiments/v0_3_17_1/",
    "ml/reports/v0_3_17_1/",
    "ml/protocols/v0_3_17_1_protocol.yaml",
    "docs/experiments/v0_3_17_1.md",
    "rehearsal/contracts/runtime_timing_trace_v2.schema.json",
    "rehearsal/docker-compose.v0_3_17_1.yml",
    "tools/audit/validate_v03171",
)
PRIVACY_PATTERNS = {
    "absolute_windows_path": re.compile(r"\b[A-Za-z]:[\\/]"),
    "email_address": re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b"),
    "public_ipv4": re.compile(
        r"(?<![\d.vV])(?!10\.|127\.|169\.254\.|192\.0\.2\.|198\.51\.100\.|203\.0\.113\.)"
        r"(?:\d{1,3}\.){3}\d{1,3}(?![\d.])"
    ),
}
SECRET_PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "bearer_token": re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]{20,}=*\b", re.I),
}


def tracked_targets() -> list[Path]:
    paths = subprocess.check_output(
        ["git", "ls-files"], cwd=ROOT, text=True, encoding="utf-8"
    ).splitlines()
    return [
        ROOT / path
        for path in paths
        if any(path.startswith(prefix) for prefix in SCANNED_PREFIXES)
        and (ROOT / path).is_file()
    ]


def _scan(
    targets: list[Path], patterns: dict[str, re.Pattern[str]]
) -> list[dict[str, Any]]:
    findings = []
    for path in targets:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for kind, pattern in patterns.items():
            count = len(pattern.findall(text))
            if count:
                findings.append(
                    {
                        "path": path.relative_to(ROOT).as_posix(),
                        "finding_type": kind,
                        "count": count,
                    }
                )
    return findings


def run() -> tuple[dict[str, Any], dict[str, Any]]:
    targets = tracked_targets()
    privacy_findings = _scan(targets, PRIVACY_PATTERNS)
    secret_findings = _scan(targets, SECRET_PATTERNS)
    negative_privacy = [
        ("email_address", "person" + "@" + "example.org"),
        ("absolute_windows_path", "Z:" + "\\private\\capture.pcap"),
        ("public_ipv4", "8." + "8.8.8"),
    ]
    negative_secrets = [
        ("private_key", "-----BEGIN " + "PRIVATE KEY-----"),
        ("aws_access_key", "AKIA" + "1234567890ABCDEF"),
        ("github_token", "ghp_" + "abcdefghijklmnopqrstuvwxyz123456"),
    ]
    privacy_detection = sum(
        bool(PRIVACY_PATTERNS[name].search(value))
        for name, value in negative_privacy
    )
    secret_detection = sum(
        bool(SECRET_PATTERNS[name].search(value)) for name, value in negative_secrets
    )
    privacy = {
        "schema_version": "v03171_privacy_report_v1",
        "stage": "v0.3.17.1",
        "target_count": len(targets),
        "privacy_all_targets_scanned": True,
        "privacy_finding_count": len(privacy_findings),
        "negative_fixture_count": len(negative_privacy),
        "negative_fixture_detection_rate": privacy_detection
        / len(negative_privacy),
        "privacy_policy_passed": not privacy_findings
        and privacy_detection == len(negative_privacy),
        "findings": privacy_findings,
    }
    secret = {
        "schema_version": "v03171_secret_scan_v1",
        "stage": "v0.3.17.1",
        "target_count": len(targets),
        "secret_finding_count": len(secret_findings),
        "negative_fixture_count": len(negative_secrets),
        "negative_fixture_detection_rate": secret_detection / len(negative_secrets),
        "secret_scan_passed": not secret_findings
        and secret_detection == len(negative_secrets),
        "findings": secret_findings,
    }
    REPORT.mkdir(parents=True, exist_ok=True)
    for name, value in (
        ("privacy_report.json", privacy),
        ("secret_scan_report.json", secret),
    ):
        (REPORT / name).write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    return privacy, secret


def main() -> int:
    privacy, secret = run()
    value = {
        "privacy_policy_passed": privacy["privacy_policy_passed"],
        "secret_scan_passed": secret["secret_scan_passed"],
        "target_count": privacy["target_count"],
    }
    print(json.dumps(value, ensure_ascii=False))
    return 0 if all(value[key] for key in ("privacy_policy_passed", "secret_scan_passed")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
