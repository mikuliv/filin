# Анализ результатов

## Назначение и статус

Research utilities для frozen metrics, comparisons и diagnostic reports.

## Место в архитектуре

Используются после campaign и не входят в online inference path.

## Входы и выходы

Входы — versioned predictions/labels в разрешённом scope; outputs — reports и metrics.

## Границы и запреты

Post-hoc analysis не может менять frozen gate или candidate identity.

## Безопасный запуск и тестирование

Используйте только stage-specific reproduction command и соответствующие tests.

## Источники истины

Frozen protocol, policy result и [evaluation principles](../../docs/research/evaluation-principles.md).
