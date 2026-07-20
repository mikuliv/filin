from checks import unittest, verify_case

class TestV0315Conformal(unittest.TestCase):
    def test_conformal(self): verify_case(self, __name__.split(".")[-1])
