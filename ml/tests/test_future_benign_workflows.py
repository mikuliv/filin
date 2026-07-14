import importlib.util
import base64
import hashlib
import socket
import sys
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLIENT = ROOT / "lab/docker/services/traffic-client"
sys.path.insert(0, str(CLIENT))
from future_workflows import WORKFLOW_PLANS, behavioral_fingerprint, primary_target, workflow_runtime_audit
from client import SCENARIOS, _client_frame, _recv_server_frame, perform_websocket_session


class TestFutureBenignWorkflows(unittest.TestCase):
    def test_internal_dns_responder_returns_a_or_nxdomain(self):
        dns_path = ROOT / "lab" / "docker" / "services" / "internal-dns" / "server.py"
        spec = importlib.util.spec_from_file_location("filin_internal_dns", dns_path)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        import struct
        def query(name):
            labels = b"".join(bytes([len(value)]) + value.encode() for value in name.split(".")) + b"\0"
            return b"\x12\x34" + struct.pack("!HHHHH", 0x0100, 1, 0, 0, 0) + labels + struct.pack("!HH", 1, 1)
        original = module.socket.gethostbyname
        module.socket.gethostbyname = lambda _: "10.0.0.2"
        try:
            good = module.response(query("target-api")); missing = module.response(query("filin-missing-service"))
        finally:
            module.socket.gethostbyname = original
        self.assertEqual(good[3] & 0x0F, 0)
        self.assertEqual(missing[3] & 0x0F, 3)

    def test_duplicate_behavior_is_disclosed_by_collision_audit(self):
        fingerprints = [behavioral_fingerprint(name) for name in WORKFLOW_PLANS]
        duplicate_count = len(fingerprints) - len(set(fingerprints))
        disclosed = sum(len(group) - 1 for group in workflow_runtime_audit()["observable_protocol_collisions"])
        self.assertGreaterEqual(disclosed, duplicate_count)

    def test_dns_workflows_create_dns_observations(self):
        for name in ("benign_dns_failover_rotation", "benign_multi_resolver_discovery", "benign_dns_cache_repopulation", "benign_resolver_failover_cycle"):
            self.assertTrue(any(action.kind == "dns" for action in WORKFLOW_PLANS[name]))

    def test_websocket_is_not_a_plain_get(self):
        for name in ("benign_websocket_keepalive", "benign_websocket_session_recovery", "benign_long_poll_reconnect"):
            self.assertTrue(any(action.kind == "websocket" for action in WORKFLOW_PLANS[name]))
            self.assertFalse(all(action.kind == "http" and action.operation.startswith("GET:") for action in WORKFLOW_PLANS[name]))

    def test_websocket_performs_ping_pong_and_close_frames(self):
        client_socket, server_socket = socket.socketpair()
        failures = []

        def server():
            try:
                request = bytearray()
                while b"\r\n\r\n" not in request:
                    request.extend(server_socket.recv(512))
                key_line = next(line for line in request.split(b"\r\n") if line.lower().startswith(b"sec-websocket-key:"))
                key = key_line.split(b":", 1)[1].strip()
                accept = base64.b64encode(hashlib.sha1(key + b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11").digest())
                server_socket.sendall(b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: " + accept + b"\r\n\r\n")
                self.assertEqual(_recv_server_frame(server_socket), (0x1, b"ping"))
                server_socket.sendall(bytes([0x81, 4]) + b"pong")
                self.assertEqual(_recv_server_frame(server_socket), (0x9, b"filin"))
                server_socket.sendall(bytes([0x8A, 5]) + b"filin")
                opcode, payload = _recv_server_frame(server_socket)
                self.assertEqual(opcode, 0x8)
                server_socket.sendall(bytes([0x88, len(payload)]) + payload)
            except BaseException as error:
                failures.append(error)
            finally:
                server_socket.close()

        thread = threading.Thread(target=server)
        thread.start()
        result = perform_websocket_session(client_socket, "control-api:8090")
        client_socket.close(); thread.join(timeout=2)
        if failures:
            raise failures[0]
        self.assertTrue(result["protocol_ping_pong"])
        self.assertTrue(result["close_handshake"])

    def test_target_roles_match_actual_primary_targets(self):
        for scenario_id in WORKFLOW_PLANS:
            self.assertEqual(SCENARIOS[scenario_id][3], primary_target(scenario_id))

    def test_runtime_audit_discloses_approximations_and_collisions(self):
        audit = workflow_runtime_audit()
        self.assertEqual(audit["workflow_count"], len(WORKFLOW_PLANS))
        self.assertTrue(any(row["unsupported_claim"] == "database" for row in audit["workflows"]))
        self.assertIn("terminal provenance beacon excluded", audit["collision_basis"])
        self.assertTrue(all(row["timing_behavior"] for row in audit["workflows"]))
        self.assertTrue(all(row["expected_observable_feature_family"] for row in audit["workflows"]))

    def test_plans_are_bounded_and_local(self):
        allowed = {"target-web", "target-api", "control-api", "internal-dns", "target-ssh-sim", "filin-missing-service"}
        for plan in WORKFLOW_PLANS.values():
            self.assertLessEqual(len(plan), 5)
            self.assertTrue(all(action.target in allowed for action in plan))


if __name__ == "__main__": unittest.main()
