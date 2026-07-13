import unittest
from ml.tests.v036_test_utils import load
class LockTests(unittest.TestCase):
 def test_lock_has_all_hashes(self):
  lock=load('ml/experiments/v0_3_6/holdout_lock_manifest.yaml');self.assertEqual(lock['expected_rows'],252);self.assertEqual(lock['expected_runs'],12);self.assertFalse(lock['holdout_modified_after_lock']);self.assertEqual(len(lock['dataset_sha256']),12)
