# Предлагаемый протокол v0.3.15.4

Статус: `proposed_not_frozen`. Протокол не запускался в v0.3.15.3.

Выбран Track E: раздельное исправление наблюдаемых scenario/labels, feature extraction и conformal decision layer. Решение о новом обучении остаётся unresolved до получения корректной development-выборки. v0.3.15.2 разрешён только для error analysis; он не является будущим test. v0.3.11 сохраняется baseline.

Связанные окна группируются по episode/session/scenario family. Closed holdout создаётся заново и не используется для feature/threshold selection, calibration, conformal, state-policy development или candidate selection. После разработки обязателен отдельный v0.3.15.5 prospective integrated runtime evaluation. v0.3.16 остаётся запрещённым.
