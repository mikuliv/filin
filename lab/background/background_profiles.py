from __future__ import annotations

import random


SOURCES = ("web_browsing", "api_status", "dns_discovery", "update_check", "log_shipping", "monitoring_heartbeat")


def build_background_profile(seed: int, group: str) -> dict:
    rng = random.Random(f"v033-background:{seed}:{group}")
    clients = 2 if group in {"mixed", "hard_negative"} else rng.randint(3, 4)
    return {
        "background_profile_id": f"{group}_background_v1",
        "background_seed": seed,
        "clients": clients,
        "actions_per_second": round(rng.uniform(1.0, 2.5), 2),
        "actions_per_interval": rng.randint(12, 32),
        "sources": list(SOURCES),
    }
