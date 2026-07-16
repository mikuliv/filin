import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311ValidationLock(unittest.TestCase):
    def test_validation_lock(self):
        assert_case("validation_lock")
