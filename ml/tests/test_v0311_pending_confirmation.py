import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311PendingConfirmation(unittest.TestCase):
    def test_pending_confirmation(self):
        assert_case("pending_confirmation")
