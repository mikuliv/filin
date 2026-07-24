# Эксперименты и метрики

Актуальные поздние этапы:

- [v0.3.14](experiments/v0_3_14.md) и [errata](experiments/v0_3_14_errata.md);
- [v0.3.15](experiments/v0_3_15.md);
- [v0.3.15.1](experiments/v0_3_15_1.md).
- [v0.3.15.2](experiments/v0_3_15_2.md).
- [v0.3.15.3](experiments/v0_3_15_3.md).
- [Предлагаемый v0.3.15.4](experiments/v0_3_15_4_proposed.md).

Текущий машинно-читаемый статус находится в [`status/project-status.yaml`](status/project-status.yaml).

## Shadow-readiness v0.3.14

Immutable prediction v0.3.13 преобразована в минимальные passive events без model execution. Девять replay profiles, 22 transport/storage faults и все safety gates пройдены. [Полный отчёт](experiments/v0_3_14.md).

## Prospective blind environmental holdout v0.3.13

Frozen candidate v0.3.11 проверен на 10 новых environmental runs без fit и tuning. Получены 760 captures, 700 scored windows и 200 episodes; все scientific gates пройдены. Полный результат: [v0.3.13](experiments/v0_3_13.md).

## v0.3.12.2 — causal-order corrected frozen regression

Три scientific bundles прошли window, stateful, episode, aggregate и non-inferiority gates. Causal alert windows: v0.3.9 `29/1/0`, v0.3.10 `60/0/0`; v0.3.8 также прошёл все gates. Readiness к blind holdout v0.3.13 — true, к backend и shadow mode — false.

## v0.3.6 — prospective holdout

Candidate был заморожен заранее; v0.3.6 не использовалась для model selection или threshold tuning.
Predictions были запрещены до блокировки 252 окон. Macro F1 `0.730381`, benign recall `0.625`,
FPR `0.375`, attack macro recall `0.933333`. Policy не пройдена; модель после evaluation не менялась.

Технические таблицы используют точку как десятичный разделитель и три знака после запятой.

| Версия | Вопрос | Train/test и grouping | Результат | Ограничение |
| --- | --- | --- | --- | --- |
| v0.2.4 | Переносятся ли client profiles между независимыми Docker-runs? | Независимые train/test runs; Leave-One-Train-Run-Out или фактический CV. | Client pipeline проверен технически. | Недостаточная независимая поддержка attack-классов на ранних данных. |
| v0.3.1 | Какой профиль лучше переносится на независимый test? | 6 train и 3 test sensor-runs; test не использовался для model selection. | `network_sensor_v0_3` рекомендован; feature fusion отсутствовала. | Лабораторная среда ограничена. |
| v0.3.2 | Сохраняется ли frozen baseline при controlled shifts? | 12 robustness-runs, 156 windows; только transform/predict/evaluation. | Policy пройдена. | Это не production validation. |

## v0.3.3

Frozen baseline восстановлен как deterministic source reconstruction B из шести
v0.3.1 train datasets. Bridge validation воспроизвела macro F1
`0.9181818181818181`, balanced accuracy `0.9722222222222223` и attack macro
recall `1.0`. На 204 v0.3.3 windows benign recall равен `0.000`, false positive
rate равен `1.000`; policy не пройдена. Модель не переобучалась на v0.3.3.

## v0.3.1

| Профиль | Train CV macro F1 | Pooled test macro F1 | Balanced accuracy | Attack macro recall | Support test |
| --- | ---: | ---: | ---: | ---: | ---: |
| `client_core_v0_2` | 0.989 | 0.024 | 0.167 | 0.200 | 39 |
| `network_sensor_v0_3` | 0.749 | 0.918 | 0.972 | 1.000 | 39 |

`network_sensor_v0_3` превзошёл DummyClassifier по macro F1 (`0.918` против `0.127`). Модель выбиралась только по независимым train-runs. Test- и robustness-runs не участвовали в выборе признаков, preprocessing или настройке гиперпараметров.

## v0.3.2

