from checks import unittest, verify_case

class TestV0315ProtocolFreeze(unittest.TestCase):
    def test_protocol_freeze(self): verify_case(self, __name__.split(".")[-1])
