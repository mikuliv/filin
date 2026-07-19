import unittest
from ml.tests._v03121_support import V03121Mixin,load,ROOT,REPORT,yaml

class V03121AlertWindowReconstruction(V03121Mixin,unittest.TestCase):
    def test_requirement(self): self.assert_timing('v0310',{'1':23,'2':21,'3':16})

