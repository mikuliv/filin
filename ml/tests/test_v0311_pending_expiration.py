import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311PendingExpiration(unittest.TestCase):
    def test_pending_expiration(self):
        assert_case("pending_expiration")
