import unittest
from ml.performance.parallel_policy_evaluator import canonical_bytes,sha256
class TestParallel(unittest.TestCase):
 def test_canonical_order(self): self.assertEqual(canonical_bytes({"b":1,"a":2}),canonical_bytes({"a":2,"b":1}))
 def test_worker_error_marker_hashable(self): self.assertEqual(sha256({"a":1}),sha256({"a":1}))
