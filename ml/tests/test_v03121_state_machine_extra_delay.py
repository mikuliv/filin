import unittest
from ml.tests._v03121_support import V03121Mixin,load,ROOT,REPORT,yaml

class V03121StateMachineExtraDelay(V03121Mixin,unittest.TestCase):
    def test_requirement(self): self.assertEqual(load('v0310_episode_delay_summary.json')['state_machine_extra_delay_count'],0)

