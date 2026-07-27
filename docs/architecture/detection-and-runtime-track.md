# Основная линия обнаружения и runtime

## Входы

Контролируемые PCAP и журналы Zeek, соответствующие методологии конкретной
кампании. Произвольный production capture не является разрешённым входом.

## Обработка

`collectors/` нормализуют наблюдения, `ml/features/` применяет
`network_features_v2`, а candidate registry разрешает только зафиксированный
кандидат `v03154:65a3dd912d845bc1`. Episode policy допускает отказ от определённого
класса. `shadow_event_v2` переносит решение в пассивный runtime contract.

## Доставка

`staging/` и `rehearsal/` подтверждают только изолированный локальный transport.
Эталонный receiver не является production backend. External integration остаётся
запрещённой.

## Текущая граница

Завершён `v0.3.18`; следующий `v0.3.19` ограничен review frozen package и
согласованием trial plan. Полная история находится в
[основной линии](../status/mainline-history.md).
