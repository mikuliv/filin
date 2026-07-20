from checks import unittest, verify_case

class TestV0315NoExternalConnection(unittest.TestCase):
    def test_no_external_connection(self): verify_case(self, __name__.split(".")[-1])
