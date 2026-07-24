from __future__ import annotations

from ml.experiments.v0_3_17_1.safety_audit import (
    PRIVACY_PATTERNS,
    SECRET_PATTERNS,
    run,
)
from tools.audit.validate_v03171_artifact_exclusion import validate


def test_privacy_negative_fixtures_are_detected() -> None:
    assert PRIVACY_PATTERNS["email_address"].search("owner@example.org")
    assert PRIVACY_PATTERNS["absolute_windows_path"].search("Z:\\data\\raw.pcap")
    assert PRIVACY_PATTERNS["public_ipv4"].search("8.8.8.8")


def test_secret_negative_fixtures_are_detected() -> None:
    assert SECRET_PATTERNS["private_key"].search("-----BEGIN PRIVATE KEY-----")
    assert SECRET_PATTERNS["aws_access_key"].search("AKIA1234567890ABCDEF")
    assert SECRET_PATTERNS["github_token"].search(
        "ghp_abcdefghijklmnopqrstuvwxyz123456"
    )


def test_stage_safety_audit_passes() -> None:
    privacy, secret = run()
    assert privacy["privacy_policy_passed"]
    assert secret["secret_scan_passed"]


def test_artifact_exclusion_passes() -> None:
    assert validate()["passed"]
