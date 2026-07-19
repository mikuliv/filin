import unittest
from ml.tests._v03121_support import V03121Mixin,load,ROOT,REPORT,yaml

class V03121V038CountChain(V03121Mixin,unittest.TestCase):
    def test_requirement(self): self.assertEqual(load('v038_count_provenance.json')['count_chain']['scored_rows'],216)

