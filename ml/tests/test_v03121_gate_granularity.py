import unittest
from ml.tests._v03121_support import V03121Mixin,load,ROOT,REPORT,yaml

class V03121GateGranularity(V03121Mixin,unittest.TestCase):
    def test_requirement(self): self.assertEqual(load('gate_granularity_audit.json')['v0.3.10']['minimum_additional_detected_episodes_to_pass'],1)

