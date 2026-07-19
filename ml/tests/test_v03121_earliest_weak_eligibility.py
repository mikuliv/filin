import unittest
from ml.tests._v03121_support import V03121Mixin,load,ROOT,REPORT,yaml

class V03121EarliestWeakEligibility(V03121Mixin,unittest.TestCase):
    def test_requirement(self): self.assertEqual(load('v039_episode_delay_summary.json')['readiness_by_second_counts']['weak_started_by_second'],30)

