import unittest
from ml.tests._v03121_support import V03121Mixin,load,ROOT,REPORT,yaml

class V03121StageRunner(V03121Mixin,unittest.TestCase):
    def test_requirement(self): self.assertTrue((ROOT/'ml/audits/v0_3_12_1/run_v0_3_12_1_audit.py').is_file())

