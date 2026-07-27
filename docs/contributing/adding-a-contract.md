# Добавление контракта

1. Выберите versioned schema ID и owner subsystem.
2. Определите required fields, enums, invariants и unknown-field policy.
3. Добавьте positive/negative tests и consumer validation.
4. Запретите silent migration со старой version.
5. Обновите [contracts index](../contracts/index.md) generator.
6. Если contract frozen stage, включите его SHA в manifest/ledger.

Human description не может ослаблять machine-readable schema.
