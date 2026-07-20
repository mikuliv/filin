# Passive event contract `shadow_event_v1`

Контракт описывает только локальную passive telemetry. Каждое событие имеет `action_authority="none"` и `enforcement_allowed=false`; оно не разрешает блокировку, remediation или изменение доступа.

Поддерживаются `sensor_health`, `decision_observation`, `alert_emitted`, `review_required`, `alert_continuation`, `delivery_status` и `drop_summary`. Идентификаторы детерминированы, delivery имеет семантику at-least-once, а sink обеспечивает idempotent dedup. Exactly-once не заявляется.

Идентификаторы run и activity являются SHA-256 pseudonyms. Это псевдонимизация, а не доказательство анонимности. Raw PCAP, payload, features, labels, credentials, IP/MAC, hostname и filesystem paths запрещены.

Hash chain предоставляет tamper evidence внутри одного activity key, но не является аутентификацией отправителя. Будущий transport обязан отдельно обеспечить authentication и encryption.
