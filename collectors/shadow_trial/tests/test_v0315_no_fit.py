from checks import unittest, verify_case

class TestV0315NoFit(unittest.TestCase):
    def test_no_fit(self): verify_case(self, __name__.split(".")[-1])
