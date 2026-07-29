# Хранилища и артефакты

## Tracked и Зафиксировано

Протоколы находятся в `ml/protocols/` и `incident_reconstruction/protocols/`.
Итоговые bundles и policy results находятся в `ml/reports/`. Candidate артефакт
и манифест — в `ml/artifacts/v0_3_15_4/`. Их byte identity фиксируют manifests,
утверждение ledgers и detached SHA.

## только в среде выполнения

`runtime/` хранит локальные базы, логи, временные exports и результаты проверок.
Эти файлы воспроизводимы или операционны и не становятся подтверждающие материалы без отдельной
процедуры фиксации.

## Документационный слой

`docs/` содержит современную навигацию и человекочитаемый summaries. Документация
не расширяет capability относительно code, contracts и policies. Protected set
публикуется в [audit реестр](../audit/protected_documentation_v2.json).

## Срок хранения

Правила external package определяются его Зафиксировано документами. Локальный operator
изменяемый слой удаляется только осознанно; его retention не меняет source подтверждающие материалы.
