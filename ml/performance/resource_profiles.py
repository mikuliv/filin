"""Загрузка и выбор безопасных resource profiles."""
from pathlib import Path
import yaml

def load_profiles(path: Path) -> dict:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if value["memory"]["minimum_free_system_memory_gb"] < 8: raise ValueError("Требуется минимум 8 ГБ свободной памяти")
    return value

def choose_policy_workers(benchmarks: list[dict]) -> int:
    eligible = [item for item in benchmarks if item.get("equivalent", True) and item.get("completed_policies") == 101]
    if not eligible: raise ValueError("Нет полного эквивалентного benchmark")
    return max(eligible, key=lambda item: item["policies_per_second"])["workers"]
