from checks import unittest, verify_case

class TestV0315BlindLabelGuard(unittest.TestCase):
    def test_blind_label_guard(self): verify_case(self, __name__.split(".")[-1])
