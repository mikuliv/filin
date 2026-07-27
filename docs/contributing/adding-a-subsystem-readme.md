---
doc_schema: filin_document_v2
title: Добавление README подсистемы
document_type: guide
audience:
  - contributor
lifecycle: current
authoritative_for: []
source_of_truth:
  - docs/contributing/documentation-style.md
last_reviewed_stage: v0.4.4
generated: false
evidence_immutable: false
---

# Добавление README подсистемы

README должен содержать разделы:

1. назначение;
2. статус (`current`, `historical`, `experimental`, `runtime-only`, `frozen evidence`);
3. место в архитектуре;
4. основные каталоги и файлы;
5. разрешённые входы;
6. выходы;
7. границы и запреты;
8. безопасный запуск;
9. тестирование;
10. источники истины и связанные документы.

Команды должны существовать, а scope не должен быть шире code/contracts/policy.
