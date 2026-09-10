from __future__ import annotations

from pathlib import Path

import pytest

from lab.network_validation.cli import parser
from lab.network_validation.contracts import ContractError, load_json
from lab.network_validation.phase1_execution_package import RUN_PLAN_PATH
from lab.network_validation.runtime_execution_package_v5 import (
    CAMPAIGN_PATH,
    OFFICIAL_RUNTIME_PACKAGE_V5_PATH,
    PREDECESSOR_PACKAGE_DIGEST,
    PREDECESSOR_PACKAGE_ID,
    SCIENTIFIC_DIGEST_FIELDS,
    build_payload,
    build_preview,
    validate_corrected_zeek_runner,
    validate_package,
    validate_predecessor_package,
    write_official_package,
)


def test_v5_predecessor_is_exact_immutable_v4() -> None:
    predecessor = validate_predecessor_package()
    assert predecessor["package_id"] == PREDECESSOR_PACKAGE_ID
    assert predecessor["canonical_digest"] == PREDECESSOR_PACKAGE_DIGEST


def test_v5_payload_preserves_v4_scientific_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "lab.network_validation.runtime_execution_package_v5.validate_runtime_sources_commit",
        lambda _: None,
    )
    value = build_payload("a" * 40, "2026-01-01T00:00:00Z")
    predecessor = validate_predecessor_package()
    assert validate_package(value) == value
    assert value["supersedes_package_id"] == PREDECESSOR_PACKAGE_ID
    assert value["supersedes_package_digest"] == PREDECESSOR_PACKAGE_DIGEST
    assert all(value[field] == predecessor[field] for field in SCIENTIFIC_DIGEST_FIELDS)
    assert value["scientific_run_plan_changed"] is False
    assert value["scientific_split_changed"] is False
    assert value["scientific_acceptance_criteria_changed"] is False
    with pytest.raises(ContractError):
        validate_package(dict(value, execution_session_count=863))


def test_v5_preview_is_deterministic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "lab.network_validation.runtime_execution_package_v5.validate_runtime_sources_commit",
        lambda _: None,
    )
    left = build_preview("a" * 40)
    right = build_preview("a" * 40)
    assert left == right
    assert left["scientific_equivalence_valid"] is True
    assert left["candidate"]["canonical_digest"] == right["candidate"]["canonical_digest"]


def test_v5_binds_corrected_zeek_runner() -> None:
    validate_corrected_zeek_runner()


def test_v5_preserves_exact_first_execution_unit() -> None:
    first = load_json(RUN_PLAN_PATH)["ordered_execution_units"][0]
    assert first["execution_token"] == "2f18df5418b1c58eab23ae37"
    assert first["execution_identity_sha256"] == "2f18df5418b1c58eab23ae37d3abe37cd78961ff41a169ff0e3ef016378bb94f"
    assert first["order_key"] == "008275f72afc66410f6d03d53a56bdfab67e29370fd7ad802b06e375e9ab4ecb"
    assert first["repetition_index"] == 0
    assert first["primary_split"] == "development_train"
    assert first["execution_seed"] == 1023
    assert first["scenario_token"] == "credential_rejection_family_b_profile_b_target_b_9080_high"
    scenario = next(
        row for row in load_json(CAMPAIGN_PATH)["scenario_templates"]
        if row["scenario"]["scenario_token"] == first["scenario_token"]
    )
    assert scenario["scenario"]["behavior_type"] == "credential_rejection"
    assert scenario["scenario"]["generator_family"] == "family_b"
    assert scenario["scenario"]["infrastructure_profile"] == "profile_b"
    assert scenario["target_implementation"] == "target_b"
    assert scenario["target_port"] == 9080
    assert scenario["intensity_band"] == "high"
    assert scenario["background_policy"] == "dns"
    assert scenario["scenario"]["parameter_vector"] == {"session_rotation": 4}


def test_v5_official_write_requires_confirmation_and_new_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "lab.network_validation.runtime_execution_package_v5.validate_runtime_sources_commit",
        lambda _: None,
    )
    target = tmp_path / "official-v5.json"
    with pytest.raises(ContractError):
        write_official_package(target, "a" * 40, "2026-01-01T00:00:00Z", False)
    write_official_package(target, "a" * 40, "2026-01-01T00:00:00Z", True)
    with pytest.raises(ContractError):
        write_official_package(target, "a" * 40, "2026-01-01T00:00:00Z", True)
    assert OFFICIAL_RUNTIME_PACKAGE_V5_PATH.name == "official_execution_package_v5.json"


def test_existing_runtime_cli_commands_target_v5_without_initialization() -> None:
    preview = parser().parse_args(["build-runtime-execution-package-preview"])
    create = parser().parse_args(["create-official-runtime-execution-package"])
    validate = parser().parse_args(["validate-runtime-execution-package"])
    assert preview.runtime_sources_commit is None
    assert Path(create.output) == OFFICIAL_RUNTIME_PACKAGE_V5_PATH
    assert Path(validate.package) == OFFICIAL_RUNTIME_PACKAGE_V5_PATH
