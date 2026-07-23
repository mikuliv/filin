from __future__ import annotations

import json
import ssl
import sqlite3
import struct
import time
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

import ml.experiments.v0_3_17.run_campaign as campaign_module
from ml.experiments.v0_3_17.run_campaign import LiveProcessor, protocol as load_protocol, raw_features
from ml.experiments.v0_3_15_4.feature_v2 import FEATURES
from ml.features.network_sensor_v0_5 import AssetState
from rehearsal.connector_app import DurableDelivery
from rehearsal.operator_view import FIELDS, project
from rehearsal.sensor_daemon import PersistentIngressClient, _lines_from
from rehearsal.traffic_source import scheduled_rate, write_pcap
from staging.storage import ConnectorJournal, ReceiverStore


ROOT = Path(__file__).resolve().parents[2]
PROTOCOL_PATH = ROOT / "ml/protocols/v0_3_17_protocol.yaml"


@pytest.fixture(scope="module")
def protocol() -> dict:
    return load_protocol()


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        (("stage",), "v0.3.17"),
        (("revision",), 3),
        (("status",), "frozen_before_revision_3_first_rehearsal_event"),
        (("campaign", "total_minimum_seconds"), 14400),
        (("campaign", "minimum_closed_capture_windows"), 14400),
        (("campaign", "warmup_windows_per_run"), 60),
        (("network_topology", "published_ports"), 0),
        (("network_topology", "external_routes"), 0),
        (("candidate_identity", "feature_count"), 51),
        (("operator_view", "contract"), "operator_projection_v1"),
        (("observability", "contract"), "rehearsal_observability_v1"),
        (("fault_schedule", "count"), 30),
        (("privacy_policy", "finding_count_max"), 0),
        (("disk_pressure", "stop_percent"), 92),
        (("backlog_policy", "final_backlog"), 0),
    ],
)
def test_frozen_protocol_values(protocol: dict, path: tuple[str, ...], expected: object) -> None:
    value = protocol
    for key in path:
        value = value[key]
    assert value == expected


def test_protocol_has_exact_policy_gate_count(protocol: dict) -> None:
    assert len(protocol["pass_fail_gates"]) == 65
    assert len(set(protocol["pass_fail_gates"])) == 65


def test_runs_are_independent_and_sum_four_hours(protocol: dict) -> None:
    runs = protocol["campaign"]["runs"]
    assert len({item["run_id"] for item in runs}) == 3
    assert len({item["seed"] for item in runs}) == 3
    assert len({item["certificate_session_id"] for item in runs}) == 3
    assert len({item["instance_namespace"] for item in runs}) == 3
    assert sum(item["duration_seconds"] for item in runs) == 14400


def test_sessions_are_unique(protocol: dict) -> None:
    sessions = protocol["campaign"]["sessions"]
    assert len(sessions) == 12
    assert len({item["session_id"] for item in sessions}) == 12
    assert len({item["seed"] for item in sessions}) == 12


def test_sensor_reuses_persistent_tls_connection() -> None:
    created = []

    class Response:
        status = 200

        @staticmethod
        def read() -> bytes:
            return b'{"durable":true}'

    class Connection:
        def __init__(self, *args: object, **kwargs: object) -> None:
            self.requests = []
            created.append(self)

        def request(self, *args: object, **kwargs: object) -> None:
            self.requests.append((args, kwargs))

        @staticmethod
        def getresponse() -> Response:
            return Response()

        @staticmethod
        def close() -> None:
            return None

    client = PersistentIngressClient(
        "https://staging-connector:8443/staging-connector/v1/events",
        ssl.create_default_context(),
        connection_factory=Connection,
    )
    assert client.send(b"{}") == {"durable": True}
    assert client.send(b"{}") == {"durable": True}
    assert len(created) == 1
    assert len(created[0].requests) == 2


@pytest.mark.parametrize(
    ("second", "phase", "rate"),
    [(0, "warmup", 5), (59, "warmup", 5), (60, "nominal", 10), (1199, "nominal", 10), (1200, "gradual", 20), (2399, "gradual", 50), (2400, "burst", 100), (2519, "burst", 100)],
)
def test_scheduler_boundaries(second: int, phase: str, rate: int) -> None:
    phases = [
        {"phase": "warmup", "start_second": 0, "end_second": 60, "rate": 5},
        {"phase": "nominal", "start_second": 60, "end_second": 1200, "rate": 10},
        {"phase": "gradual", "start_second": 1200, "end_second": 2400, "rate": [20, 50]},
        {"phase": "burst", "start_second": 2400, "end_second": 2520, "rate": 100},
    ]
    assert scheduled_rate(phases, second) == (phase, rate)


