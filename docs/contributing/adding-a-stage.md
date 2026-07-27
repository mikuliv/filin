---
doc_schema: filin_document_v2
title: Добавление этапа
document_type: guide
audience:
  - contributor
lifecycle: current
authoritative_for: []
source_of_truth:
  - frozen_protocol_policy
last_reviewed_stage: v0.4.4
generated: false
evidence_immutable: false
---

# Добавление этапа

1. Убедитесь, что stage разрешён machine-readable status.
2. Заморозьте protocol до реализации/evaluation.
3. Зафиксируйте identity anchors, scope, gates, stop conditions и prohibitions.
4. Выполните campaign без скрытой adaptation.
5. Создайте policy result, manifest, detached SHA, ledger и summary.
6. Добавьте protocol/report indexes.
7. Обновите status YAML только по frozen result.
8. Обновите current docs и limitations без изменения historical evidence.

`completed` и `passed` должны храниться раздельно. Documentation alone не создаёт stage.
