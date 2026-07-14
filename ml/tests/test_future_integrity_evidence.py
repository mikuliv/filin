import tempfile
import unittest
import hashlib
import yaml
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
        self.assertEqual(result["status"], "not_executed_secure_artifacts_unavailable"); self.assertNotIn("path", result)

    def test_secure_manifest_class_count_schema_and_hash_are_verified(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact = root / "candidate.bin"
            artifact.write_bytes(b"frozen")
            artifact_hash = hashlib.sha256(artifact.read_bytes()).hexdigest()
            schema_hash = "a" * 64
            manifest = {
                "schema_version": 1, "artifact_type": "test_candidate",
                "artifact_relative_path": "candidate.bin", "artifact_sha256": artifact_hash,
                "feature_schema_sha256": schema_hash, "model_class": "TestModel", "feature_count": 20,
            }
            (root / "manifest.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
            descriptor = {
                "schema_version": 2, "artifact_type": "test_candidate", "external_storage_required": True,
                "artifact_relative_path": "candidate.bin", "manifest_relative_path": "manifest.yaml",
                "expected_manifest_schema_version": 1, "expected_artifact_sha256": artifact_hash,
                "expected_feature_schema_sha256": schema_hash, "expected_model_class": "TestModel",
                "expected_feature_count": 20, "required_environment_variable": "FILIN_SECURE_ARTIFACT_ROOT",
                "verification_command": "test", "sensitive_content_excluded": True,
                "historical_artifact_not_corrected_by_audit": True,
            }
            descriptor_path = root / "descriptor.yaml"
            descriptor_path.write_text(yaml.safe_dump(descriptor), encoding="utf-8")
            result = verify(str(root), descriptor_path)
            self.assertEqual(result["status"], "passed")
            self.assertNotIn("path", result)
            manifest["feature_count"] = 21
            (root / "manifest.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
            self.assertEqual(verify(str(root), descriptor_path)["reason"], "secure_contract_mismatch")

    def test_traversal_and_unknown_descriptor_fields_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            descriptor = yaml.safe_load(Path("ml/experiments/post_v037_audit/secure_artifact_reference.yaml").read_text(encoding="utf-8"))
            descriptor["artifact_relative_path"] = "../escape.bin"
            path = root / "descriptor.yaml"
            path.write_text(yaml.safe_dump(descriptor), encoding="utf-8")
            self.assertEqual(verify(str(root), path)["reason"], "unsafe_artifact_reference")
            descriptor["unexpected"] = True
            path.write_text(yaml.safe_dump(descriptor), encoding="utf-8")
            self.assertEqual(verify(str(root), path)["reason"], "descriptor_schema_mismatch")


if __name__ == "__main__": unittest.main()
