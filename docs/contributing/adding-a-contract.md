# Добавление контракта

1. Выберите версионированный schema ID и owner subsystem.
2. Определите required fields, enums, invariants и unknown-field policy.
3. Добавьте positive/negative tests и потребитель проверка.
4. Запретите silent migration со старой version.
5. Обновите [contracts index](../contracts/index.md) generator.
6. Если contract Зафиксировано stage, включите его SHA в манифест/ledger.

Human description не может ослаблять машиночитаемый schema.
