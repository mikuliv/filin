from checks import unittest, verify_case

class TestV0315ActivityKey(unittest.TestCase):
    def test_activity_key(self): verify_case(self, __name__.split(".")[-1])
