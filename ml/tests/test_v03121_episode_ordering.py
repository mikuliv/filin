import unittest
from ml.tests._v03121_support import V03121Mixin,load,ROOT,REPORT,yaml

class V03121EpisodeOrdering(V03121Mixin,unittest.TestCase):
    def test_requirement(self): self.assertEqual(load('v039_episode_delay_summary.json')['causal_alert_window_counts'],{'1':29,'2':1,'3':0})

