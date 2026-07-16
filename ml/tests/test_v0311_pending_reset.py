import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311PendingReset(unittest.TestCase):
    def test_pending_reset(self):
        assert_case("pending_reset")
