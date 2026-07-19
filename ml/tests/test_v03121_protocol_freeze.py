import unittest
from ml.tests._v03121_support import V03121Mixin,load,ROOT,REPORT,yaml

class V03121ProtocolFreeze(V03121Mixin,unittest.TestCase):
    def test_requirement(self): self.assert_result_flag('audit_protocol_frozen')

