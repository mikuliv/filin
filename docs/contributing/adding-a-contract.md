---
doc_schema: filin_document_v2
title: Добавление контракта
document_type: guide
audience:
  - contributor
lifecycle: current
authoritative_for: []
source_of_truth:
  - versioned_schemas
last_reviewed_stage: v0.4.4
generated: false
evidence_immutable: false
---

# Добавление контракта

1. Выберите versioned schema ID и owner subsystem.
2. Определите required fields, enums, invariants и unknown-field policy.
3. Добавьте positive/negative tests и consumer validation.
4. Запретите silent migration со старой version.
5. Обновите [contracts index](../contracts/index.md) generator.
6. Если contract frozen stage, включите его SHA в manifest/ledger.

Human description не может ослаблять machine-readable schema.
