import unittest
from ml.tests._v03121_support import V03121Mixin,load,ROOT,REPORT,yaml,complete_bundle
from tools.audit.validate_regression_bundle import validate
import tempfile
from pathlib import Path

class V03121BundleHashMismatch(V03121Mixin,unittest.TestCase):
    def test_requirement(self):
        with tempfile.TemporaryDirectory() as tmp:
            data=complete_bundle(Path(tmp)); data['feature_table_sha256']='0'*64; manifest=Path(tmp)/'bundle.yaml'; manifest.write_text(yaml.safe_dump(data),encoding='utf-8')
            self.assertIn('hash_mismatch:feature_table_path',validate(manifest)['errors'])
