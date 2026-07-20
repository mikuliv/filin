from checks import unittest, verify_case

class TestV0315CaptureCounts(unittest.TestCase):
    def test_capture_counts(self): verify_case(self, __name__.split(".")[-1])
