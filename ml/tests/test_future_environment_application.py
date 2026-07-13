import subprocess
import unittest

from lab.environment.application_controller import (
    EnvironmentApplicationController, EnvironmentSafetyError,
    assign_profile, audit_condition_independence, netem_arguments,
)


class FakeRunner:
    def __init__(self): self.netem = False; self.commands = []
    def __call__(self, command):
        self.commands.append(command)
        if "replace" in command: self.netem = True
        elif "del" in command: self.netem = False
        output = "qdisc netem 1: root" if self.netem else "qdisc noqueue 0: root"
        return subprocess.CompletedProcess(command, 0, output, "")


class TestFutureEnvironmentApplication(unittest.TestCase):
    def test_profile_is_applied_verified_and_rolled_back(self):
        runner = FakeRunner(); controller = EnvironmentApplicationController("traffic-client", runner=runner)
        evidence = controller.apply_verify_rollback({"profile_id": "stress", "latency_ms": [20, 40], "jitter_ms": 5, "packet_loss_percent": 1}, 42)
        self.assertEqual(evidence.status, "passed"); self.assertTrue(evidence.rollback_verified)
        self.assertIn("netem", evidence.applied_command); self.assertFalse(runner.netem)

    def test_safety_rejects_host_or_shell_identifiers(self):
        with self.assertRaises(EnvironmentSafetyError): EnvironmentApplicationController("host; rm")
        with self.assertRaises(EnvironmentSafetyError): netem_arguments({"packet_loss_percent": 50}, 1)

    def test_assignment_does_not_accept_or_depend_on_label(self):
        profiles = ["a", "b", "c"]
        self.assertEqual(assign_profile("run-1", profiles, 7), assign_profile("run-1", profiles, 7))
        records = [{"run_id": "run-1", "environment_profile_id": "a", "assignment_seed": 7, "assignment_inputs": ["run_id", "assignment_seed"]}]
        self.assertEqual(audit_condition_independence(records)["status"], "passed")
        records[0]["assignment_inputs"].append("label")
        self.assertEqual(audit_condition_independence(records)["status"], "failed")


if __name__ == "__main__": unittest.main()
