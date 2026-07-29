# Обучение модели

## Назначение и статус

Исторические и controlled training utilities. Текущий candidate уже Зафиксировано.

## Место в архитектуре

Training создаёт candidate только в специально разрешённом development stage;
обычный среда выполнения и `v0.4.x` этот слой не вызывают.

## Входы и выходы

версионированный development Наборы данных → candidate artifacts и training reports.

## Границы и запреты

Hidden retraining, отложенная контрольная выборка reuse и запуск нового cycle без protocol запрещены.

## Безопасный запуск и тестирование

Нет общего quick-start training command. Используйте Зафиксировано protocol отдельного stage.

## Источники истины

[Candidate история происхождения](../../docs/research/candidate-lineage.md) и исторический experiment reports.