Зафиксированная `LogisticRegression` с `SimpleImputer(strategy="median")` и `StandardScaler` оценена на 12 robustness-runs: по три topology, background, temporal и combined. Pooled macro F1 — `0.933`, balanced accuracy — `0.979`, attack macro recall — `1.000`; support — 156 windows. Повторное обучение не выполнялось.

Метрики всех 12 runs одинаковы в сохранённом runtime report. Это наблюдение требует осторожной интерпретации и не является подтверждением широкого обобщения.

## v0.3.5

Frozen candidate v0.3.4 оценивается offline на неизменяемом v0.3.3 locked
regression benchmark. Он не участвовал в fit, выборе модели, preprocessing,
hyperparameter или threshold tuning и не является полностью слепым final test.
После него требуется отдельный blind holdout; backend integration не выполняется.

## v0.3.7 — иерархический network sensor

После отрицательного prospective holdout v0.3.6 введён новый независимый цикл: 12 training runs и 6 validation runs. Строки, labels и predictions v0.3.6 не участвуют в обучении, выборе profiles, calibration или thresholds. Model selection использует nested `StratifiedGroupKFold` 6×4 по `run_id`; единственный candidate замораживается до однократной internal validation.

Flat multiclass control сохранён только для ablation. Основной тракт разделяет suspicious gate, benign OOD guard, attack subtype model, abstention и причинный temporal accumulator. Internal validation не разрешает fit или tuning и сама по себе не подтверждает generalization.

## v0.3.8 — class-conditional evidence

Новый независимый цикл содержит 12 training runs (432 scored windows, 144 episodes) и 6 validation runs (216 scored windows, 72 episodes). До сбора validation заморожены candidate и policy; после сбора заморожен validation lock. Единственная оценка выполнена в no-fit режиме.

Выбран 51-признаковый contextual control, два calibrated HistGradientBoosting-этапа, Mondrian conformal при `alpha=0.05`, class-conditional 3-NN support с training-квантилем `0.975` и episode policy `consistent_2_of_3`. Closed-set macro F1 равен `0.990734`, FPR — `0`, conformal coverage — `0.995370`. Но attack-window alert recall `0.600000`, episode recall `0.933333` и unresolved episode rate `0.066667` нарушили frozen policy. Итог отрицательный; повторная настройка на validation запрещена.

## v0.3.9 — episode-first alert promotion

Новый изолированный цикл оставляет HGB/HGB, 51 contextual features, OOF sigmoid calibration и Mondrian `alpha=0.05` фиксированными. Selection касается только strong/weak evidence, signed accumulation и lifecycle. Episode является primary detection unit; final attack-window alert rate остаётся диагностикой, поскольку окна до причинной активации не делают episode пропущенным.

Training содержит 12 runs, 504 scored windows и 168 episodes; prospective internal validation — 6 runs, 252 windows и 84 episodes. Старые строки v0.3.6–v0.3.8 запрещены для fit, calibration, thresholds и decision selection.

Цикл завершён 15 июля 2026 года. Closed-set macro F1 составил `0.990734`,
benign recall — `1.000000`, FPR — `0.000000`; strong-evidence precision —
`1.000000`, recall — `0.600000`. Episode-first policy не решила operational
разрыв: review rate `0.416667`, attack episode recall `0.700000`, detection by
second window `0.666667`, unresolved rate `0.300000`, support top-2 rate
`0.607143`. Frozen policy не пройдена, validation не использовалась для tuning.
# v0.3.10: minimal probability-conformal promotion

После отрицательного результата v0.3.9 открыт новый изолированный training/internal-validation cycle. Он сохраняет HGB/HGB, 51 contextual feature, grouped OOF calibration и Mondrian conformal, но удаляет k-NN support, signed accumulation, decay и active lifecycle из promotion path. Support остаётся diagnostic-only.

Training содержит 12 новых runs, 216 episodes и 648 scored windows; prospective validation — 6 новых runs, 108 episodes и 324 scored windows. Главный detection gate — attack episode recall. Alert-emission window rate используется только диагностически.

