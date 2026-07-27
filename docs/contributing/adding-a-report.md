---
doc_schema: filin_document_v2
title: Добавление отчёта
document_type: guide
audience:
  - contributor
lifecycle: current
authoritative_for: []
source_of_truth:
  - bundle_manifest_contracts
last_reviewed_stage: v0.4.4
generated: false
evidence_immutable: false
---

# Добавление отчёта

Report размещается в versioned stage directory и содержит scope, result, metrics,
limitations и links на protocol/policy. Bundle manifest фиксирует path, size и SHA;
detached SHA фиксирует manifest, ledger — claims.

После freeze report не редактируется. Correction оформляется новым stage, errata
или current overview. Обновите [reports index](../reports/index.md) generator.
