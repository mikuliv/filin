import unittest
from ml.performance.equivalence_audit import audit
class TestEquivalence(unittest.TestCase):
 def test_equal(self):
  r={"workers":1,"results":[{"x":1.0}],"canonical_output_sha256":"a"};v={**r,"workers":6};self.assertTrue(audit(r,[v])["parallel_policy_evaluator_equivalent"])
