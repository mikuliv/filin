import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311StageRunner(unittest.TestCase):
    def test_stage_runner(self):
        assert_case("stage_runner")
