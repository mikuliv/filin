# Runbook локальной репетиции v0.3.17

## Предусловия

1. Рабочая копия чистая, HEAD и backend tree соответствуют protocol/code lock.
2. Docker доступен; образы `python:3.11-slim`, `zeek/zeek:7.0.5` и локальный `filin-rehearsal-v0317:local` совпадают с frozen digests.
3. `runtime/v0_3_17` отсутствует или пуст; protocol и pre-campaign code lock прошли validator.
4. Никакая внешняя сеть, published port, backend endpoint или реальные данные не используются.

Запуск выполняется единственной командой `python -m ml.experiments.v0_3_17.run_campaign --start`. Runner fail-closed отклоняет изменённый protocol, source file или image digest. Три runs занимают не менее четырёх фактических часов; ускорение времени не поддерживается.

Во время выполнения проверяются commentary/status file, container health, capture receipts, receiver progress, backlog и resource cadence. Raw runtime не добавляется в Git. Planned maintenance выполняется только по frozen offsets. Нештатная ошибка не исправляется на работающей кампании: campaign сохраняется и инвалидируется согласно protocol.

После completion запускаются finalizer, strict bundle validator, behavioral tests, semantic documentation validator, artifact exclusion и compileall. Только санитарные `ml/reports/v0_3_17` добавляются принудительно, поскольку общий reports namespace игнорируется.

