import unittest
from ml.experiments.v0_3_13.blind_label_guard import BlindLabelGuard
from ml.experiments.v0_3_13.causal_order_invariance import canonical_sort


class NegativeGuards(unittest.TestCase):
    def test_label_vault_locked_before_prediction(self):
        with self.assertRaises(PermissionError): BlindLabelGuard().unlock(lambda: {})

    def test_missing_causal_order_is_blocked(self):
        with self.assertRaises(ValueError): canonical_sort([{"benchmark_id":"b","run_id":"r","activity_key":"a","immutable_row_id":"i"}])

    def test_duplicate_causal_order_is_blocked(self):
        row={"benchmark_id":"b","run_id":"r","activity_key":"a","causal_order":1}
        with self.assertRaises(ValueError): canonical_sort([{**row,"immutable_row_id":"i1"},{**row,"immutable_row_id":"i2"}])

