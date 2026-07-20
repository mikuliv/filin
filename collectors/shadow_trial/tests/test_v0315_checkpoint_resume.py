from checks import unittest, verify_case

class TestV0315CheckpointResume(unittest.TestCase):
    def test_checkpoint_resume(self): verify_case(self, __name__.split(".")[-1])
