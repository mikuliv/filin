from __future__ import annotations

from pathlib import Path

import pytest

from lab.network_validation.contracts import ContractError
from lab.network_validation.superseding_execution_package import (
    PREDECESSOR_PACKAGE_DIGEST,
    PREDECESSOR_PACKAGE_ID,
    build_payload,
    build_preview,
    scientific_equivalence,
    validate_package,
    write_official_package,
)


def test_scientific_equivalence_preserves_all_frozen_inputs() -> None:
    result = scientific_equivalence()
    assert result["valid"] is True
    assert result["scenario_templates"] == 288
    assert result["execution_sessions"] == 864
    assert result["counterfactual_pairs"] == 24
    assert result["proxy_warning_count"] == result["nuisance_warning_count"] == 0
    assert result["execution_tokens_unchanged"] is True
    assert result["scientific_seeds_unchanged"] is True


def test_preview_is_not_an_official_artifact() -> None:
    result = build_preview("a" * 40)
    assert result["official_superseding_execution_package_created"] is False
    assert result["official_superseding_execution_package_valid"] is False
    assert result["scientific_equivalence_valid"] is True


def test_payload_supersedes_predecessor_without_scientific_change() -> None:
    value = build_payload("a" * 40, "2026-01-01T00:00:00Z")
    assert value["supersedes_package_id"] == PREDECESSOR_PACKAGE_ID
    assert value["supersedes_package_digest"] == PREDECESSOR_PACKAGE_DIGEST
    assert value["package_id"] != PREDECESSOR_PACKAGE_ID
    assert value["scientific_protocol_changed"] is False
    assert value["scientific_run_plan_changed"] is False
    assert value["scientific_split_changed"] is False
    assert value["scientific_campaign_started"] is False
    assert value["scientific_sessions_executed"] == 0


def test_validation_rejects_tamper(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("lab.network_validation.superseding_execution_package.validate_operational_contracts_commit", lambda _: None)
    value = build_payload("a" * 40, "2026-01-01T00:00:00Z")
    assert validate_package(value) == value
    with pytest.raises(ContractError):
        validate_package(dict(value, execution_session_count=863))


def test_official_write_requires_confirmation_and_never_overwrites(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("lab.network_validation.superseding_execution_package.validate_operational_contracts_commit", lambda _: None)
    target = tmp_path / "package.json"
    with pytest.raises(ContractError):
        write_official_package(target, "a" * 40, "2026-01-01T00:00:00Z", False)
    write_official_package(target, "a" * 40, "2026-01-01T00:00:00Z", True)
    with pytest.raises(ContractError):
        write_official_package(target, "a" * 40, "2026-01-01T00:00:00Z", True)
