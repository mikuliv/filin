from checks import unittest, verify_case

class TestV0315ReviewNotLost(unittest.TestCase):
    def test_review_not_lost(self): verify_case(self, __name__.split(".")[-1])
