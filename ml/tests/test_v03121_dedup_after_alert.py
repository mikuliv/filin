import unittest
from ml.tests._v03121_support import V03121Mixin,load,ROOT,REPORT,yaml

class V03121DedupAfterAlert(V03121Mixin,unittest.TestCase):
    def test_requirement(self): self.assertFalse(load('state_machine_consistency.json')['first_alert_suppression_found'])

