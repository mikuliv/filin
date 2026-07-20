from checks import unittest, verify_case

class TestV0315Bootstrap(unittest.TestCase):
    def test_bootstrap(self): verify_case(self, __name__.split(".")[-1])
