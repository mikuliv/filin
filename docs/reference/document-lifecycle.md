---
doc_schema: filin_document_v2
title: Жизненный цикл документов
document_type: reference
audience:
  - contributor
  - auditor
lifecycle: current
authoritative_for:
  - document_lifecycle
source_of_truth:
  - docs/contributing/documentation-style.md
last_reviewed_stage: v0.4.4
generated: false
evidence_immutable: false
---

# Жизненный цикл документов

| lifecycle | Значение | Разрешённое изменение |
|---|---|---|
| `current` | текущий канонический документ | обычный reviewed commit |
| `historical` | описание завершённого состояния | только явная errata/навигация |
| `redirect` | совместимый старый путь | только смена canonical target |
| `generated` | представление реестра/дерева | только через generator |
| frozen | bytes входят в protected set | изменение запрещено |

Current canonical docs используют `filin_document_v2` front matter. Frozen files
не получают front matter задним числом; metadata хранится в inventory.

Перед перемещением проверяются incoming links и manifests. Старый путь сохраняется
redirect, если он публичен, исторически упомянут или contractually referenced.
