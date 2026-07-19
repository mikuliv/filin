# Производительность исследовательского контура

## Профиль v0.3.13

Сбор ограничен тремя Docker workers, Zeek — четырьмя slots, feature/metrics/bootstrap — шестью workers. Frozen inference выполнен на CPU и уложился в лимит 120 секунд; GPU не применялся.

## v0.3.12.2

Профиль фиксирует один процесс inference и детерминированную causal evaluation; GPU не применяется. Bootstrap использует 5000 run-level resamples с seed 42. Фактические wall-time, CPU и peak RSS сохраняются в runtime-отчётах этапа.

## Базовая линия v0.3.10

Технический аудит v0.3.10.1 не повторял обучение. Для одного компьютера с Ryzen 5 5600X (6 ядер/12 потоков), 64 ГБ RAM и RTX 5060 Ti сохранена операторская базовая линия: полный этап занял приблизительно 5 часов 5 минут, selection — более 66 минут. Наблюдавшиеся 14 745 секунд CPU на 3 960 секунд wall time соответствуют примерно 3,72 занятым логическим потокам, или 31% от 12; peak RSS оценивался примерно в 782 MiB.

## Причина и безопасная параллельность

Основной инженерный резерв находился в последовательной оценке 101 независимой decision policy. `ml/performance/parallel_policy_evaluator.py` загружает неизменные grouped OOF и frozen calibrators один раз на процесс, не вызывает fit/predict generation и распределяет только причинный state-machine evaluation. Внутри worker заданы `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1` и `NUMEXPR_NUM_THREADS=1`.

Профили 1/3/6/8 workers измеряются на полном наборе. Результат допускается к использованию только после exact-equivalence с workers=1, проверки input/source hashes и canonical ordering. Atomic checkpoint содержит completed marker и input hash; partial или устаревший checkpoint не принимается. Свободная RAM должна оставаться не ниже 8 ГБ, вычисления — ниже 48 ГБ, рост swap более 1 ГБ останавливает benchmark.

## GPU

RTX 5060 Ti не ускоряет frozen путь на scikit-learn HistGradientBoosting, NumPy и Python state machine: в нём нет CUDA backend. Замена estimator или вычислительного стека изменит научный метод и требует отдельного заранее frozen этапа.

## Будущие этапы

Для collection базовый Docker profile — 3 workers, aggressive preflight — 4, Zeek — 4–6. Для model fitting нельзя допускать nested oversubscription; профили `3 processes × 4 OpenMP threads` и `6 × 2` можно сравнивать только в новом preflight. Долгие операции должны показывать task/fold/candidate progress, ETA, worker count, CPU, RAM и checkpoint count.

## Профиль v0.3.11

HGB profiles A (3 процесса × 4 OpenMP) и B (6 × 2) дали канонически одинаковые probabilities; выбран профиль B. Policy evaluator при 1 и 8 workers также дал точное совпадение, но короткий environment check ускорился только в 1,23× из-за стоимости запуска процессов. CPU average и median не достигли инженерных целей; дальнейшее ускорение должно использовать persistent pools и shared read-only arrays без изменения frozen вычислений. Validation после Docker race была безопасно продолжена с одним Docker worker; Zeek оставался ограничен четырьмя workers.
# Predict-only профиль v0.3.12

Label-blind preflight сравнил A (1×6), B (3×2) и C (5×1); вероятности эквивалентны с tolerance `1e-12`. Выбран B, поскольку его время отличается от C менее чем на 5%, а процессов меньше. Полный stage занял `13.032655` s, prediction `0.343479` s, metrics `0.101413` s, bootstrap `0.596444` s. CPU utilization ниже engineering targets из-за малого объёма двух совместимых наборов; научное решение от этого не зависит.

# Read-only профиль v0.3.12.1

Профили A (1×1), B (3×1) и C (6×1) дают канонически эквивалентный результат. Если ускорение меньше 10%, выбирается serial A. GPU не применяется; thread limits равны одному потоку на worker, oversubscription отсутствует.
