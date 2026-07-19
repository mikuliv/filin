import unittest
from ml.tests._v03121_support import V03121Mixin,load,ROOT,REPORT,yaml

class V03121EpisodeLengthDelay(V03121Mixin,unittest.TestCase):
    def test_requirement(self): self.assertIn('3',load('per_episode_length_delay.json')['v0.3.9'])