def test_scheduler_rejects_gap() -> None:
    with pytest.raises(RuntimeError, match="schedule_gap"):
        scheduled_rate([{"phase": "a", "start_second": 1, "end_second": 2, "rate": 1}], 0)


def test_pcap_is_closed_unique_and_has_expected_packet_count(tmp_path: Path) -> None:
    first, second = tmp_path / "a.pcap", tmp_path / "b.pcap"
    one = write_pcap(first, 27101, 1, 5, 1_900_000_000.0)
    two = write_pcap(second, 27101, 2, 5, 1_900_000_001.0)
    assert one["packet_count"] == two["packet_count"] == 5
    assert one["pcap_sha256"] != two["pcap_sha256"]
    assert first.read_bytes()[:4] == struct.pack("<I", 0xA1B2C3D4)
    assert first.stat().st_size == 24 + 5 * (16 + 54)


@pytest.mark.parametrize("phase", ["nominal", "burst", "periodic_service_polling", "recovery", "maintenance"])
def test_feature_vector_contract(phase: str) -> None:
    vector = raw_features(AssetState(4), "local-run", 3, phase)
    assert list(vector) == FEATURES
    assert len(vector) == 51
    assert all(isinstance(value, float) for value in vector.values())


def sample_event() -> dict:
    return {
        "event_id": "evt_" + "1" * 64,
        "event_type": "decision_observation",
        "event_timestamp": "2026-07-23T00:00:00+00:00",
        "event_contract_version": "shadow_event_v2",
        "causal_order": 7,
        "activity_key": "2" * 64,
        "candidate_ref": {"candidate_id": "v03154:65a3dd912d845bc1"},
        "prediction_ref": {"prediction_id": "pred_" + "3" * 64, "source_capture_id": "cap_" + "4" * 64},
        "runtime_ref": {"session_id": "runtime_contract_baseline_001", "hash_chain_previous": None},
        "payload": {"state": "observed", "reason_code": "confidence_high"},
    }


def test_operator_projection_has_exact_fields() -> None:
    value = project(sample_event(), "rrc_" + "5" * 32, "2026-07-23T00:01:00+00:00")
    assert list(value) == FIELDS


@pytest.mark.parametrize("forbidden", ["raw_ip", "hostname", "username", "email", "credential", "payload", "features", "label", "scenario", "private_key"])
def test_operator_projection_excludes_private_fields(forbidden: str) -> None:
    value = project(sample_event(), "rrc_" + "5" * 32, "2026-07-23T00:01:00+00:00")
    assert forbidden not in value
    assert forbidden not in json.dumps(value)


def test_operator_projection_schema() -> None:
    schema = json.loads((ROOT / "rehearsal/contracts/operator_projection_v1.schema.json").read_text(encoding="utf-8"))
    value = project(sample_event(), "rrc_" + "5" * 32, "2026-07-23T00:01:00+00:00")
    Draft202012Validator(schema).validate(value)


def test_observability_schema_is_strict() -> None:
    schema = json.loads((ROOT / "rehearsal/contracts/rehearsal_observability_v1.schema.json").read_text(encoding="utf-8"))
    assert schema["additionalProperties"] is False
    assert len(schema["required"]) == 25


