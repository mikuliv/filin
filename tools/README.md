# Инструменты проекта

## Назначение

Versioned generators, bundle validators, documentation checks и standalone verifiers.

## Статус

`current`; отдельные scripts относятся к historical frozen stages.

## Место в архитектуре

Tools воспроизводят и проверяют artifacts, но не являются runtime service.

## Основные каталоги

`audit/`, `docs/` и `lab_console/`.

## Разрешённые входы и выходы

Tracked contracts/reports и локальный runtime. Generator может менять только явно
указанные generated files.

## Границы и запреты

Нельзя rebuild frozen evidence для маскировки mismatch или обходить policy gate.

## Безопасный запуск и тестирование

Используйте только команды из [справочника](../docs/reference/command-reference.md).
Documentation v2 проверяется `python -m tools.docs.validate_documentation_v2 --strict`.

## Источники истины

CLI source, tests и frozen protocol соответствующего stage.
