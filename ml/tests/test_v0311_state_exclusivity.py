import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311StateExclusivity(unittest.TestCase):
    def test_state_exclusivity(self):
        assert_case("state_exclusivity")