def test_sensor_reads_only_complete_lines(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    path.write_bytes(b'{"a":1}\n{"a":2}')
    rows, offset = _lines_from(path, 0, 50)
    assert rows == [{"a": 1}]
    assert offset == len(b'{"a":1}\n')


def test_sensor_resume_offset(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    path.write_text('{"a":1}\n{"a":2}\n', encoding="utf-8")
    first, offset = _lines_from(path, 0, 1)
    second, final = _lines_from(path, offset, 1)
    assert first == [{"a": 1}]
    assert second == [{"a": 2}]
    assert final == path.stat().st_size


def test_connector_journal_ack_is_after_commit(tmp_path: Path) -> None:
    journal = ConnectorJournal(tmp_path / "connector.sqlite")
    event = {
        "event_id": "evt_" + "1" * 64,
        "idempotency_key": "2" * 64,
        "candidate_ref": {"candidate_id": "v03154:65a3dd912d845bc1"},
        "runtime_ref": {"source_sequence": 1},
    }
    result = journal.append("request-1", [event])
    assert result["accepted"] == [event["event_id"]]
    assert journal.counts() == {"durable": 1, "pending": 1, "acknowledged": 0}


def test_connector_journal_idempotent_replay(tmp_path: Path) -> None:
    journal = ConnectorJournal(tmp_path / "connector.sqlite")
    event = {"event_id": "evt_" + "1" * 64, "idempotency_key": "2" * 64, "candidate_ref": {"candidate_id": "v03154:65a3dd912d845bc1"}, "runtime_ref": {"source_sequence": 1}}
    journal.append("request-1", [event])
    replay = journal.append("request-1", [event])
    assert replay["accepted"] == []
    assert replay["duplicates"] == [event["event_id"]]


@pytest.mark.parametrize(
    ("service", "networks"),
    [
        ("traffic-source", {"filin_sensor_connector_internal"}),
        ("sensor-runtime", {"filin_sensor_connector_internal"}),
        ("staging-connector", {"filin_sensor_connector_internal", "filin_connector_receiver_internal"}),
        ("reference-receiver", {"filin_connector_receiver_internal", "filin_receiver_operator_internal"}),
        ("operator-view", {"filin_receiver_operator_internal"}),
    ],
)
def test_compose_network_separation(service: str, networks: set[str]) -> None:
    compose = yaml.safe_load((ROOT / "rehearsal/docker-compose.v0_3_17.yml").read_text(encoding="utf-8"))
    assert set(compose["services"][service]["networks"]) == networks


@pytest.mark.parametrize("service", ["traffic-source", "sensor-runtime", "staging-connector", "reference-receiver", "operator-view"])
def test_compose_hardening(service: str) -> None:
    value = yaml.safe_load((ROOT / "rehearsal/docker-compose.v0_3_17.yml").read_text(encoding="utf-8"))["services"][service]
    assert value["user"] == "65532:65532"
    assert value["read_only"] is True
    assert value["cap_drop"] == ["ALL"]
    assert value["security_opt"] == ["no-new-privileges:true"]
    assert value["restart"] == "no"
    assert "ports" not in value


def test_all_compose_networks_are_internal() -> None:
    compose = yaml.safe_load((ROOT / "rehearsal/docker-compose.v0_3_17.yml").read_text(encoding="utf-8"))
    assert len(compose["networks"]) == 3
    assert all(value["internal"] is True for value in compose["networks"].values())


def test_operator_volume_is_read_only() -> None:
    compose = yaml.safe_load((ROOT / "rehearsal/docker-compose.v0_3_17.yml").read_text(encoding="utf-8"))
    assert compose["services"]["operator-view"]["volumes"] == ["${FILIN_V0317_RUNTIME_DIR:-../runtime/v0_3_17}/volumes/receiver:/run/receiver:ro"]


@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE", "PATCH"])
def test_operator_write_methods_are_implemented_as_rejections(method: str) -> None:
    source = (ROOT / "rehearsal/operator_view.py").read_text(encoding="utf-8")
    assert f"do_{method} = _reject_write" in source


def test_no_backend_import_in_rehearsal_sources() -> None:
    sources = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "rehearsal").rglob("*.py"))
    assert "from backend" not in sources
    assert "import backend" not in sources


def test_no_published_ports_in_compose() -> None:
    compose = yaml.safe_load((ROOT / "rehearsal/docker-compose.v0_3_17.yml").read_text(encoding="utf-8"))
    assert all("ports" not in service for service in compose["services"].values())


def test_batch_processor_exceeds_average_run_rate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, protocol: dict) -> None:
    monkeypatch.setattr(campaign_module, "RUNTIME", tmp_path)
    run = protocol["campaign"]["runs"][0]
    sessions = [item for item in protocol["campaign"]["sessions"] if item["run"] == run["run_id"]]
    (tmp_path / run["run_id"]).mkdir(parents=True)
    processor = LiveProcessor(run, sessions)
    receipt = {"scheduled_event_rate": 100, "capture_id": "cap_" + "1" * 64, "pcap_sha256": "2" * 64, "phase": "burst", "capture_wall_ns": 1_900_000_000_000_000_000}
    started = time.perf_counter()
    processor.process_receipt(receipt)
    elapsed = time.perf_counter() - started
    assert processor.window_count == 100
    assert processor.warmup_count == 60
    assert processor.event_count == 40
    assert 100 / elapsed >= 20