Цикл завершён 16 июля 2026 года. Все 12/12 training и 6/6 validation runs
успешны; candidate заморожен до validation, а lock включил 360/360 capture
hashes до единственной prediction. Closed-set macro F1, benign recall, strong
precision/recall, attack episode recall и episode alert precision равны
`1.000000`; FPR и benign episode false-alert rate равны `0.000000`.
Attack pending rate `0.666667` и overall pending rate `0.370370` превысили
frozen limits, а training-only model-selection policy не была пройдена.
Поэтому итог отрицательный и regression v0.3.11 не разрешена.
# Технический аудит v0.3.10.1

Post-hoc аудит использует только immutable validation predictions/transitions и сохранённые grouped OOF records v0.3.10. Он не выполняет fit, calibration, tuning или новую генерацию predictions. Аудит разделяет pre-alert pending, alert emission, post-alert continuation, duplicate suppression и unresolved pending и повторяет метрики всех 101 training policies. Официальный отрицательный результат v0.3.10 не изменён.

# v0.3.11: burden-aware promotion

Новый независимый цикл завершён положительно: 12 training и 6 prospective validation runs, 792 и 396 уникальных captures соответственно. Frozen HGB/HGB candidate использует 51 причинный признак, grouped OOF calibration, Mondrian conformal и раздельные pre-alert/post-alert состояния. Все scientific и integrity policies пройдены; следующий разрешённый этап — v0.3.12 frozen regression. Подробный протокол: [эксперимент v0.3.11](experiments/v0_3_11.md).
# Frozen multi-benchmark regression v0.3.12

Этап v0.3.12 завершён без fit и tuning. Из пяти зарегистрированных benchmark core-evaluable оказались только v0.3.9 и v0.3.10; v0.3.6/v0.3.7 не имеют frozen 51-feature table, а v0.3.8 имеет count mismatch 216/252. На двух допустимых наборах macro F1 равна `0.990734` и `1.0`, но evaluation coverage и detection-by-second-window gate не пройдены. Подробности: [отчёт v0.3.12](experiments/v0_3_12.md).

# Технический аудит v0.3.12.1

Post-hoc аудит отделил frozen record-order latency от causal alert emission, объяснил 216/252 для v0.3.8 и классифицировал восстановимость v0.3.6/v0.3.7. [Протокол и выводы](experiments/v0_3_12_1.md) не меняют научный результат v0.3.12.

# v0.3.15

[Local controlled passive shadow trial](experiments/v0_3_15.md) выполнил 10 последовательных sessions и подтвердил непрерывную обработку 1520 captures, 1440 online predictions, passive delivery и restart recovery без production-интеграции.


## v0.3.15.5

Независимый controlled synthetic holdout завершён: scientific gates пройдены, runtime contract gate не пройден, candidate не promoted.

## v0.3.15.5.1

[Candidate-compatible runtime recovery trial](experiments/v0_3_15_5_1.md) сохранил отрицательный overall result v0.3.15.5, создал `shadow_event_v2` и frozen registry, затем провёл 12 новых label-free runtime-сессий. Reconciliation 2 280/2 280 и faults 12/12 пройдены; candidate promoted только для допуска к локальному staging-only v0.3.16.

## v0.3.16

[Isolated staging connector and reference receiver](experiments/v0_3_16.md) завершил revision 2 на 12 новых сессиях. 2 280/2 280 событий прошли durable connector и отдельный reference receiver, faults 24/24 и все 59 gates пройдены. Разрешена только подготовка локального v0.3.17; shadow mode, backend и production запрещены.

## v0.3.17

[Длительная controlled local rehearsal](experiments/v0_3_17.md) завершила revision 8 тремя независимыми запусками общей фактической длительностью `14400.000` секунды. Захвачено `201600` закрытых синтетических окон, source/connector/receiver согласовали `201420` canonical events, итоговый backlog равен нулю. Общий результат отрицательный: historical-anchor, clock/latency, performance и corruption/bundle gates не пройдены. Разрешён только corrective v0.3.17.1; v0.3.18, shadow mode, backend и production запрещены.
