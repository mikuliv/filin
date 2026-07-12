from __future__ import annotations

ALLOWED_TARGETS = {"target-web", "target-api", "control-api", "internal-dns", "target-ssh-sim"}
MAX_ACTIONS_PER_SECOND = 3
MAX_CLIENTS = 4
MAX_ACTIONS_PER_INTERVAL = 40


def validate_background_config(config: dict) -> None:
    if config.get("target") not in ALLOWED_TARGETS:
        raise ValueError("Фоновая цель не входит в allowlist.")
    if int(config.get("clients", 0)) > MAX_CLIENTS:
        raise ValueError("Превышен лимит фоновых клиентов.")
    if float(config.get("actions_per_second", 0)) > MAX_ACTIONS_PER_SECOND:
        raise ValueError("Превышен лимит частоты фоновых действий.")
    if int(config.get("actions_per_interval", 0)) > MAX_ACTIONS_PER_INTERVAL:
        raise ValueError("Превышен лимит фоновых действий на execution interval.")
