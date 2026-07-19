import unittest
from ml.tests._v03121_support import V03121Mixin,load,ROOT,REPORT,yaml

class V03121PrimaryReasonPrecedence(V03121Mixin,unittest.TestCase):
    def test_requirement(self): self.assertIn('input_or_mapping_error',load('v0310_episode_delay_summary.json')['primary_reason_counts'])

