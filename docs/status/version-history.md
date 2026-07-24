# История версий

Источник структуры этапов — [`project-status.yaml`](project-status.yaml).
Historical results приведены без переоценки.

## v0.3.1 — Базовая оценка

**Статус:** `completed`.

**Назначение:** `evaluation`.

**Результат:** `historical`.

**Ограничение:** Контролируемая лабораторная среда.

**Следующий разрешённый шаг:** `v0.3.2`.

**Evidence:** [`docs/experiments.md`](../../docs/experiments.md).

## v0.3.2 — Проверка устойчивости

**Статус:** `completed`.

**Назначение:** `evaluation`.

**Результат:** `historical`.

**Ограничение:** Контролируемые сдвиги.

**Следующий разрешённый шаг:** `v0.3.3`.

**Evidence:** [`docs/experiments.md`](../../docs/experiments.md).

## v0.3.3 — Проверка изменённой среды

**Статус:** `completed`.

**Назначение:** `evaluation`.

**Результат:** `negative`.

**Ограничение:** Исторический отрицательный результат.

**Следующий разрешённый шаг:** `v0.3.4`.

**Evidence:** [`docs/experiments.md`](../../docs/experiments.md).

## v0.3.4 — Переработка benign-представления

**Статус:** `completed`.

**Назначение:** `training`.

**Результат:** `historical`.

**Ограничение:** Не production validation.

**Следующий разрешённый шаг:** `v0.3.5`.

**Evidence:** [`docs/v0_3_4-design.md`](../../docs/v0_3_4-design.md).

## v0.3.5 — Frozen regression evaluation

**Статус:** `completed`.

**Назначение:** `regression`.

**Результат:** `historical`.

**Ограничение:** Известный benchmark.

**Следующий разрешённый шаг:** `v0.3.6`.

**Evidence:** [`docs/experiments.md`](../../docs/experiments.md).

## v0.3.6 — Prospective holdout

**Статус:** `completed`.

**Назначение:** `holdout`.

**Результат:** `negative`.

**Ограничение:** Ограниченная среда.

**Следующий разрешённый шаг:** `v0.3.7`.

**Evidence:** [`docs/experiments.md`](../../docs/experiments.md).

## v0.3.7 — Иерархический training cycle

**Статус:** `completed`.

**Назначение:** `training`.

**Результат:** `negative`.

**Ограничение:** Internal validation.

**Следующий разрешённый шаг:** `v0.3.8`.

**Evidence:** [`docs/experiments.md`](../../docs/experiments.md).

## v0.3.8 — Class-conditional uncertainty

**Статус:** `completed`.

**Назначение:** `training`.

**Результат:** `negative`.

**Ограничение:** Некоторые gates не пройдены.

**Следующий разрешённый шаг:** `v0.3.9`.

**Evidence:** [`docs/experiments.md`](../../docs/experiments.md).

## v0.3.9 — Episode-first promotion

**Статус:** `completed`.

**Назначение:** `training`.

**Результат:** `negative`.

**Ограничение:** Episode policy не пройдена.

**Следующий разрешённый шаг:** `v0.3.10`.

**Evidence:** [`docs/experiments.md`](../../docs/experiments.md).

## v0.3.10 — Minimal probability-conformal cycle

**Статус:** `completed`.

**Назначение:** `training`.

**Результат:** `negative`.

**Ограничение:** Pending policy не пройдена.

**Следующий разрешённый шаг:** `v0.3.10.1`.

**Evidence:** [`docs/experiments.md`](../../docs/experiments.md).

## v0.3.10.1 — Аудит семантики pending

**Статус:** `completed`.

**Назначение:** `corrective`.

**Результат:** `clarification`.

**Ограничение:** Frozen result не переписан.

**Следующий разрешённый шаг:** `v0.3.11`.

**Evidence:** [`docs/experiments.md`](../../docs/experiments.md).

## v0.3.11 — Burden-aware candidate

**Статус:** `completed`.

**Назначение:** `training`.

**Результат:** `passed`.

**Ограничение:** Internal validation.

**Следующий разрешённый шаг:** `v0.3.12`.

**Evidence:** [`docs/experiments/v0_3_11.md`](../../docs/experiments/v0_3_11.md).

Policy: [`ml/reports/v0_3_11/v0_3_11_policy_result.json`](../../ml/reports/v0_3_11/v0_3_11_policy_result.json).

## v0.3.12 — Frozen multi-benchmark regression

**Статус:** `completed`.

**Назначение:** `regression`.

**Результат:** `negative`.

**Ограничение:** Coverage и episode gate.

**Следующий разрешённый шаг:** `v0.3.12.1`.

**Evidence:** [`docs/experiments/v0_3_12.md`](../../docs/experiments/v0_3_12.md).

Policy: [`ml/reports/v0_3_12/v0_3_12_policy_result.json`](../../ml/reports/v0_3_12/v0_3_12_policy_result.json).

## v0.3.12.1 — Аудит causal ordering

**Статус:** `completed`.

**Назначение:** `corrective`.

