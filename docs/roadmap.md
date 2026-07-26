# Roadmap

Roadmap описывает разрешённые направления, но не обещает сроки и не расширяет
readiness из [`project-status.yaml`](status/project-status.yaml).

Последний завершённый этап — v0.3.18 (`completed`, `passed`).

Исторический этап v0.3.1 — базовая оценка завершён.
Этап v0.3.2 — проверка устойчивости зафиксированной модели также завершён;
полная хронология вынесена в отдельный version history.

## Current authorized next step

Разрешён только **v0.3.19 — independent external package review and trial-plan
agreement**.

В этот scope входят:

- независимая проверка protocols, contracts и commitments;
- проверка deterministic evaluator, builder и standalone verifier;
- обсуждение organizational role separation;
- согласование будущего sample plan и acceptance criteria;
- подготовка проекта data agreement.

## Not yet authorized

Не разрешены:

- real external blind trial;
- real organization trial;
- real traffic capture;
- shadow mode;
- backend integration;
- production connection;
- real notifications;
- automatic enforcement и network blocking.

Фактический trial требует отдельного решения после v0.3.19.

## Параллельная исследовательская линия v0.4.x

v0.4.0 завершён отдельно от основной линии. На синтетических лабораторных
событиях реализованы контракты, детерминированный базовый построитель и
проверка карточки инцидента. Результат не заменяет внешнюю проверку модели и
не меняет следующий основной этап v0.3.19.

Следующий допустимый шаг этой линии — только v0.4.1: расширенная
детерминированная реконструкция времени и связей наблюдаемых фактов.
Состояние хранится отдельно в [`v0_4_track.yaml`](status/v0_4_track.yaml).

Полная история результатов находится в
[version history](status/version-history.md).
