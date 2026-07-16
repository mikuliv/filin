import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311WeakPending(unittest.TestCase):
    def test_weak_pending(self):
        assert_case("weak_pending")
