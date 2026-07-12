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
