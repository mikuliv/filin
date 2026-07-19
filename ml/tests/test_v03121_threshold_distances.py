import unittest
from ml.tests._v03121_support import V03121Mixin,load,ROOT,REPORT,yaml

class V03121ThresholdDistances(V03121Mixin,unittest.TestCase):
    def test_requirement(self): self.assertIn('threshold_gap_summary',load('v039_episode_delay_summary.json'))

