import unittest
from ml.tests._v03121_support import V03121Mixin,load,ROOT,REPORT,yaml

class V03121DelayReasonTaxonomy(V03121Mixin,unittest.TestCase):
    def test_requirement(self): self.assertEqual(load('v039_episode_delay_summary.json')['primary_reason_counts'],{'input_or_mapping_error':8})

