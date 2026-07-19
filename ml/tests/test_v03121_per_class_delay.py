import unittest
from ml.tests._v03121_support import V03121Mixin,load,ROOT,REPORT,yaml

class V03121PerClassDelay(V03121Mixin,unittest.TestCase):
    def test_requirement(self): self.assertEqual(len(load('per_class_delay.json')['v0.3.9']),5)

