from __future__ import annotations

import unittest

from tools.audit.validate_v0318_artifact_exclusion import validate as validate_artifacts
from tools.audit.validate_v0318_docs import validate as validate_docs


class V0318ValidatorTests(unittest.TestCase):
    def test_documentation_package_is_complete(self):
        self.assertTrue(validate_docs()["passed"])

    def test_tracked_artifacts_are_sanitized(self):
        self.assertTrue(validate_artifacts()["artifact_exclusion_passed"])


if __name__ == "__main__":
    unittest.main()
