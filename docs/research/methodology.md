# Исследовательская методология

## Принципы

Каждый значимый этап начинается с versioned protocol и заранее определённых gates.
Inputs, candidate identity, split, metrics и prohibited adaptations фиксируются до
оценки. Итог сохраняется независимо от того, положительный он или отрицательный.

## Разделение development и evaluation

Training/development data не используются как независимое подтверждение. Frozen
holdout и prospective campaign запрещают скрытый выбор thresholds, features или
candidate по результату. Отсутствующие исходные данные ограничивают claim, а не
заменяются реконструкцией.

## Неопределённость

Conformal prediction, abstention и competing hypotheses сохраняют неопределённость.
Forced winner запрещён там, где evidence не различает варианты.

## Воспроизводимость

Artifacts связываются через manifests, SHA-256, semantic SHA, claim ledgers и
deterministic generators. Human-readable summary не переписывает policy result.

## Две линии

`v0.3.x` оценивает model/runtime/external procedure. `v0.4.x` оценивает лабораторную
reconstruction и operator workflow над неизменными событиями. Положительный
результат одной линии не расширяет scope другой.

См. [принципы оценки](evaluation-principles.md),
[воспроизводимость](reproducibility.md) и [источники истины](../reference/sources-of-truth.md).
