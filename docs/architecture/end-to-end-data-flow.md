# Сквозной поток данных

## Последовательность

1. Контролируемый трафик сохраняется в PCAP.
2. Zeek создаёт журналы сетевых наблюдений.
3. `network_features_v2` формирует 51 причинно допустимый признак.
4. Frozen candidate выдаёт class scores, conformal set и episode decision.
5. `shadow_event_v2` упаковывает пассивное событие без автоматического действия.
6. Staging connector доставляет событие эталонному локальному receiver.
7. `incident_reconstruction` разрешает ссылки на подтверждающие материалы и строит факты.
8. Детерминированные правила строят temporal/structural relations и gaps.
9. Несколько гипотез получают evidential profiles без forced winner.
10. Карточка v2 объединяет представления и ограничения.
11. `lab_console` показывает read-only source и хранит ручной overlay отдельно.
12. Экспорт фиксирует решение оператора без изменения frozen bundle.

## Точки проверки

На каждой границе используются versioned contracts, schema validation, identity
anchors и manifest SHA. Наличие связи между объектами означает только проверяемое
отношение, определённое контрактом.

## Запрещённые обратные потоки

Operator notes не возвращаются в model input, не меняют hypotheses и не входят в
frozen evidence. Runtime output не используется для скрытого дообучения. Результат
лабораторной карточки не разрешает внешнее испытание или production integration.

См. [источники истины](../reference/sources-of-truth.md) и
[хранилища](storage-and-artifacts.md).
