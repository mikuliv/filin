import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311CaptureLock(unittest.TestCase):
    def test_capture_lock(self):
        assert_case("capture_lock")
