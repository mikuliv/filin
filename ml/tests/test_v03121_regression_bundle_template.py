import unittest
from ml.tests._v03121_support import V03121Mixin,load,ROOT,REPORT,yaml

class V03121RegressionBundleTemplate(V03121Mixin,unittest.TestCase):
    def test_requirement(self): self.assertFalse(yaml.safe_load((ROOT/'ml/templates/regression_bundle_manifest.template.yaml').read_text(encoding='utf-8'))['regression_bundle_complete'])

