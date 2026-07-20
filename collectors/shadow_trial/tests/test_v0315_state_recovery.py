from checks import unittest, verify_case

class TestV0315StateRecovery(unittest.TestCase):
    def test_state_recovery(self): verify_case(self, __name__.split(".")[-1])
