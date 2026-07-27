---
doc_schema: filin_document_v2
title: Точка входа независимого эксперта
document_type: guide
audience:
  - external_reviewer
lifecycle: current
authoritative_for:
  - external_review_entrypoint
source_of_truth:
  - ml/reports/v0_3_18/external_review_package_manifest.yaml
  - docs/status/project-status.yaml
last_reviewed_stage: v0.4.4
generated: false
evidence_immutable: false
---

# Точка входа независимого эксперта

## Что подготовлено

`v0.3.18` зафиксировал package, roles, metric policy, stop conditions, transfer и
retention requirements, а также провёл синтетическую rehearsal процедуры. Это не
было внешним blind trial.

## Что разрешено на v0.3.19

Только независимая проверка полноты и непротиворечивости пакета и согласование
плана возможного будущего испытания. Фактическое испытание требует нового решения.

## Роли

Предусмотрены evaluator, data provider, label custodian, trial operator и result
approver с разделёнными обязанностями. На первом контакте передаются публичная
навигация, confirmed scope, limitations и перечень frozen artifacts — не реальные
данные, labels, secrets или доступ к инфраструктуре.

## Организационная граница

Колледж не является автоматически назначенной испытательной площадкой. Его участие,
как и участие любой организации, требует отдельного согласования правовых,
организационных и технических условий.

## Навигация

- [внешний README](../../external_review/README.md);
- [confirmed scope](../external_review/confirmed_scope.md);
- [known limitations](../external_review/known_limitations.md);
- [frozen package manifest](../../ml/reports/v0_3_18/external_review_package_manifest.yaml).

Checklist не является юридическим заключением.
