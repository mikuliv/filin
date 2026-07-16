import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311CheckpointResume(unittest.TestCase):
    def test_checkpoint_resume(self):
        assert_case("checkpoint_resume")
