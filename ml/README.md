# Подсистема ML

## Назначение

Features, candidate artifacts, inference/decision policies, experiments, protocols и reports.

## Статус

`current` для frozen candidate/runtime contracts и `historical/frozen` для завершённых stages.

## Место в архитектуре

Формирует model decision основной линии. `v0.4.x` потребляет output, но не меняет модель.

## Основные каталоги

`features/`, `training/`, `decision/`, `analysis/`, `artifacts/`, `experiments/`,
`protocols/`, `reports/`, `tests/`.

## Разрешённые входы

Versioned feature rows и datasets, разрешённые frozen protocol.

## Выходы

Candidate artifacts, predictions, policies, manifests и evidence reports.

## Границы и запреты

Запрещены silent retraining, holdout adaptation и изменение frozen reports.

## Безопасный запуск и тестирование

```powershell
python -m pytest ml/tests -q
```

## Источники истины

Candidate `v03154:65a3dd912d845bc1`,
`artifacts/v0_3_15_4/candidate_manifest.json`, [protocol index](protocols/index.md) и
[report index](reports/index.md).

## Лабораторное обучение v0.4.6

`v0.4.6` использует только проверенные synthetic feature rows и один frozen allowlist recipe. Два независимых выполнения должны подтвердить воспроизводимость до формирования proposal package. Новый model binary хранится исключительно в runtime и требует отдельного лицензионного решения; действующий candidate registry не меняется.

## Слепая проверка v0.4.7

Новый независимый synthetic control pack, labels и prediction packages существуют только в runtime. В Git входят агрегированные метрики, commitments, gates и ручное решение. Процедура пройдена, однако proposal получил `failed_validation`; действующий кандидат и registry не изменены.
