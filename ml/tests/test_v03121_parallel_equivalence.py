import unittest
from ml.tests._v03121_support import V03121Mixin,load,ROOT,REPORT,yaml

class V03121ParallelEquivalence(V03121Mixin,unittest.TestCase):
    def test_requirement(self): self.assertTrue(load('performance_preflight.json')['exact_equivalence'])

