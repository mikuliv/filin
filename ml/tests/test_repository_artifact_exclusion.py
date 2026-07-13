import unittest

from tools.audit.check_repository_artifacts import violations


class TestRepositoryArtifactExclusion(unittest.TestCase):
    def test_protected_and_generated_files_are_rejected(self):
        paths = ["lab/output/run/a.csv", "ml/artifacts/model.joblib", "x/capture.pcap", "ml/__pycache__/a.pyc"]
        self.assertEqual(len(violations(paths)), 4)

    def test_public_descriptors_and_sources_are_allowed(self):
        self.assertEqual(violations(["ml/experiments/post_v037_audit/secure_artifact_reference.yaml", "tools/audit/a.py"]), [])


if __name__ == "__main__": unittest.main()
