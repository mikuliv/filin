# Итоговый отчёт v0.3.15.5

## Итоговый статус

Этап полностью выполнен и имеет статус `completed`. Кампания валидна, абсолютные scientific gates пройдены, но общий policy result отрицательный: frozen `shadow_event_v1` разрешает только historical candidate ID и отклоняет `v03154:65a3dd912d845bc1`. Кандидат не promoted; v0.3.16 запрещён.

## Заморозка и независимость

Исходный HEAD: `6ddba2c835a53679285b6afddcef3b74cb28d430`. Protocol был закоммичен до первого capture. Созданы 20 новых сессий, 4 000 PCAP, 200 warmup и 3 800 scored окон. Пересечения session, seed, capture, PCAP hash, episode, variant и exact parameters равны нулю. Historical stages и backend tree `04218a4eb01534950efd5f7d6390f1a575cacbc8` не изменены.

## Baseline

Baseline `v0311:19176acb401be2d4` признан недопустимым comparator: historical PCAP extractor угадывает application profile по портам и форме трафика. Baseline inference count — 0; paired reports имеют статус `not_applicable_baseline_ineligible`; превосходство не заявляется.

## Blind evaluation

До открытия label vault зафиксированы 3 800 уникальных predictions. Missing, duplicate, after-unlock и repeated inference — 0. Fit, partial fit, calibration fit, conformal fit, feature selection, threshold selection и candidate replacement — 0.

## Научные результаты

Benign recall `1.000`, FPR `0.000`, attack macro recall `1.000`, attack macro F1 `1.000`. Recall каждого attack-класса равен 1.0. Attack episode recall `1.000`, episode alert precision `1.000`, benign episode FAR `0.000`, detection by second window `1.000`. Conformal coverage `1.000`, empty-set и wrong-only rate равны 0.

## Runtime и причина отказа promotion

Candidate event rejected до spool: `schema_validation_failed:'v0311:19176acb401be2d4' was expected`. Поэтому integrated runtime, fault subset, source/sink reconciliation, exact latency и performance gates не пройдены. Это не меняет scientific predictions, но блокирует promotion. Требуется новый заранее замороженный corrective stage v0.3.15.5.1 с candidate-compatible event contract и полностью новой runtime campaign; текущий holdout повторно использовать для promotion нельзя.

## Безопасность и ограничения

External network, production connection, backend write, automatic action и network block attempts — 0. Raw PCAP, Zeek logs, features, predictions, labels, events, ACK, spool и checkpoints остаются только в ignored runtime. Shadow mode, backend integration, production, automatic enforcement и external validation остаются запрещены.
