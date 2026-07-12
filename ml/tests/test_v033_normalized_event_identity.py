from __future__ import annotations

import unittest


class NormalizedEventIdentityTests(unittest.TestCase):
    def test_event_id_keeps_log_ordinal_when_zeek_uid_is_missing(self) -> None:
        run_id, log_name = "run", "files.log"
        first = f"{run_id}:{log_name}:1:"
        second = f"{run_id}:{log_name}:2:"
        self.assertNotEqual(first, second)
