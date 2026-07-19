import unittest

from ml.tests._v03122_support import assert_contract


class V03122RegistryFreeze(unittest.TestCase):
    def test_contract(self):
        assert_contract(self, "registry_freeze")

