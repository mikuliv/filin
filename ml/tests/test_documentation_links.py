import unittest
from pathlib import Path
import sys
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "docs"))
from validate_documentation import validate  # noqa: E402
from tools.docs.documentation_v2 import link_findings  # noqa: E402


class DocumentationLinksTests(unittest.TestCase):
    def test_internal_links_are_valid(self):
        self.assertEqual(validate(ROOT), [])

    def test_missing_link_is_rejected(self):
        with TemporaryDirectory(prefix="filin-doc-link-") as directory:
            root = Path(directory)
            fixture = root / "fixture.md"
            fixture.write_text("[тест](definitely_missing_documentation_target.md)\n", encoding="utf-8")
            broken, anchors, escapes = link_findings(fixture, root)
            self.assertIn("definitely_missing_documentation_target.md", broken)
            self.assertEqual(anchors, [])
            self.assertEqual(escapes, [])
