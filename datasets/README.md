# Datasets

## Назначение

Правила происхождения, описания и controlled references для исследовательских наборов.

## Статус

`current reference`; raw sensitive data не является частью Git repository.

## Место в архитектуре

Dataset metadata поддерживает experiment protocols и feature generation основной линии.

## Основные файлы

Описания sources, splits, labels и provenance; точный состав определяется stage protocol.

## Разрешённые входы и выходы

Только synthetic/controlled inputs с documented provenance. Output — metadata и
локальные runtime artifacts, разрешённые protocol.

## Границы и запреты

Запрещены personal data, secrets, неизвестные licenses и коммит raw captures.

## Безопасный запуск и тестирование

Используйте tests конкретной ML campaign; отдельного production importer нет.

## Источники истины

[Data provenance](../docs/data-provenance.md) и frozen protocols соответствующего stage.
