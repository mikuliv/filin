# Пакет независимой проверки

Этот раздел описывает подготовленный в v0.3.18 frozen external review package.
Этап завершён со статусом `passed`, но проверял только протокол на
синтетической репетиции. Реальные внешние данные, организация, научная
внешняя валидация и trial execution отсутствуют.

## С чего начать

1. [Подтверждённая область](confirmed_scope.md) отделяет факты от будущих
   действий.
2. [Известные ограничения](known_limitations.md) фиксируют недоказанные
   свойства.
3. [Руководство reviewer](reviewer_guide.md) задаёт порядок независимой
   проверки пакета.
4. [Архитектура](architecture.md) объясняет разделение ролей и артефактов.
5. [Политика приёма данных](data_acceptance_policy.md) и
   [условия остановки](stop_conditions.md) задают fail-closed границы.

## Руководства по ролям

- [поставщик данных](data_provider_guide.md);
- [хранитель labels](label_custodian_guide.md);
- [оператор trial](trial_operator_guide.md);
- [evaluator](evaluator_guide.md);
- [утверждающий результат](result_approver_guide.md).

## Правовые и технические требования

- [правовые требования](legal_requirements_checklist.md);
- [передача данных](data_transfer_requirements.md);
- [хранение и удаление](retention_and_deletion_requirements.md);
- [метрики](metric_policy.md);
- [воспроизводимость](reproducibility_guide.md);
- [публикация](publication_requirements.md).

Следующий допустимый этап v0.3.19 ограничен независимым review пакета и
согласованием trial plan. Он не разрешает запуск trial, получение реального
трафика, backend integration, shadow mode или production.

[Общий индекс документации](../index.md) ·
[текущий статус](../status/current-status.md) ·
[контракты](../contracts/index.md)
