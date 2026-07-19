# ML-подсистема

## Frozen prospective evaluation v0.3.6

`experiments/v0_3_6/` реализует protocol freeze, holdout lock и единственный predict. Policy не
пройдена; `.fit()`, calibration, threshold tuning и feature selection не выполнялись.

## Назначение

Построение проверяемых feature datasets, внешняя оценка и диагностические analyses лабораторного сетевого сенсора.

## Что реализовано

`features/` содержит profiles, builders и validators; `analysis/` — audits; `experiments/` — v0.3.1 baseline и v0.3.2 frozen robustness evaluation. `training/` содержит загрузчики и контроль разделения данных.

## Входные данные и выходные данные

Входом sensor pipeline являются correlated Zeek observations. Datasets, reports и model artifacts являются runtime artifacts и не коммитятся.

## Запуск

Для быстрой проверки: `python -m unittest discover -s ml/tests -p "test_*.py"`.

## Проверки

Model selection, external evaluation и robustness evaluation разделены. В v0.3.2 запрещено `.fit()` на robustness data.
v0.3.4 добавляет fixed `network_sensor_v0_3_control`, rates и hybrid profiles.
Selection использует только training-runs; internal validation доступна только
после candidate freeze. Данные v0.3.3 заблокированы.

## Ограничения

ML-результаты относятся к controlled laboratory data; backend model integration не начата.

## Связанные документы

[Эксперименты](../docs/experiments.md), [datasets](../datasets/README.md), [ограничения](../docs/limitations.md).

## network_sensor_v0_5

Профили: control 16, temporal 41 и contextual 51 features. Иерархический candidate состоит из binary gate, group-aware sigmoid calibrators, benign-only OOD guard, subtype classifier и causal temporal evidence. Nested grouped CV и все параметры выбираются только на training OOF; internal validation работает в no-fit режиме. Runtime models, predictions и reports не коммитятся.

## network_sensor_v0_6 class-conditional evidence

v0.3.8 добавляет 60-признаковый audited evidence profile, Mondrian conformal prediction, robust-scaled class-conditional kNN support и episode-level evidence. Nested grouped selection выбрал 51-признаковый contextual control. Замороженные source manifests коммитятся; model artifacts, datasets, predictions и reports остаются runtime artifacts вне Git. Frozen policy не пройдена.

## network_sensor_v0_7 episode-first

v0.3.9 фиксирует HGB/HGB и contextual control из 51 признака. После calibrated probabilities применяются Mondrian conformal, continuous class-support margins, strong/weak evidence, signed accumulation и alert lifecycle. Decision-layer значения никогда не входят в model X. Grouped OOF используется только на новых training runs; validation выполняется в no-fit режиме.
# Цикл v0.3.10

Minimal probability-conformal candidate сохраняет fixed HGB/HGB и 51-feature contextual profile. Group-aware calibration, conformal scores и decision thresholds строятся только на новых training grouped OOF rows. Validation работает predict-only после полного capture lock.

Frozen evaluation завершена: closed-set macro F1 `1.0`, attack episode recall
`1.0`, benign episode false-alert rate `0.0`, но pending rate `0.370370` и
attack pending rate `0.666667`. Поэтому итоговая policy отрицательна;
candidate не разрешён для regression, backend или shadow mode.
# Аудит v0.3.10.1

`audits/v0_3_10_1` содержит технический read-only аудит pending semantics и `performance` — эквивалентный параллельный evaluator. Он читает только frozen v0.3.10 и не создаёт новую модель, calibration или validation prediction.

# Цикл v0.3.11

`experiments/v0_3_11` реализует новый HGB/HGB burden-aware цикл на 51 причинном признаке. Training grouped OOF полностью отделён от prospective validation; candidate, capture manifest и validation lock создаются до единственной no-fit prediction. Frozen policy пройдена и разрешена только для v0.3.12 regression; runtime models, datasets, PCAP, predictions и отчёты остаются вне Git.
# Frozen regression v0.3.12

`experiments/v0_3_12` реализует predict-only regression кандидата v0.3.11. Compatibility audit fail-closed блокирует missing features, count mismatch, imputation и реконструкцию episode mapping. На доступных v0.3.9/v0.3.10 predictions заморожены, но общая policy не пройдена из-за coverage и episode latency gate.
