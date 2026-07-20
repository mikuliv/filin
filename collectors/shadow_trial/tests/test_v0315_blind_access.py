from checks import unittest, verify_case

class TestV0315BlindAccess(unittest.TestCase):
    def test_blind_access(self): verify_case(self, __name__.split(".")[-1])
