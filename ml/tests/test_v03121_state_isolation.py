import unittest
from ml.tests._v03121_support import V03121Mixin,load,ROOT,REPORT,yaml

class V03121StateIsolation(V03121Mixin,unittest.TestCase):
    def test_requirement(self): self.assert_state_zero('cross_run_state_transfer_count')

