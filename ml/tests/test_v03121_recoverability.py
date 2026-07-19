import unittest
from ml.tests._v03121_support import V03121Mixin,load,ROOT,REPORT,yaml

class V03121Recoverability(V03121Mixin,unittest.TestCase):
    def test_requirement(self): self.assertEqual(load('historical_recoverability.json')['v0.3.6']['classification'],'rebuildable_but_not_frozen')

