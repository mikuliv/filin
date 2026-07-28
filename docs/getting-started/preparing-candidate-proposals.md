# Подготовка предложения кандидата

1. Запустите консоль только на `127.0.0.1` с `FILIN_CONSOLE_TOKEN`.
2. Откройте «Предложения кандидатов» и выберите единственные allowlist dataset, split и recipe.
3. Создайте draft, выполните validation и dry run.
4. Запустите два независимых обучения и проверьте reproducibility.
5. Заморозьте proposal; только после этого выполняйте internal screening и сравнение.

Все результаты сохраняются в локальной SQLite/runtime области. Не переносите model binary или dataset в Git. На этом этапе proposal не является кандидатом.
