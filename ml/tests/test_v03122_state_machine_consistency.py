import unittest

from ml.tests._v03122_support import assert_contract


class V03122StateMachineConsistency(unittest.TestCase):
    def test_contract(self):
        assert_contract(self, "state_machine_consistency")

