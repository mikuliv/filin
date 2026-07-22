from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]


def prepend(path: Path, text: str) -> None:
    current = path.read_text(encoding="utf-8")
    if "Статус v0.3.15.5" not in current:
        first, separator, rest = current.partition("\n")
        path.write_text(first + "\n\n" + text.strip() + "\n\n" + rest.lstrip("\n"), encoding="utf-8", newline="\n")


def append_history(path: Path) -> None:
    current = path.read_text(encoding="utf-8")
    marker = "<!-- stage-history:end -->"
    if "- v0.3.15.5 —" not in current and marker in current:
        current = current.replace(marker, "- v0.3.15.5 — completed independent holdout; scientific gates passed, runtime contract failed, candidate not promoted.\n" + marker)
        path.write_text(current, encoding="utf-8", newline="\n")


def main() -> int:
    path = ROOT / "docs/status/project-status.yaml"
    status = yaml.safe_load(path.read_text(encoding="utf-8"))
    status.update({"current_completed_stage": "v0.3.15.5", "latest_independent_model_holdout": "v0.3.15.5",
                   "latest_runtime_trial": "v0.3.15.5", "next_allowed_stage": "v0.3.15.5.1",
                   "next_required_work": "Corrective v0.3.15.5.1: candidate-compatible event contract и новая runtime campaign; v0.3.16 запрещён"})
    if not any(row["version"] == "v0.3.15.5" for row in status["stages"]):
        status["stages"].append({"version": "v0.3.15.5", "title": "Независимый перспективный сравнительный holdout",
            "category": "holdout", "chronological_order": 23, "status": "completed",
            "result": "scientific_passed_runtime_contract_failed_not_promoted",
            "primary_report": "docs/experiments/v0_3_15_5.md", "policy_result": "ml/reports/v0_3_15_5/v0_3_15_5_policy_result.json",
            "limitations": "Historical baseline ineligible; frozen event contract отклоняет candidate v03154; v0.3.16 запрещён",
            "superseded_claims": [], "next_stage": "v0.3.15.5.1"})
    path.write_text(yaml.safe_dump(status, allow_unicode=True, sort_keys=False), encoding="utf-8", newline="\n")
    legacy_path = ROOT / "docs/research-state.yaml"
    legacy = yaml.safe_load(legacy_path.read_text(encoding="utf-8"))
    legacy.update({"latest_completed_stage": "v0.3.15.5", "latest_completed_result": "scientific_passed_runtime_contract_failed_not_promoted",
                   "next_allowed_stage": "v0.3.15.5.1"})
    legacy_path.write_text(yaml.safe_dump(legacy, allow_unicode=True, sort_keys=False), encoding="utf-8", newline="\n")
    prepend(ROOT / "README.md", "> Статус v0.3.15.5: independent controlled synthetic holdout завершён. Scientific gates кандидата v0.3.15.4 пройдены, но promotion отклонён: frozen `shadow_event_v1` допускает только historical candidate ID и не принимает `v03154:65a3dd912d845bc1`. v0.3.16, shadow mode, backend integration и production остаются запрещены; следующий допустимый этап — corrective v0.3.15.5.1.")
    prepend(ROOT / "docs/status.md", "Статус v0.3.15.5: этап completed, holdout валиден, абсолютные scientific gates пройдены. Кандидат не promoted из-за несовместимости frozen event contract с candidate ID v03154. Следующий допустимый этап — v0.3.15.5.1; v0.3.16 запрещён.")
    prepend(ROOT / "docs/current-capabilities.md", "Статус v0.3.15.5: scientific качество development-кандидата подтверждено на 3 800 новых scored окнах. Frozen passive event schema несовместима с candidate ID v03154, поэтому runtime delivery, staging connector readiness, shadow mode, backend integration и production не подтверждены.")
    prepend(ROOT / "docs/roadmap.md", "Статус v0.3.15.5: promotion отклонён из-за frozen event-contract mismatch. Следующий допустимый этап — v0.3.15.5.1: заранее замороженная candidate-compatible коррекция контракта и новая runtime campaign. Текущий holdout нельзя повторно использовать для подбора; v0.3.16 остаётся заблокирован.")
    append_history(ROOT / "README.md")
    append_history(ROOT / "docs/roadmap.md")
    replacements = {
        ROOT / "README.md": [("Последний завершённый этап — v0.3.15.4.", "Последний завершённый этап — v0.3.15.5."),
                              ("Следующий разрешённый этап — независимый prospective holdout v0.3.15.5.", "Следующий разрешённый этап — corrective v0.3.15.5.1.")],
        ROOT / "docs/status.md": [("- Текущий завершённый этап: v0.3.15.4.", "- Текущий завершённый этап: v0.3.15.5."),
                                  ("- Следующий разрешённый этап: независимый prospective holdout v0.3.15.5.", "- Следующий разрешённый этап: corrective v0.3.15.5.1.")],
    }
    for document, pairs in replacements.items():
        value = document.read_text(encoding="utf-8")
        for old, new in pairs: value = value.replace(old, new)
        document.write_text(value, encoding="utf-8", newline="\n")
    for document in (ROOT / "docs/experiments.md", ROOT / "docs/development-history.md"):
        value = document.read_text(encoding="utf-8")
        if "v0.3.15.5" not in value:
            value += "\n\n## v0.3.15.5\n\nНезависимый controlled synthetic holdout завершён: scientific gates пройдены, runtime contract gate не пройден, candidate не promoted.\n"
            document.write_text(value, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
