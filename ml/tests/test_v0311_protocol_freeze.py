import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311ProtocolFreeze(unittest.TestCase):
    def test_protocol_freeze(self):
        assert_case("protocol_freeze")
