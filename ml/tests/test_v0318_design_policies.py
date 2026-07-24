from __future__ import annotations

import unittest

from ml.experiments.v0_3_18.freeze_design import (
    blind_protocol,
    contamination,
    data_acceptance,
    metric_policy,
    role_matrix,
    stop_conditions,
    sufficiency_policy,
)


class DesignPolicyTests(unittest.TestCase):
    def test_roles_are_complete_and_conflict_free_in_rehearsal(self):
        matrix = role_matrix()
        self.assertEqual(len(matrix["roles"]), 7)
        self.assertEqual(matrix["role_conflict_count"], 0)
        self.assertFalse(matrix["roles"]["trial_operator"]["labels_access_before_prediction_freeze"])
        self.assertFalse(matrix["roles"]["label_custodian"]["predictions_access_before_prediction_freeze"])

    def test_only_confirmed_input_is_supported(self):
        policy = data_acceptance()
        self.assertEqual(policy["supported_input_forms"], ["pcap"])
        self.assertFalse(policy["row_random_split_proves_independence"])

    def test_contamination_requires_attestation_for_unverifiable_checks(self):
        policy = contamination()
        self.assertGreaterEqual(len(policy["checks"]), 10)
        self.assertFalse(policy["different_filename_proves_independence"])
        self.assertFalse(policy["full_independence_claim_without_all_checks"])

    def test_blind_workflow_freezes_predictions_before_reveal(self):
        protocol = blind_protocol()
        steps = protocol["steps"]
        self.assertLess(steps.index("prediction_commitment"), steps.index("label_reveal"))
        self.assertFalse(protocol["post_reveal_prediction_change_allowed"])

    def test_metrics_do_not_invent_external_thresholds(self):
        policy = metric_policy()
        self.assertTrue(policy["unresolved_external_acceptance_thresholds"])
        self.assertFalse(policy["post_hoc_threshold_selection_allowed"])
        self.assertFalse(policy["policy_complete_for_real_trial_execution"])
        self.assertFalse(policy["scientific_evidence"])

    def test_sample_plan_is_context_approved(self):
        policy = sufficiency_policy()
        self.assertFalse(policy["universal_numeric_minimum_defined"])
        self.assertTrue(policy["approval_required_before_holdout_commitment"])

    def test_all_mandatory_stop_conditions_are_frozen(self):
        policy = stop_conditions()
        self.assertEqual(len(policy["conditions"]), 28)
        self.assertTrue(policy["negative_result_must_be_preserved"])


if __name__ == "__main__":
    unittest.main()
