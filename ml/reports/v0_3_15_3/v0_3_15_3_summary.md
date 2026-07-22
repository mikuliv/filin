# Итог v0.3.15.3

Аналитический этап завершён: `true`. Отрицательный результат v0.3.15.2, frozen candidate и backend не изменены. Успех означает полноту анализа, а не готовность модели.

## Основной вывод

Подтверждена смешанная причина. В `auth_failures` генератор задавал ноль failed flows и создавал односторонние TCP payloads без наблюдаемого ответа аутентификации. Feature extractor дополнительно назначал application/HTTP semantics по угаданному профилю без соответствующего Zeek application log. Для `port_scan` и `web_probe` subtype был правильным во всех окнах, но пустой conformal set направил их в review.

Все 120 scheduled episodes покрыты: detected 24, review-only 36, полностью missed 0. На window-level: gate false negatives 0, subtype false negatives 42, conformal abstentions 126, state-policy suppressions 0. Frozen recall/latency/performance/privacy metrics не пересчитывались.

## Evidence и ограничения

Inventory содержит 29 доступных и 6 отсутствующих позиций. Нет raw gate/subtype scores, raw ACK, exact capture-to-sink trace и v0.3.11 feature rows. Поэтому calibration-only suppression и полный historical Zeek/version shift остаются unresolved. Feature shift report содержит 317 class-feature comparisons, прошедших заранее заданное диагностическое правило; это association, а не самостоятельное доказательство причины.

## Следующий цикл

Выбран `Track E — mixed redevelopment`. Training required: `unresolved`; technical/scenario/feature fixes: `true`; state-policy revision: `false`; calibration/conformal revision: `unresolved`. Создан только проект v0.3.15.4 со статусом `proposed_not_frozen`; он не запускался. После контролируемой разработки обязателен новый независимый v0.3.15.5 prospective holdout.

Для будущего trial реализованы additive monotonic latency traces, нормализованная CPU methodology и versioned raw synthetic ACK evidence contract с privacy scan. Instrumentation equivalence пройдена. Исторические CPU p95=103%, missing exact latency и missing raw ACK остаются непройденными.

v0.3.16, backend integration, shadow mode, production и automatic enforcement остаются заблокированными.
