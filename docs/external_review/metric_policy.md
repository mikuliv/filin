# Практическое применение политики метрик

## Авторитетный источник

Frozen rules находятся в
[metric policy JSON](../../ml/reports/v0_3_18/metric_policy.json). Политика
complete для protocol rehearsal, но не для real trial execution.

## Обязательные outputs

- confusion matrix;
- per-class precision, recall и F1;
- macro и weighted F1;
- balanced accuracy;
- false-positive и false-negative counts;
- abstention count/rate;
- coverage и selective accuracy;
- missing, duplicate и invalid counts;
- episode-level metrics;
- uncertainty intervals;
- dataset composition.

## Порядок расчёта

1. Проверить prediction и label commitments.
2. Проверить taxonomy и completeness.
3. Зафиксировать missing/duplicate/invalid records.
4. Рассчитать row-level frozen metrics.
5. Рассчитать abstention и coverage.
6. Выполнить episode aggregation.
7. Рассчитать uncertainty intervals по frozen plan.
8. Canonically serialize machine-readable result.
9. Повторить execution для проверки детерминизма.

## Abstention и missing predictions

Abstention не считается правильным prediction. Missing prediction не
заменяется default class. Selective accuracy публикуется только вместе с
coverage, иначе результат вводит в заблуждение.

## Запрещённые post-hoc действия

Нельзя выбирать threshold, averaging, class merge или исключать samples после
reveal. Неудобный отрицательный результат сохраняется.

## Неустановленные criteria

Organization-specific false-positive/false-negative limits и minimum external
macro F1 должны быть согласованы до holdout commitment. Документ не назначает
их числовые значения.

## Ошибки расчёта

Commitment mismatch, incomplete set или nondeterminism останавливают
evaluation. Исправление evaluator или policy требует новой revision.

## Ограничение интерпретации

Metrics описывают только зафиксированный dataset и coverage. Synthetic
rehearsal v0.3.18 не является scientific evidence.

## Связанные документы

- [Руководство evaluator](evaluator_guide.md)
- [Известные ограничения](known_limitations.md)
- [Stop conditions](stop_conditions.md)
- [Result schema](../../external_review/contracts/external_evaluation_result_v1.schema.json)
- [Текущий статус](../status/current-status.md)
