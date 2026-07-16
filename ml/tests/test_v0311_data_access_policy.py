import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311DataAccessPolicy(unittest.TestCase):
    def test_data_access_policy(self):
        assert_case("data_access_policy")
