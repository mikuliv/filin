from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path

import pytest

from staging.contracts import ContractError, digest, validate_batch, validate_ingress, validate_receiver_ack
from staging.contracts.models import CANDIDATE_ID, REGISTRY_COMMITMENT
from staging.storage import ConnectorJournal, ReceiverStore

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "ml/reports/v0_3_16"


def event(index: int = 1) -> dict:
    return {"schema_version": "shadow_event_v2", "event_contract_version": "shadow_event_v2", "event_id": "evt_" + f"{index:064x}", "event_type": "decision_observation", "event_timestamp": "2026-07-22T00:00:00Z", "causal_order": index, "activity_key": "1" * 64, "idempotency_key": f"{index + 1000:064x}", "candidate_ref": {"candidate_id": CANDIDATE_ID, "registry_commitment_sha256": REGISTRY_COMMITMENT}, "prediction_ref": {}, "runtime_ref": {"source_sequence": index}, "payload": {}}


def ingress(events=None) -> dict:
    value = {"ingress_contract_version": "connector_ingress_v1", "request_id": "request-1", "sensor_instance_id": "sensor-1", "candidate_registry_commitment_sha256": REGISTRY_COMMITMENT, "events": events or [event()]}
    value["request_body_sha256"] = digest(value)
    return value


def batch(events=None) -> dict:
    value = {"batch_contract_version": "staging_event_batch_v1", "batch_id": "batch-1", "attempt_id": "attempt-1", "connector_instance_id": "connector-1", "candidate_registry_commitment_sha256": REGISTRY_COMMITMENT, "event_contract_version": "shadow_event_v2", "events": events or [event()], "event_count": len(events or [event()]), "previous_batch_commitment_sha256": None}
    value["request_body_sha256"] = digest(value)
    return value


def test_ingress_contract_accepts(): assert validate_ingress(ingress())
def test_batch_contract_accepts(): assert validate_batch(batch())


@pytest.mark.parametrize("change,code", [
    (lambda x: x.update(extra=True), "ingress_schema_invalid"),
    (lambda x: x.update(candidate_registry_commitment_sha256="0" * 64), "registry_commitment_mismatch"),
    (lambda x: x.update(request_body_sha256="0" * 64), "request_body_hash_mismatch"),
])
def test_ingress_rejections(change, code):
    value = ingress(); change(value)
    with pytest.raises(ContractError) as error: validate_ingress(value)
    assert error.value.code == code


@pytest.mark.parametrize("change,code", [
    (lambda x: x.update(event_count=2), "event_count_mismatch"),
    (lambda x: x.update(candidate_registry_commitment_sha256="0" * 64), "registry_commitment_mismatch"),
    (lambda x: x.update(request_body_sha256="0" * 64), "request_body_hash_mismatch"),
    (lambda x: x.update(extra=True), "batch_schema_invalid"),
])
def test_batch_rejections(change, code):
    value = batch(); change(value)
    with pytest.raises(ContractError) as error: validate_batch(value)
    assert error.value.code == code


def test_connector_commit_before_ack_material():
    root = Path(tempfile.mkdtemp()); journal = ConnectorJournal(root / "connector.sqlite")
    result = journal.append("request-1", [event()])
    assert result["accepted"] and result["commit_id"] and result["commit_sha256"] and journal.counts()["durable"] == 1


def test_connector_duplicate_ingress():
    root = Path(tempfile.mkdtemp()); journal = ConnectorJournal(root / "connector.sqlite")
    journal.append("request-1", [event()]); result = journal.append("request-1", [event()])
    assert result["duplicates"] == [event()["event_id"]] and journal.counts()["durable"] == 1


def test_connector_collision_rejected():
    root = Path(tempfile.mkdtemp()); journal = ConnectorJournal(root / "connector.sqlite")
    journal.append("request-1", [event()]); changed = event(); changed["payload"] = {"state": "changed"}
    with pytest.raises(ContractError): journal.append("request-2", [changed])


