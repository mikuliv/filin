from __future__ import annotations

import pytest

from collectors.shadow.performance import run_profile
from collectors.shadow.tests.behavioral_helpers import events


@pytest.mark.parametrize("workers,batch_size", [(1, 1), (1, 50), (2, 50), (3, 100)])
def test_profile_uses_real_worker_pool_and_batch_path(tmp_path, workers, batch_size):
    report = run_profile(events(120), tmp_path, workers=workers, batch_size=batch_size, repetitions=1)
    assert report["real_worker_pool"]
    assert report["real_batch_delivery"]
    assert report["reconciled"]
    assert report["runs"][0]["sample_count"] > 0
    assert report["runs"][0]["peak_rss_mb"] > 0
    assert report["runs"][0]["queue_peak"] == 120
