import unittest
from ml.performance.resource_profiles import choose_policy_workers
class TestProfiles(unittest.TestCase):
 def test_choose_fastest(self): self.assertEqual(choose_policy_workers([{"workers":3,"completed_policies":101,"policies_per_second":2},{"workers":6,"completed_policies":101,"policies_per_second":4}]),6)
