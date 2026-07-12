from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from check_release_images import find_mutable_images  # noqa: E402


class ReproducibilityGuardsTests(unittest.TestCase):
    def test_release_guard_finds_latest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            compose = Path(directory) / "compose.yml"
            compose.write_text("services:\n  zeek:\n    image: zeek/zeek:latest\n", encoding="utf-8")
            self.assertEqual(find_mutable_images(compose), ["zeek/zeek:latest"])

    def test_runtime_artifacts_are_ignored(self) -> None:
        ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
        for pattern in ("*.pcap", "*.joblib", "lab/output/", "ml/reports/"):
            self.assertIn(pattern, ignored)
