from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import yaml

from collectors.shadow.acknowledgement import AckContractError, make_ack, validate_ack
from collectors.shadow.event_model import causal_sort
from collectors.shadow.integrated_exporter import IntegratedPassiveExporter
from collectors.shadow.integrated_sink import FaultInjectingSink, LocalIdempotentSink
from collectors.shadow.performance import run_profile
from collectors.shadow.privacy import audit
from collectors.shadow.scenario_runner import run_all, run_scenario
from ml.experiments.v0_3_15_1.run_v0_3_15_1 import corpus
from ml.experiments.v0_3_15_2.freeze_campaign import ATTACKS, SEEDS, episode_schedule, fault_schedule, sessions
from tools.docs.validate_project_status import validate as validate_status
from tools.audit.check_repository_artifacts import violations
from tools.audit.strict_bundle import verify_bundle


ROOT = Path(__file__).resolve().parents[2]
CFG = ROOT / "ml/experiments/v0_3_15_2"
REPORT = ROOT / "ml/reports/v0_3_15_2"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class ProspectiveTrialBehavior(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = corpus(30)

    def test_01_protocol_freeze(self):
        protocol = yaml.safe_load((ROOT / "ml/protocols/v0_3_15_2_protocol.yaml").read_text(encoding="utf-8"))
        self.assertEqual(protocol["revision"], 2); self.assertEqual(protocol["frozen_candidate"]["feature_count"], 51)

    def test_02_campaign_freeze(self):
        value = yaml.safe_load((CFG / "campaign.yaml").read_text(encoding="utf-8"))
        self.assertEqual((value["session_count"], value["capture_window_count"], value["scored_window_count"]), (12, 2400, 2280))

    def test_03_new_seeds(self):
        self.assertEqual(len(SEEDS), len(set(SEEDS))); self.assertFalse(set(SEEDS) & {18101,18102,18201,18202,18301,18302,18401,18402,18501,18502})

    def test_04_episode_balance(self):
        rows = episode_schedule(sessions())
        self.assertEqual(sum(row["kind"] == "benign" for row in rows), 60); self.assertTrue(all(sum(row["class"] == name for row in rows) == 12 for name in ATTACKS))
        self.assertTrue(all(sum(row["kind"] == kind and row["length"] == length for row in rows) == 15 for kind in ("benign","attack") for length in range(2,6)))

    def test_05_label_vault_separation(self):
        value = read_json(REPORT / "blind_access_audit.json")
        self.assertTrue(value["blind_access_audit_passed"]); self.assertTrue(all(value[key] == 0 for key in value if key.endswith("_count")))

    def test_06_prediction_uniqueness(self):
        value = read_json(REPORT / "immutable_prediction_manifest.json")
        self.assertEqual((value["unique_prediction_row_count"], value["missing_prediction_row_count"], value["duplicate_prediction_row_count"]), (2280,0,0))

    def test_07_integrated_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            sink = LocalIdempotentSink(); exporter = IntegratedPassiveExporter(sink, directory, batch_size=3, rate=1000)
            for event in self.events[:3]: self.assertTrue(exporter.submit(event).accepted)
            self.assertTrue(exporter.drain()); self.assertEqual(len(sink.events), 3)

    def test_08_all_fault_scenarios(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_all(Path(directory), self.events)
            self.assertEqual((result["scenario_count"], result["passed_count"]), (35,35)); self.assertTrue(result["all_passed_faults_actually_injected"])

    def test_09_ack_validation(self):
        event = self.events[0]; self.assertEqual(validate_ack(make_ack(event), event).outcome, "success")
        with self.assertRaises(AckContractError): validate_ack({"status":"accepted"}, event)

    def test_10_retry_classification(self):
        with tempfile.TemporaryDirectory() as directory:
            sink = FaultInjectingSink("sink_timeout"); exporter = IntegratedPassiveExporter(sink, directory)
            exporter.submit(self.events[0]); exporter.drain(); self.assertGreater(exporter.report()["metrics"]["retry_count"], 0)

    def test_11_drop_reconciliation(self):
        with tempfile.TemporaryDirectory() as directory:
            exporter = IntegratedPassiveExporter(LocalIdempotentSink(), directory, capacity=2)
            decisions = [exporter.submit(row) for row in self.events[:3]]; exporter.drain()
            self.assertTrue(any(not row.accepted for row in decisions)); self.assertEqual(exporter.reconciliation()["unaccounted_drop_count"], 0)

    def test_12_crash_recovery(self):
        with tempfile.TemporaryDirectory() as directory: self.assertTrue(run_scenario("crash_after_ack_before_checkpoint", Path(directory), self.events)["passed"])

    def test_13_clock_safety(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertTrue(run_scenario("clock_backward_jump", Path(directory), self.events)["passed"]); self.assertTrue(run_scenario("clock_forward_jump", Path(directory), self.events)["passed"])

    def test_14_source_sink_reconciliation(self):
        value = read_json(REPORT / "source_sink_reconciliation_report.json")
        self.assertTrue(value["event_sets_equal"]); self.assertEqual((value["semantic_duplicate_count"],value["idempotency_collision_count"],value["unaccounted_drop_count"]),(0,0,0))

    def test_15_causal_invariance(self):
        rows = [{"benchmark_id":"b","run_id":"r","activity_key":"a","causal_order":value,"immutable_row_id":str(value)} for value in (3,1,2)]
        self.assertEqual([row["causal_order"] for row in causal_sort(rows)], [1,2,3]); self.assertTrue(read_json(REPORT / "causal_invariance_report.json")["causal_order_invariance_passed"])

    def test_16_restart_invariance(self):
        self.assertTrue(read_json(REPORT / "restart_invariance_report.json")["restart_boundary_invariance_passed"])

    def test_17_privacy_surface_behavior(self):
        self.assertEqual(audit({"event_id":"a"*64}), []); self.assertTrue(audit({"payload":"secret"}))

    def test_18_performance_topology(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_profile(self.events[:10], Path(directory), workers=2, batch_size=5, repetitions=1)
            self.assertTrue(result["real_worker_pool"]); self.assertTrue(result["real_batch_delivery"]); self.assertTrue(result["reconciled"])

    def test_19_strict_resume(self):
        value = read_json(REPORT / "resume_fixture_report.json"); self.assertTrue(value["strict_resume_passed"]); self.assertEqual(value["skipped_prediction_count"], 2280)

    def test_20_corruption_rejection(self):
        value = read_json(REPORT / "resume_fixture_report.json"); self.assertEqual(value["corruption_case_count"], 11); self.assertTrue(value["corrupted_bundle_rejected"])

    def test_21_documentation_consistency(self):
        self.assertTrue(validate_status()["valid"])

    def test_22_no_fit_audit(self):
        value = read_json(REPORT / "no_fit_audit.json"); self.assertTrue(value["no_fit_audit_passed"])
        self.assertTrue(all(value.get(key,0) == 0 for key in ("fit_call_count","partial_fit_call_count","calibration_fit_call_count","conformal_fit_call_count","feature_selection_call_count","threshold_selection_call_count","candidate_replacement_count")))

    def test_23_prohibited_actions(self):
        value = read_json(REPORT / "v0_3_15_2_policy_result.json")
        self.assertTrue(all(value[key] == 0 for key in ("external_network_attempt_count","production_connection_attempt_count","backend_write_attempt_count","automatic_action_attempt_count","network_block_attempt_count")))
        self.assertFalse(value["candidate_ready_for_shadow_mode"]); self.assertFalse(value["production_ready"])

    def test_24_fault_schedule_is_complete(self):
        self.assertEqual(len(fault_schedule(sessions())), 35)

    def test_25_negative_result_is_not_hidden(self):
        value = read_json(REPORT / "v0_3_15_2_policy_result.json")
        self.assertFalse(value["scientific_policy_passed"]); self.assertFalse(value["v03152_prospective_runtime_trial_passed"]); self.assertFalse(value["candidate_ready_for_v0_3_16_staging_connector_readiness"])

    def test_26_final_bundle_validator(self):
        result = verify_bundle(REPORT / "v0_3_15_2_bundle_manifest.yaml", REPORT / "v0_3_15_2_bundle_manifest.sha256", allowed_root=ROOT)
        self.assertEqual(result["verified_artifact_count"], 54)

    def test_27_artifact_exclusion(self):
        self.assertEqual(violations(["ml/reports/v0_3_15_2/window_metrics.json","runtime/.env.example"]), [])
        self.assertEqual(violations(["runtime/v0_3_15_2/capture.pcap"]), ["runtime/v0_3_15_2/capture.pcap"])


if __name__ == "__main__":
    unittest.main()
