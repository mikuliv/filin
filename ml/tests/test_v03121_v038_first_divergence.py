import unittest
from ml.tests._v03121_support import V03121Mixin,load,ROOT,REPORT,yaml

class V03121V038FirstDivergence(V03121Mixin,unittest.TestCase):
    def test_requirement(self): self.assertEqual(load('v038_count_provenance.json')['first_divergence'],'warmup_exclusion_before_scored_rows')

