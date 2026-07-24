from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ml.experiments.v0_3_18.negative_scenarios import run_negative_scenarios


class NegativeScenarioTests(unittest.TestCase):
    def test_all_forty_scenarios_are_rejected(self):
        result = run_negative_scenarios()
        self.assertEqual(result["scenario_count"], 40)
        self.assertEqual(result["rejected_count"], 40)
        self.assertEqual(result["failed_count"], 0)
        self.assertTrue(result["all_negative_scenarios_rejected"])
        self.assertEqual(len({row["case_id"] for row in result["results"]}), 40)


if __name__ == "__main__":
    unittest.main()
