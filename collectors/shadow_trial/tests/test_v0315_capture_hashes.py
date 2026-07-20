from checks import unittest, verify_case

class TestV0315CaptureHashes(unittest.TestCase):
    def test_capture_hashes(self): verify_case(self, __name__.split(".")[-1])
