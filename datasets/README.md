# Наборы данных

## Назначение

Правила происхождения, описания и controlled references для исследовательских наборов.

## Статус

`current reference`; raw sensitive data не является частью Git repository.

## Место в архитектуре

набор данных metadata поддерживает experiment protocols и признак generation основной линии.

## Основные файлы

Описания sources, splits, labels и происхождение; точный состав определяется stage protocol.

## Разрешённые входы и выходы

Только synthetic/controlled inputs с documented происхождение. Output — metadata и
локальные среда выполнения artifacts, разрешённые protocol.

## Границы и запреты

Запрещены personal data, secrets, неизвестные licenses и коммит raw captures.

## Безопасный запуск и тестирование

Используйте tests конкретной ML campaign; отдельного промышленная эксплуатация importer нет.

## Источники истины

[Data происхождение](../docs/data-provenance.md) и Зафиксировано protocols соответствующего stage.
