from checks import unittest, verify_case

class TestV0315CandidateIntegrity(unittest.TestCase):
    def test_candidate_integrity(self): verify_case(self, __name__.split(".")[-1])
