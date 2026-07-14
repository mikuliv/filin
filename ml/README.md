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
