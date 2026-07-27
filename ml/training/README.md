# Обучение модели

## Назначение и статус

Исторические и controlled training utilities. Текущий candidate уже frozen.

## Место в архитектуре

Training создаёт candidate только в специально разрешённом development stage;
обычный runtime и `v0.4.x` этот слой не вызывают.

## Входы и выходы

Versioned development datasets → candidate artifacts и training reports.

## Границы и запреты

Hidden retraining, holdout reuse и запуск нового cycle без protocol запрещены.

## Безопасный запуск и тестирование

Нет общего quick-start training command. Используйте frozen protocol отдельного stage.

## Источники истины

[Candidate lineage](../../docs/research/candidate-lineage.md) и historical experiment reports.
