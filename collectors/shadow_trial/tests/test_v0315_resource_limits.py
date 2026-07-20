from checks import unittest, verify_case

class TestV0315ResourceLimits(unittest.TestCase):
    def test_resource_limits(self): verify_case(self, __name__.split(".")[-1])
