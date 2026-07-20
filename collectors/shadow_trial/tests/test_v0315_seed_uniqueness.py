from checks import unittest, verify_case

class TestV0315SeedUniqueness(unittest.TestCase):
    def test_seed_uniqueness(self): verify_case(self, __name__.split(".")[-1])
