import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311ScenarioCounts(unittest.TestCase):
    def test_scenario_counts(self):
        assert_case("scenario_counts")
