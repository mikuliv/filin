from checks import unittest, verify_case

class TestV0315PreviousStageIntegrity(unittest.TestCase):
    def test_previous_stage_integrity(self): verify_case(self, __name__.split(".")[-1])
