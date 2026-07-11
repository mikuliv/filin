from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class RepositoryRootLayoutTests(unittest.TestCase):
    def test_project_uses_root_layout_without_filin_directory(self):
        self.assertFalse((ROOT / "filin").exists())
        for name in ("backend", "collectors", "datasets", "docs", "examples", "lab", "ml", "runtime", "tools"):
            self.assertTrue((ROOT / name).is_dir(), name)

    def test_root_documentation_and_runtime_rules_exist(self):
        self.assertTrue((ROOT / "README.md").is_file())
        self.assertTrue((ROOT / "docs" / "index.md").is_file())
        ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
        for rule in ("lab/output/", "ml/reports/", "ml/artifacts/", "*.pcap"):
            self.assertIn(rule, ignored)

    def test_working_python_code_has_no_legacy_root_paths(self):
        forbidden = ("filin/lab", "filin/ml", "filin/docs", "H:\\Anomalyzer")
        for source in ROOT.rglob("*.py"):
            if ".git" in source.parts or "tests" in source.parts:
                continue
            text = source.read_text(encoding="utf-8")
            self.assertFalse(any(value in text for value in forbidden), source)
