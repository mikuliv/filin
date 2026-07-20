from checks import unittest, verify_case

class TestV0315RestartBoundaryInvariance(unittest.TestCase):
    def test_restart_boundary_invariance(self): verify_case(self, __name__.split(".")[-1])
