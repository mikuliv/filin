"""Побайтово восстанавливает защищённые и официальные файлы из исходного HEAD этапа."""
from __future__ import annotations

import io
import json
import subprocess
import zipfile

from tools.docs.validate_russian_narrative import OFFICIAL, ROOT

STARTING_HEAD = "50b97243df84d9f924f40eb16a145a1e1f7c5a2a"
FROZEN_PREFIXES = (
    "backend/",
    "docs/external_review/",
    "ml/reports/",
    "ml/protocols/",
    "ml/experiments/",
    "ml/audits/",
    "lab_console/contracts/",
)


def main() -> int:
    protected_payload = json.loads(
        (ROOT / "docs/audit/protected_documentation_v2.json").read_text(encoding="utf-8")
    )
    protected = {row["path"] for row in protected_payload["files"]} | set(OFFICIAL)
    archive_result = subprocess.run(
        ["git", "archive", "--format=zip", STARTING_HEAD],
        cwd=ROOT,
        capture_output=True,
        check=True,
    )
    restored: list[str] = []
    with zipfile.ZipFile(io.BytesIO(archive_result.stdout)) as archive:
        available = {item.filename for item in archive.infolist() if not item.is_dir()}
        protected.update(name for name in available if name.startswith(FROZEN_PREFIXES))
        for path in sorted(protected):
            if path not in available:
                continue
            expected = archive.read(path)
            # В рабочей конфигурации Git архив получает CRLF, тогда как frozen-хеши
            # и исходные blob-объекты проекта зафиксированы с LF.
            if b"\0" not in expected[:4096]:
                expected = expected.replace(b"\r\n", b"\n")
            target = ROOT / path
            if target.exists() and target.read_bytes() == expected:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(expected)
            restored.append(path)
    print(json.dumps({"starting_head": STARTING_HEAD, "restored_count": len(restored)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