def test_receiver_commit_and_ack():
    root = Path(tempfile.mkdtemp()); store = ReceiverStore(root / "receiver.sqlite", "receiver-1")
    value = batch(); ack = store.commit(value)
    assert ack["durable"] and store.count() == 1 and validate_receiver_ack(ack, value)


def test_receiver_duplicate_batch_same_ack():
    root = Path(tempfile.mkdtemp()); store = ReceiverStore(root / "receiver.sqlite", "receiver-1")
    value = batch(); assert store.commit(value) == store.commit(value) and store.count() == 1


def test_checkpoint_only_after_receiver_ack():
    root = Path(tempfile.mkdtemp()); journal = ConnectorJournal(root / "connector.sqlite"); store = ReceiverStore(root / "receiver.sqlite", "receiver-1")
    journal.append("request-1", [event()]); value = batch(); ack = store.commit(value); journal.checkpoint(value, ack)
    assert journal.counts() == {"durable": 1, "pending": 0, "acknowledged": 1}


def test_compose_has_two_internal_networks():
    text = (ROOT / "staging/docker-compose.v0_3_16.yml").read_text(encoding="utf-8")
    assert text.count("internal: true") == 2


def test_compose_has_no_published_ports():
    text = (ROOT / "staging/docker-compose.v0_3_16.yml").read_text(encoding="utf-8")
    assert "ports:" not in text and "network_mode: host" not in text


@pytest.mark.parametrize("token", ["user: \"65532:65532\"", "read_only: true", "no-new-privileges:true", "cap_drop: [ALL]", "mem_limit: 256m", "pull_policy: never"])
def test_container_hardening(token): assert token in (ROOT / "staging/docker-compose.v0_3_16.yml").read_text(encoding="utf-8")


@pytest.mark.parametrize("name", ["receiver_unavailable", "connection_timeout", "connection_reset", "http_429_retry_after", "http_503", "slow_receiver", "malformed_ack", "unknown_ack", "expired_client_certificate", "untrusted_certificate", "wrong_receiver_san", "missing_client_certificate", "plaintext_attempt", "certificate_rotation", "connector_crash_before_journal_commit", "connector_crash_after_journal_before_ingress_ack", "connector_crash_after_send_before_receiver_ack", "receiver_crash_before_commit", "receiver_crash_after_commit_before_ack", "receiver_restart_wal", "connector_restart_pending_journal", "receiver_storage_temporarily_unavailable", "duplicate_batch", "bounded_queue_overload"])
def test_fault_schedule_has_oracle(name):
    report = json.loads((REPORT / "fault_execution_results.json").read_text(encoding="utf-8"))
    row = next(item for item in report["scenarios"] if item["fault_name"] == name)
    assert row["injection_count"] > 0 and row["passed"] and row["oracle"]


@pytest.mark.parametrize("name", ["expired_certificate", "not_yet_valid_certificate", "untrusted_ca", "wrong_san", "wrong_eku", "revoked_certificate", "missing_client_certificate", "plaintext", "tls_downgrade", "weak_cipher", "wrong_batch_hash", "wrong_event_hash", "wrong_registry_commitment", "wrong_candidate", "partial_ack", "idempotency_collision"])
def test_security_negative_fixture_rejected(name):
    report = json.loads((REPORT / "security_negative_test_report.json").read_text(encoding="utf-8"))
    row = next(item for item in report["tests"] if item["name"] == name)
    assert row["injection_count"] == 1 and row["rejected"]


def test_policy_result():
    policy = json.loads((REPORT / "v0_3_16_policy_result.json").read_text(encoding="utf-8"))
    assert policy["v0316_stage_passed"] and policy["candidate_ready_for_v0_3_17_controlled_local_shadow_rehearsal"]
    assert not any(policy[key] for key in ("candidate_ready_for_shadow_mode", "backend_integration_allowed", "shadow_mode_allowed", "production_ready"))
