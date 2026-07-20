from checks import unittest, verify_case

class TestV0315Summary(unittest.TestCase):
    def test_summary(self): verify_case(self, __name__.split(".")[-1])
