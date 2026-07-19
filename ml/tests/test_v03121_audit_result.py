import unittest
from ml.tests._v03121_support import V03121Mixin,load,ROOT,REPORT,yaml

class V03121AuditResult(V03121Mixin,unittest.TestCase):
    def test_requirement(self): self.assert_result_flag('v03121_audit_completed')

