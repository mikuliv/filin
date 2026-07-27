# Хранилища и артефакты

## Tracked и frozen

Протоколы находятся в `ml/protocols/` и `incident_reconstruction/protocols/`.
Итоговые bundles и policy results находятся в `ml/reports/`. Candidate artifact
и manifest — в `ml/artifacts/v0_3_15_4/`. Их byte identity фиксируют manifests,
claim ledgers и detached SHA.

## Runtime-only

`runtime/` хранит локальные базы, логи, временные exports и результаты проверок.
Эти файлы воспроизводимы или операционны и не становятся evidence без отдельной
процедуры фиксации.

## Документационный слой

`docs/` содержит современную навигацию и human-readable summaries. Документация
не расширяет capability относительно code, contracts и policies. Protected set
публикуется в [audit registry](../audit/protected_documentation_v2.json).

## Срок хранения

Правила external package определяются его frozen документами. Локальный operator
overlay удаляется только осознанно; его retention не меняет source evidence.
