from checks import unittest, verify_case

class TestV0315StatePersistence(unittest.TestCase):
    def test_state_persistence(self): verify_case(self, __name__.split(".")[-1])
