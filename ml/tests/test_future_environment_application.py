import json
import subprocess
import unittest

from lab.environment.application_controller import (
    EnvironmentApplicationController, EnvironmentSafetyError,
    assign_profile, audit_condition_independence, netem_arguments,
)
from lab.tools.future_scenario_runner import execute_with_environment


class FakeRunner:
    def __init__(self, project="filin_smoke", network="filin_smoke_lab"):
        self.netem = False
        self.commands = []
        self.project = project
        self.network = network

    def __call__(self, command):
        self.commands.append(command)
        if command[1] == "inspect":
            output = json.dumps([{
                "Config": {"Labels": {"com.docker.compose.project": self.project}},
                "NetworkSettings": {"Networks": {self.network: {}}},
            }])
            return subprocess.CompletedProcess(command, 0, output, "")
        if "replace" in command:
            self.netem = True
        elif "del" in command:
            self.netem = False
        output = "qdisc netem 1: root" if self.netem else "qdisc noqueue 0: root"
        return subprocess.CompletedProcess(command, 0, output, "")


def controller(runner):
    return EnvironmentApplicationController(
        "traffic-client", expected_compose_project="filin_smoke",
        expected_network="filin_smoke_lab", runner=runner,
    )


class TestFutureEnvironmentApplication(unittest.TestCase):
    def test_condition_stays_active_during_execution_then_rolls_back(self):
        runner = FakeRunner()
        with controller(runner).applied({"profile_id": "stress", "latency_ms": 20}, 42) as evidence:
            self.assertTrue(runner.netem)
            self.assertEqual(evidence.status, "active")
        self.assertFalse(runner.netem)
        self.assertEqual(evidence.status, "passed")
        self.assertTrue(evidence.rollback_verified)

    def test_rollback_on_exception_and_timeout(self):
        for error in (RuntimeError("failure"), TimeoutError("timeout")):
            runner = FakeRunner()
            with self.assertRaises(type(error)):
                with controller(runner).applied({"profile_id": "stress", "jitter_ms": 5}, 1):
                    self.assertTrue(runner.netem)
                    raise error
            self.assertFalse(runner.netem)

    def test_measurement_is_taken_before_rollback(self):
        runner = FakeRunner()
        callback = lambda: {"netem_active": runner.netem}
        with controller(runner).applied({"profile_id": "stress", "latency_ms": 20}, 1, callback) as evidence:
            pass
        self.assertEqual(evidence.measurements, {"netem_active": True})

    def test_future_runner_executes_inside_application_scope(self):
        runner = FakeRunner()
        result, evidence = execute_with_environment(
            controller=controller(runner), profile={"profile_id": "latency", "latency_ms": 5}, seed=3,
            execute=lambda: {"status": "completed", "netem_active": runner.netem},
        )
        self.assertTrue(result["netem_active"])
        self.assertTrue(evidence.rollback_verified)
        self.assertFalse(runner.netem)

    def test_unsupported_fields_are_evidence_not_tc_arguments(self):
        runner = FakeRunner()
        profile = {"profile_id": "stress", "latency_ms": 20, "clients": [2, 5], "background_profile": "x"}
        with controller(runner).applied(profile, 1) as evidence:
            pass
        self.assertEqual(evidence.unsupported_fields, ["background_profile", "clients"])
        applied = " ".join(evidence.applied_command)
        self.assertNotIn("clients", applied)
        self.assertNotIn("background_profile", applied)

    def test_wrong_project_or_network_is_rejected(self):
        with self.assertRaises(EnvironmentSafetyError):
            with controller(FakeRunner(project="another")).applied({"profile_id": "x"}, 1):
                pass
        with self.assertRaises(EnvironmentSafetyError):
            with controller(FakeRunner(network="another")).applied({"profile_id": "x"}, 1):
                pass

    def test_safety_rejects_host_or_shell_identifiers(self):
        with self.assertRaises(EnvironmentSafetyError):
            EnvironmentApplicationController("host; rm", expected_compose_project="x", expected_network="x")
        with self.assertRaises(EnvironmentSafetyError):
            netem_arguments({"packet_loss_percent": 50}, 1)

    def test_assignment_does_not_accept_or_depend_on_label(self):
        profiles = ["a", "b", "c"]
        self.assertEqual(assign_profile("run-1", profiles, 7), assign_profile("run-1", profiles, 7))
        records = [{"run_id": "run-1", "environment_profile_id": "a", "assignment_seed": 7, "assignment_inputs": ["run_id", "assignment_seed"]}]
        self.assertEqual(audit_condition_independence(records)["status"], "passed")
        records[0]["assignment_inputs"].append("label")
        self.assertEqual(audit_condition_independence(records)["status"], "failed")


if __name__ == "__main__":
    unittest.main()
