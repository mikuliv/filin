import unittest
from ml.tests._v03121_support import V03121Mixin,load,ROOT,REPORT,yaml

class V03121WeakConfirmation(V03121Mixin,unittest.TestCase):
    def test_requirement(self): self.assertEqual(load('v039_episode_delay_summary.json')['readiness_by_second_counts']['weak_confirmed_by_second'],29)

