import unittest
from ml.tests._v03121_support import V03121Mixin,load,ROOT,REPORT,yaml

class V03121IdenticalRateAudit(V03121Mixin,unittest.TestCase):
    def test_requirement(self): self.assertIn('артефакт',load('cross_benchmark_delay_comparison.json')['identical_rate_explanation'])

