"""Стабильный renderer полной version history из authoritative status."""
from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "docs/status/project-status.yaml"
TARGET = ROOT / "docs/status/version-history.md"


def render() -> str:
    status = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))
    lines = [
        "# История версий",
        "",
        "Источник структуры этапов — [`project-status.yaml`](project-status.yaml).",
        "Historical results приведены без переоценки.",
        "",
    ]
    for row in status["stages"]:
        version = row["version"]
        lines.extend(
            [
                f"## {version} — {row['title']}",
                "",
                f"**Статус:** `{row['status']}`.",
                "",
                f"**Назначение:** `{row['category']}`.",
                "",
                f"**Результат:** `{row['result']}`.",
                "",
                f"**Ограничение:** {row['limitations']}.",
                "",
                f"**Следующий разрешённый шаг:** `{row['next_stage'] or 'не был установлен'}`.",
                "",
                f"**Evidence:** [`{row['primary_report']}`](../../{row['primary_report']}).",
                "",
            ]
        )
        if row.get("policy_result"):
            policy = row["policy_result"]
            if (ROOT / policy).is_file():
                lines.extend([f"Policy: [`{policy}`](../../{policy}).", ""])
            else:
                lines.extend(
                    [
                        f"Policy path из historical registry: `{policy}` "
                        "(tracked artifact отсутствует).",
                        "",
                    ]
                )
        if row.get("superseded_claims"):
            lines.extend(
                [
                    "Superseded claims: "
                    + ", ".join(f"`{claim}`" for claim in row["superseded_claims"])
                    + ".",
                    "",
                ]
            )
    lines.extend(
        [
            "## Текущий переход",
            "",
            "После v0.3.18 разрешён только v0.3.19 package review и согласование",
            "trial plan. Фактический external trial не разрешён.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    TARGET.write_text(render(), encoding="utf-8", newline="\n")
    print(f"rendered={TARGET.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
