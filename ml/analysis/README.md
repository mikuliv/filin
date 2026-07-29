# Анализ результатов

## Назначение и статус

Research utilities для Зафиксировано показатели, comparisons и diagnostic reports.

## Место в архитектуре

Используются после campaign и не входят в online inference path.

## Входы и выходы

Входы — версионированный predictions/labels в разрешённом область применимости; outputs — reports и показатели.

## Границы и запреты

Post-hoc analysis не может менять Зафиксировано gate или candidate identity.

## Безопасный запуск и тестирование

Используйте только stage-specific reproduction command и соответствующие tests.

## Источники истины

Зафиксировано protocol, policy result и [оценка principles](../../docs/research/evaluation-principles.md).
