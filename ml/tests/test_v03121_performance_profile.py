import unittest
from ml.tests._v03121_support import V03121Mixin,load,ROOT,REPORT,yaml

class V03121PerformanceProfile(V03121Mixin,unittest.TestCase):
    def test_requirement(self): self.assertIn(load('performance_preflight.json')['selected_profile'],('A','B','C'))

