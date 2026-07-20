from checks import unittest, verify_case

class TestV0315StageRunner(unittest.TestCase):
    def test_stage_runner(self): verify_case(self, __name__.split(".")[-1])
