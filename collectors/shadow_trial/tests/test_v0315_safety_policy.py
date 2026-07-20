from checks import unittest, verify_case

class TestV0315SafetyPolicy(unittest.TestCase):
    def test_safety_policy(self): verify_case(self, __name__.split(".")[-1])
