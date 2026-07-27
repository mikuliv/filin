---
doc_schema: filin_document_v2
title: Точка входа разработчика
document_type: guide
audience:
  - developer
lifecycle: current
authoritative_for: []
source_of_truth:
  - docs/reference/component-directory.md
last_reviewed_stage: v0.4.4
generated: false
evidence_immutable: false
---

# Точка входа разработчика

1. Прочитайте [границу current/historical](../architecture/current-vs-historical.md).
2. Подготовьте [локальное окружение](local-environment.md).
3. Найдите компонент в [каталоге](../reference/component-directory.md) и прочитайте его README.
4. Проверьте input/output schema через [индекс контрактов](../contracts/index.md).
5. Используйте [справочник команд](../reference/command-reference.md).
6. Запустите тесты компонента и documentation validators.
7. Не изменяйте protected files из [реестра](../audit/protected_documentation_v2.json).

Изменение capability требует отдельного versioned stage, protocol и policy result;
документационный коммит не может разрешить новое поведение.
