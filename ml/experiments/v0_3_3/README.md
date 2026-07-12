# Филин v0.3.3 — внешняя environment evaluation

Этап использует frozen baseline `network_sensor_v0_3` только для внешнего
`predict`. Данные v0.3.3 не участвуют в обучении, выборе признаков,
preprocessing, подборе параметров или настройке порогов.

Оригинальный serialized artifact v0.3.1 не сохранился в migration-репозитории.
Для проверки v0.3.3 применяется документированная deterministic source
reconstruction из шести recovered datasets v0.3.1. Она воспроизводит
исторические pooled test metrics v0.3.1, но не объявляется криптографически
идентичной отсутствующему original artifact.

`recover_frozen_baseline.py` читает только recovered v0.3.1 train/test
datasets. `run_environment_evaluation.py` не содержит операции `fit` и
проверяет SHA-256 artifact перед prediction.
# Preserved negative environment evaluation

v0.3.3 evaluates the deterministically reconstructed v0.3.1 baseline without
fitting it on v0.3.3 data. Its benign recall is `0.000` and false positive rate
is `1.000`; this negative result is preserved. The environment data are now a
diagnostic/hard-negative development set, not future blind evaluation data.
