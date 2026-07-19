import unittest

from ml.tests._v03122_support import assert_contract


class V03122ProtocolFreeze(unittest.TestCase):
    def test_contract(self):
        assert_contract(self, "protocol_freeze")

