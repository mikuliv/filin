import unittest
from ml.tests._v03121_support import V03121Mixin,load,ROOT,REPORT,yaml

class V03121EarliestStrongEligibility(V03121Mixin,unittest.TestCase):
    def test_requirement(self): self.assertEqual(load('v0310_episode_delay_summary.json')['readiness_by_second_counts']['strong_ready_by_second'],60)

