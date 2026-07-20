from checks import unittest, verify_case

class TestV0315CaptureLock(unittest.TestCase):
    def test_capture_lock(self): verify_case(self, __name__.split(".")[-1])
