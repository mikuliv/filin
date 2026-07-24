from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.external_review.build_external_review_package import build_package
from tools.external_review.frozen_evaluator import EvaluationError, evaluate
from tools.external_review.verify_external_review_package import verify


class EvaluatorTests(unittest.TestCase):
    def setUp(self):
        self.labels = [
            {"episode_id": "episode-001", "class": "benign"},
            {"episode_id": "episode-002", "class": "beacon"},
        ]
        self.predictions = [
            {"episode_id": "episode-001", "predicted_class": "benign", "abstained": False},
            {"episode_id": "episode-002", "predicted_class": None, "abstained": True},
        ]

    def test_evaluator_is_deterministic_and_marks_rehearsal(self):
        first = evaluate(self.predictions, self.labels)
        second = evaluate(list(reversed(self.predictions)), list(reversed(self.labels)))
        self.assertEqual(first, second)
        self.assertFalse(first["scientific_evidence"])
        self.assertEqual(first["coverage"], 0.5)

    def test_missing_duplicate_unknown_and_invalid_abstention_rejected(self):
        with self.assertRaises(EvaluationError):
            evaluate(self.predictions[:1], self.labels)
        with self.assertRaises(EvaluationError):
            evaluate([self.predictions[0], self.predictions[0]], self.labels)
        with self.assertRaises(EvaluationError):
            evaluate(self.predictions + [{"episode_id": "unknown", "predicted_class": "benign", "abstained": False}], self.labels)
        broken = [dict(row) for row in self.predictions]
        broken[1]["abstained"] = False
        with self.assertRaises(EvaluationError):
            evaluate(broken, self.labels)


class PackageTests(unittest.TestCase):
    def test_build_and_standalone_verify(self):
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "package"
            manifest = build_package(package, candidate_commitment="1" * 64, protocol_commitment="2" * 64, evaluator_commitment="3" * 64)
            result = verify(package)
            self.assertTrue(result["package_verification_passed"])
            self.assertEqual(result["root_commitment"], manifest["root_commitment"])
            self.assertFalse(result["network_used"])
            self.assertFalse(result["backend_used"])

    def test_corruption_extra_missing_and_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "package"
            build_package(package, candidate_commitment="1" * 64, protocol_commitment="2" * 64, evaluator_commitment="3" * 64)
            manifest = json.loads((package / "package_manifest.json").read_text(encoding="utf-8"))
            target = package / Path(*manifest["files"][0]["path"].split("/"))
            original = target.read_bytes()
            target.write_bytes(original + b"x")
            self.assertFalse(verify(package)["package_verification_passed"])
            target.write_bytes(original)
            (package / "extra.txt").write_text("extra", encoding="utf-8")
            self.assertFalse(verify(package)["package_verification_passed"])
            (package / "extra.txt").unlink()
            target.unlink()
            self.assertFalse(verify(package)["package_verification_passed"])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(original)
            manifest["files"][0]["path"] = "../escape"
            (package / "package_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            self.assertFalse(verify(package)["package_verification_passed"])


if __name__ == "__main__":
    unittest.main()
