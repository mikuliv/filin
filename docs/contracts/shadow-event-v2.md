# Контракт shadow_event_v2

`shadow_event_v2` — candidate-aware структурный контракт локального passive runtime v0.3.15.5.1. Он не заменяет и не изменяет historical `shadow_event_v1`.

JSON Schema проверяет структуру, тип события, идентификаторы, причинный порядок, ссылки на prediction и runtime, а также минимальный payload. Авторизация кандидата выполняется отдельно по frozen `candidate_registry_v1` и его canonical commitment. Campaign allowlist допускает только `v03154:65a3dd912d845bc1`; silent migration между v1 и v2 запрещена.

Контракт не разрешает raw feature vectors, labels, IP/MAC/hostname, packet payload, credentials или абсолютные локальные пути. Все события пассивны и не имеют полномочий выполнять сетевые блокировки или автоматические действия.
