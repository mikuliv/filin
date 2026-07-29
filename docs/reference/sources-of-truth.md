# Источники истины

## Иерархия

1. **Статус основной линии:** `docs/status/project-status.yaml`.
2. **Статус лабораторной линии:** `docs/status/v0_4_track.yaml`.
3. **Идентичность кандидата:** `collectors/shadow/contracts/candidate_registry_v1.json`
   и `ml/artifacts/v0_3_15_4/candidate_manifest.json`.
4. **Результат этапа:** Зафиксировано protocol, policy result, комплект манифест, detached SHA,
   утверждение-подтверждающие материалы ledger и итоговый report.
5. **Форма данных:** Файлы JSON Schema, YAML contract, Pydantic contract или версионированный API contract.
6. **Реализованное поведение:** code, tests, contracts и policy соответствующего этапа.
7. **Документация:** объясняет перечисленные источники, но не расширяет capability.

## Разрешение противоречий

машиночитаемый status имеет приоритет над README. Policy result имеет приоритет
над summary. манифест определяет состав комплект, а detached SHA — identity манифест.
Code не может задним числом изменить исторический результат: для нового поведения
нужен новый stage и новый подтверждающие материалы.

## человекочитаемый страницы

[Текущий статус](../status/current-status.md) сводит две линии, а
[подтверждённые возможности](../status/confirmed-capabilities.md) связывают capability
с подтверждающие материалы. Они должны проходить строгую consistency проверка.

## Лицензионные источники истины

Для назначения лицензии приоритет имеют `REUSE.toml` и `licensing/repository-license-manifest.json`; для границ выпуска — `distribution/profiles/*.json`; для результата проверки — `docs/licensing/license-validation-result.json`. Текстовые страницы объясняют эти источники, но не расширяют разрешённый состав.
