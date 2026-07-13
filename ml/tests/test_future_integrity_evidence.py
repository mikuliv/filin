import tempfile
import unittest
from pathlib import Path

from tools.audit.artifact_hashes import canonical_sha256, execution_mapping_sha256, marker_intervals_sha256
from tools.audit.integrity_evidence import IntegrityEvidence, final_integrity_gate
from tools.audit.reproduction_audit import compare_aggregates
from tools.audit.verify_secure_artifacts import verify


class TestFutureIntegrityEvidence(unittest.TestCase):
    def test_hash_domains_are_distinct(self):
        value = [{"execution_id": "e", "marker_nonce": "n", "start": 1, "end": 2, "duration_seconds": 1, "source": "sensor_marker"}]
        marker = marker_intervals_sha256(value)
        mapping = execution_mapping_sha256([{"run_id": "r", "execution_id": "e", "scenario_id": "s", "window_index": 0}])
        self.assertNotEqual(marker, mapping)
        self.assertNotEqual(canonical_sha256("pcap_sha256", value), canonical_sha256("normalized_events_sha256", value))

    def test_not_executed_is_not_passed(self):
        evidence = IntegrityEvidence("secure", "not_executed", "unavailable", {})
        result = final_integrity_gate([evidence])
        self.assertEqual(result["status"], "not_executed"); self.assertFalse(result["passed"])

    def test_failed_check_fails_final_gate(self):
        checks = [IntegrityEvidence("a", "passed", "ok", {}), IntegrityEvidence("b", "failed", "mismatch", {})]
        self.assertEqual(final_integrity_gate(checks)["status"], "failed")

    def test_reproduction_is_computed(self):
        good = compare_aggregates({"e": [{"x": 2}]}, [{"execution_id": "e", "total": 2}], lambda rows: {"total": sum(r["x"] for r in rows)}, ["total"])
        bad = compare_aggregates({"e": [{"x": 2}]}, [{"execution_id": "e", "total": 3}], lambda rows: {"total": sum(r["x"] for r in rows)}, ["total"])
        self.assertEqual(good.status, "passed"); self.assertEqual(bad.status, "failed")

    def test_secure_root_absence_is_tri_stated_without_path(self):
        descriptor = Path("ml/experiments/post_v037_audit/secure_artifact_reference.yaml")
        result = verify(None, descriptor)
        self.assertEqual(result["status"], "secure_artifacts_not_available"); self.assertNotIn("path", result)


if __name__ == "__main__": unittest.main()
