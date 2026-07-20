from checks import unittest, verify_case

class TestV0315ContinuousAvailability(unittest.TestCase):
    def test_continuous_availability(self): verify_case(self, __name__.split(".")[-1])
