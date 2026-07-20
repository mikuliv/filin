from checks import unittest, verify_case

class TestV0315FailSafe(unittest.TestCase):
    def test_fail_safe(self): verify_case(self, __name__.split(".")[-1])
