import unittest
from ml.tests._v03121_support import V03121Mixin,load,ROOT,REPORT,yaml,complete_bundle
from tools.audit.validate_regression_bundle import validate
import tempfile
from pathlib import Path

class V03121BundleLabelSeparation(V03121Mixin,unittest.TestCase):
    def test_requirement(self):
        with tempfile.TemporaryDirectory() as tmp:
            data=complete_bundle(Path(tmp)); data['label_table_path']=data['feature_table_path']; data['label_table_sha256']=data['feature_table_sha256']; manifest=Path(tmp)/'bundle.yaml'; manifest.write_text(yaml.safe_dump(data),encoding='utf-8')
            self.assertIn('label_separation_failed',validate(manifest)['errors'])
