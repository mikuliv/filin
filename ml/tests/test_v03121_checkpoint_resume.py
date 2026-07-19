import unittest
from ml.tests._v03121_support import V03121Mixin,load,ROOT,REPORT,yaml

class V03121CheckpointResume(V03121Mixin,unittest.TestCase):
    def test_requirement(self): self.assert_report_exists('stage_checkpoint.json')

