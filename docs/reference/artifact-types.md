---
doc_schema: filin_document_v2
title: Типы артефактов
document_type: reference
audience:
  - developer
  - auditor
lifecycle: current
authoritative_for: []
source_of_truth:
  - bundle_manifests
last_reviewed_stage: v0.4.4
generated: false
evidence_immutable: false
---

# Типы артефактов

- **protocol** — заранее зафиксированные scope, inputs, gates и запреты;
- **policy result** — machine-readable итог gates;
- **bundle manifest** — список paths, sizes, roles и SHA;
- **detached SHA** — отдельная фиксация identity manifest;
- **claim-evidence ledger** — связь assertions и supporting artifacts;
- **run journal** — команды, timestamps и environment details;
- **summary** — human-readable итог без собственной расширяющей силы;
- **contract/schema** — versioned форма и ограничения данных;
- **semantic SHA** — identity нормализованного значимого содержимого;
- **runtime overlay** — изменяемое состояние, не frozen evidence по умолчанию.

Навигация: [контракты](../contracts/index.md), [протоколы](../protocols/index.md),
[отчёты](../reports/index.md).
