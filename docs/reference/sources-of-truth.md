# Источники истины

## Иерархия

1. **Статус основной линии:** `docs/status/project-status.yaml`.
2. **Статус лабораторной линии:** `docs/status/v0_4_track.yaml`.
3. **Идентичность кандидата:** `collectors/shadow/contracts/candidate_registry_v1.json`
   и `ml/artifacts/v0_3_15_4/candidate_manifest.json`.
4. **Результат этапа:** frozen protocol, policy result, bundle manifest, detached SHA,
   claim-evidence ledger и итоговый report.
5. **Форма данных:** JSON Schema, YAML contract, Pydantic contract или versioned API contract.
6. **Реализованное поведение:** code, tests, contracts и policy соответствующего этапа.
7. **Документация:** объясняет перечисленные источники, но не расширяет capability.

## Разрешение противоречий

Machine-readable status имеет приоритет над README. Policy result имеет приоритет
над summary. Manifest определяет состав bundle, а detached SHA — identity manifest.
Code не может задним числом изменить исторический результат: для нового поведения
нужен новый stage и новый evidence.

## Human-readable страницы

[Текущий статус](../status/current-status.md) сводит две линии, а
[подтверждённые возможности](../status/confirmed-capabilities.md) связывают capability
с evidence. Они должны проходить строгую consistency validation.