**Результат:** `clarification`.

**Ограничение:** Историческая policy сохранена.

**Следующий разрешённый шаг:** `v0.3.12.2`.

**Evidence:** [`docs/experiments/v0_3_12_1.md`](../../docs/experiments/v0_3_12_1.md).

Policy path из historical registry: `ml/reports/v0_3_12_1/v0_3_12_1_policy_result.json` (tracked artifact отсутствует).

## v0.3.12.2 — Causal-order corrected regression

**Статус:** `completed`.

**Назначение:** `regression`.

**Результат:** `passed`.

**Ограничение:** Frozen regression.

**Следующий разрешённый шаг:** `v0.3.13`.

**Evidence:** [`docs/experiments/v0_3_12_2.md`](../../docs/experiments/v0_3_12_2.md).

Policy: [`ml/reports/v0_3_12_2/v0_3_12_2_policy_result.json`](../../ml/reports/v0_3_12_2/v0_3_12_2_policy_result.json).

## v0.3.13 — Prospective environmental holdout

**Статус:** `completed`.

**Назначение:** `holdout`.

**Результат:** `passed`.

**Ограничение:** Локальная лабораторная инфраструктура.

**Следующий разрешённый шаг:** `v0.3.14`.

**Evidence:** [`docs/experiments/v0_3_13.md`](../../docs/experiments/v0_3_13.md).

Policy: [`ml/reports/v0_3_13/v0_3_13_policy_result.json`](../../ml/reports/v0_3_13/v0_3_13_policy_result.json).

## v0.3.14 — Passive component and contract audit

**Статус:** `completed_reassessed`.

**Назначение:** `runtime_audit`.

**Результат:** `limited_scope`.

**Ограничение:** Full integrated fault readiness не доказана.

**Следующий разрешённый шаг:** `v0.3.15`.

**Evidence:** [`docs/experiments/v0_3_14.md`](../../docs/experiments/v0_3_14.md).

Policy: [`ml/reports/v0_3_14/v0_3_14_policy_result.json`](../../ml/reports/v0_3_14/v0_3_14_policy_result.json).

Superseded claims: `full_integrated_fault_readiness`.

## v0.3.15 — Controlled local passive shadow trial

**Статус:** `completed_reassessed`.

**Назначение:** `runtime_trial`.

**Результат:** `scientific_result_preserved_runtime_claims_not_revalidated`.

**Ограничение:** Исторические runtime fault claims имеют недостаточную behavioral evidence.

**Следующий разрешённый шаг:** `v0.3.15.1`.

**Evidence:** [`docs/experiments/v0_3_15.md`](../../docs/experiments/v0_3_15.md).

Policy: [`ml/reports/v0_3_15/v0_3_15_policy_result.json`](../../ml/reports/v0_3_15/v0_3_15_policy_result.json).

Superseded claims: `v0316_readiness`.

## v0.3.15.1 — Passive runtime evidence hardening

**Статус:** `completed`.

**Назначение:** `corrective`.

**Результат:** `remediation_passed_readiness_blocked`.

**Ограничение:** Требуется новый frozen runtime trial; внешняя validation отсутствует.

**Следующий разрешённый шаг:** `не был установлен`.

**Evidence:** [`docs/experiments/v0_3_15_1.md`](../../docs/experiments/v0_3_15_1.md).

Policy: [`ml/reports/v0_3_15_1/v0_3_15_1_policy_result.json`](../../ml/reports/v0_3_15_1/v0_3_15_1_policy_result.json).

## v0.3.15.2 — Prospective integrated passive runtime trial

**Статус:** `completed`.

**Назначение:** `runtime_trial`.

**Результат:** `negative_scientific_and_evidence_policy`.

**Ограничение:** Scientific gates не пройдены; raw ACK privacy surface и точная capture-to-sink latency не сохранены; CPU p95 выше frozen порога.

**Следующий разрешённый шаг:** `v0.3.15.3`.

**Evidence:** [`docs/experiments/v0_3_15_2.md`](../../docs/experiments/v0_3_15_2.md).

Policy: [`ml/reports/v0_3_15_2/v0_3_15_2_policy_result.json`](../../ml/reports/v0_3_15_2/v0_3_15_2_policy_result.json).

## v0.3.15.3 — Анализ научной регрессии и проект следующего цикла

**Статус:** `completed`.

**Назначение:** `regression_analysis`.

**Результат:** `analysis_passed_mixed_cause`.

**Ограничение:** Training necessity unresolved; v0.3.11 feature rows и historical raw scores отсутствуют; v0.3.16 остаётся заблокирован.

**Следующий разрешённый шаг:** `v0.3.15.4`.

**Evidence:** [`docs/experiments/v0_3_15_3.md`](../../docs/experiments/v0_3_15_3.md).

Policy: [`ml/reports/v0_3_15_3/v0_3_15_3_policy_result.json`](../../ml/reports/v0_3_15_3/v0_3_15_3_policy_result.json).

## v0.3.15.4 — Контролируемая смешанная переработка

**Статус:** `completed`.

