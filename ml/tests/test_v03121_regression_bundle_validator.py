import unittest
from ml.tests._v03121_support import V03121Mixin,load,ROOT,REPORT,yaml,complete_bundle
from tools.audit.validate_regression_bundle import validate
import tempfile
from pathlib import Path

class V03121RegressionBundleValidator(V03121Mixin,unittest.TestCase):
    def test_requirement(self): self.assertTrue((ROOT/'tools/audit/validate_regression_bundle.py').is_file())
    def test_complete_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            data=complete_bundle(Path(tmp)); manifest=Path(tmp)/"bundle.yaml"; manifest.write_text(yaml.safe_dump(data),encoding="utf-8")
            self.assertTrue(validate(manifest)["valid"])
