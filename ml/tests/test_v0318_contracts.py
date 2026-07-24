from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ml.experiments.v0_3_18.contracts import SCHEMAS, validate_contract
from tools.external_review.canonical_commitment import (
    CommitmentError,
    canonical_bytes,
    commitment_receipt,
    commitment_sha256,
    confined_path,
    load_json_strict,
    manifest_root,
    verify_receipt,
)


class CanonicalCommitmentTests(unittest.TestCase):
    def test_canonical_order_is_deterministic(self):
        self.assertEqual(canonical_bytes({"b": 2, "a": 1}), b'{"a":1,"b":2}')

    def test_duplicate_keys_rejected(self):
        with self.assertRaises(CommitmentError):
            load_json_strict('{"a":1,"a":2}')

    def test_non_finite_numbers_rejected(self):
        for raw in ('{"a":NaN}', '{"a":Infinity}', '{"a":-Infinity}'):
            with self.assertRaises(CommitmentError):
                load_json_strict(raw)

    def test_receipt_verifies_and_detects_mutation(self):
        value = {"a": 1}
        receipt = commitment_receipt(value, subject="fixture")
        self.assertTrue(verify_receipt(value, receipt))
        self.assertFalse(verify_receipt({"a": 2}, receipt))

    def test_paths_are_confined(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(confined_path(root, "a/b.json"), root / "a" / "b.json")
            for raw in ("../x", "C:\\x", "/x", "\\\\server\\share"):
                with self.assertRaises(CommitmentError):
                    confined_path(root, raw)

    def test_manifest_tree_rejects_duplicates(self):
        entry = {"path": "a.json", "sha256": "0" * 64, "size": 1}
        self.assertEqual(len(manifest_root([entry])), 64)
        with self.assertRaises(CommitmentError):
            manifest_root([entry, entry])


class ContractTests(unittest.TestCase):
    def test_all_schemas_are_draft_2020_12(self):
        self.assertEqual(len(SCHEMAS), 13)
        for name, schema in SCHEMAS.items():
            self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
            self.assertEqual(schema["properties"]["schema_version"]["const"], name)

    def test_prediction_duplicate_and_abstention_rejected(self):
        value = {
            "schema_version": "prediction_submission_v1",
            "holdout_id": "holdout-001",
            "candidate_commitment": "0" * 64,
            "predictions": [
                {"episode_id": "episode-001", "predicted_class": "benign", "abstained": False},
                {"episode_id": "episode-001", "predicted_class": None, "abstained": False},
            ],
        }
        errors = validate_contract("prediction_submission_v1", value)
        self.assertIn("predictions:duplicate_episode_id", errors)
        self.assertIn("predictions:invalid_abstention_semantics", errors)

    def test_chronology_rejects_early_reveal(self):
        events = []
        names = ["dataset_commitment", "label_commitment", "label_reveal", "candidate_commitment",
                 "evaluator_commitment", "blind_handoff", "prediction_commitment", "evaluation"]
        for index, name in enumerate(names, 1):
            events.append({"sequence": index, "event": name, "occurred_at_ns": index,
                           "role_attestation": "0" * 64})
        value = {"schema_version": "external_trial_chronology_v1", "rehearsal_id": "rehearsal-001", "events": events}
        self.assertIn("events:label_reveal_before_prediction_commitment", validate_contract("external_trial_chronology_v1", value))


if __name__ == "__main__":
    unittest.main()