**Назначение:** `training`.

**Результат:** `redevelopment_passed_candidate_ready_for_v03155_only`.

**Ограничение:** Development corpus; независимый prospective holdout ещё не выполнен; v0.3.16 запрещён.

**Следующий разрешённый шаг:** `v0.3.15.5`.

**Evidence:** [`docs/experiments/v0_3_15_4.md`](../../docs/experiments/v0_3_15_4.md).

Policy: [`ml/reports/v0_3_15_4/v0_3_15_4_policy_result.json`](../../ml/reports/v0_3_15_4/v0_3_15_4_policy_result.json).

## v0.3.15.5 — Независимый перспективный сравнительный holdout

**Статус:** `completed`.

**Назначение:** `holdout`.

**Результат:** `scientific_passed_runtime_contract_failed_not_promoted`.

**Ограничение:** Historical baseline ineligible; frozen event contract отклоняет candidate v03154; v0.3.16 запрещён.

**Следующий разрешённый шаг:** `v0.3.15.5.1`.

**Evidence:** [`docs/experiments/v0_3_15_5.md`](../../docs/experiments/v0_3_15_5.md).

Policy: [`ml/reports/v0_3_15_5/v0_3_15_5_policy_result.json`](../../ml/reports/v0_3_15_5/v0_3_15_5_policy_result.json).

## v0.3.15.5.1 — Candidate-compatible event contract и prospective runtime recovery

**Статус:** `completed`.

**Назначение:** `runtime_trial`.

**Результат:** `runtime_passed_composite_promotion_passed`.

**Ограничение:** Только локальный synthetic runtime trial; shadow, backend, production и external validation запрещены.

**Следующий разрешённый шаг:** `v0.3.16`.

**Evidence:** [`docs/experiments/v0_3_15_5_1.md`](../../docs/experiments/v0_3_15_5_1.md).

Policy: [`ml/reports/v0_3_15_5_1/v0_3_15_5_1_policy_result.json`](../../ml/reports/v0_3_15_5_1/v0_3_15_5_1_policy_result.json).

## v0.3.16 — Isolated staging connector and reference receiver

**Статус:** `completed`.

**Назначение:** `staging_transport_trial`.

**Результат:** `staging_transport_passed`.

**Ограничение:** Только локальная синтетическая staging-среда; reference receiver не является backend; shadow mode, backend integration, production и external validation запрещены.

**Следующий разрешённый шаг:** `v0.3.17`.

**Evidence:** [`docs/experiments/v0_3_16.md`](../../docs/experiments/v0_3_16.md).

Policy: [`ml/reports/v0_3_16/v0_3_16_policy_result.json`](../../ml/reports/v0_3_16/v0_3_16_policy_result.json).

## v0.3.17 — Длительная контролируемая локальная репетиция

**Статус:** `completed`.

**Назначение:** `controlled_local_rehearsal`.

**Результат:** `rehearsal_completed_policy_failed`.

**Ограничение:** Четырёхчасовая локальная кампания завершена, но historical-anchor, clock-domain, healthy/nominal latency, performance и corruption/bundle gates не пройдены; допуск к v0.3.18 не выдан.

**Следующий разрешённый шаг:** `v0.3.17.1`.

**Evidence:** [`docs/experiments/v0_3_17.md`](../../docs/experiments/v0_3_17.md).

Policy: [`ml/reports/v0_3_17/v0_3_17_policy_result.json`](../../ml/reports/v0_3_17/v0_3_17_policy_result.json).

## v0.3.17.1 — Корректирующий аудит доказательств, временных трасс и производительности

**Статус:** `completed`.

**Назначение:** `corrective_audit`.

**Результат:** `corrective_audit_passed_design_review_ready`.

**Ограничение:** Разрешён только design review v0.3.18; shadow mode, backend integration, production, внешние подключения, реальные уведомления и automatic enforcement запрещены.

**Следующий разрешённый шаг:** `v0.3.18`.

**Evidence:** [`docs/experiments/v0_3_17_1.md`](../../docs/experiments/v0_3_17_1.md).

Policy: [`ml/reports/v0_3_17_1/v0_3_17_1_policy_result.json`](../../ml/reports/v0_3_17_1/v0_3_17_1_policy_result.json).

## v0.3.18 — Проектирование независимой внешней проверки и слепого испытания

**Статус:** `completed`.

**Назначение:** `external_review_design`.

**Результат:** `design_and_synthetic_rehearsal_passed`.

**Ограничение:** Реальные внешние данные и labels не использовались; scientific external validation не выполнена; разрешён только package review v0.3.19.

**Следующий разрешённый шаг:** `v0.3.19`.

**Evidence:** [`docs/experiments/v0_3_18.md`](../../docs/experiments/v0_3_18.md).

Policy: [`ml/reports/v0_3_18/v0_3_18_policy_result.json`](../../ml/reports/v0_3_18/v0_3_18_policy_result.json).

## Текущий переход

После v0.3.18 разрешён только v0.3.19 package review и согласование
trial plan. Фактический external trial не разрешён.
