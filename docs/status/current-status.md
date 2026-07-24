---
status_schema: filin_current_status_v1
latest_completed_stage: v0.3.18
latest_stage_status: completed
latest_stage_result: passed
next_allowed_stage: v0.3.19
next_stage_scope: external_package_review_only
external_trial_execution_allowed: false
shadow_mode_allowed: false
backend_integration_allowed: false
production_ready: false
automatic_enforcement_ready: false
real_external_data_used_in_v0_3_18: false
synthetic_rehearsal_scientific_evidence: false
---

# Текущий статус

Machine-readable источник — [`project-status.yaml`](project-status.yaml).

Последний завершённый этап — v0.3.18, статус `completed / passed`. Этап
подготовил external review package и проверил protocol на synthetic fixtures.
Это не научная external validation.

## Candidate

Current frozen candidate: `v03154:65a3dd912d845bc1`. Registry и manifest
доступны в `collectors/shadow/contracts` и `ml/artifacts/v0_3_15_4`.

## Подтверждённый scope

Подтверждены laboratory causal extraction, frozen inference, stateful episode
processing, passive event contracts, local durable delivery, длительная local
campaign, corrective timing validation и synthetic external-review rehearsal.

## Readiness

Разрешён только v0.3.19 — независимый review external package и согласование
trial plan. External trial execution, shadow mode, backend integration,
production и automatic enforcement запрещены.

## Evidence

- [Summary v0.3.18](../../ml/reports/v0_3_18/v0_3_18_summary.md)
- [Policy v0.3.18](../../ml/reports/v0_3_18/v0_3_18_policy_result.json)
- [Описание этапа](../experiments/v0_3_18.md)
- [Confirmed capabilities](confirmed-capabilities.md)
- [Prohibited capabilities](prohibited-capabilities.md)
