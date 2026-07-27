# Точка входа аудитора

## Порядок проверки

1. Сопоставьте [human status](../status/current-status.md) с обоими YAML registries.
2. Проверьте candidate registry и candidate manifest.
3. Найдите stage в [protocol index](../protocols/index.md).
4. Откройте policy result, manifest, detached SHA и claim ledger через [reports index](../reports/index.md).
5. Прочитайте limitations и negative results.
6. Выполните reproduction command только в разрешённой локальной области.
7. Проверьте [protected set](../audit/protected_documentation_v2.json).

Document summary не имеет приоритета над frozen policy. Baseline manifest mismatch,
если он существовал до текущего прохода, фиксируется отдельно и не скрывается.
