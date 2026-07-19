import unittest
from ml.tests._v03121_support import V03121Mixin,load,ROOT,REPORT,yaml

class V03121ArtifactInventory(V03121Mixin,unittest.TestCase):
    def test_requirement(self): self.assertGreater(load('v037_artifact_inventory.json')['candidate_file_count'],0)

