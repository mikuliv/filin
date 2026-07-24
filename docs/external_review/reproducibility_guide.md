# Руководство по воспроизводимости

1. Использовать чистый каталог и поддерживаемый Python.
2. Не предоставлять Git history, сеть или backend.
3. Запустить `tools/external_review/verify_external_review_package.py` с путём
   package.
4. Сверить `root_commitment` и три parent commitments.
5. Запустить v0.3.18 unit tests на sanitized fixtures.
6. Повторить evaluator и сравнить canonical JSON result.

Архив package не хранится в Git. Детерминизм обеспечивается allowlist,
сортировкой путей, content hashes и нормализованным mtime.
