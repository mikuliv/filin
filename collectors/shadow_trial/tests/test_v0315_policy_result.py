from checks import unittest, verify_case

class TestV0315PolicyResult(unittest.TestCase):
    def test_policy_result(self): verify_case(self, __name__.split(".")[-1])
