from checks import unittest, verify_case

class TestV0315Privacy(unittest.TestCase):
    def test_privacy(self): verify_case(self, __name__.split(".")[-1])
