import unittest
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "docs"))
from validate_documentation import validate  # noqa: E402


class DocumentationLinksTests(unittest.TestCase):
    def test_internal_links_are_valid(self):
        self.assertEqual(validate(ROOT), [])
