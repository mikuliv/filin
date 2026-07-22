# Контракт `operator_projection_v1`

Контракт определяет минимальную санитарную read-only проекцию durable receiver event для локальной репетиции v0.3.17. Авторитетная JSON Schema находится в `rehearsal/contracts/operator_projection_v1.schema.json`.

Разрешены ровно поля `projection_contract_version`, `projection_id`, `generated_at`, `candidate_id`, `event_contract_version`, `source_event_id`, `event_type`, `event_timestamp`, `session_pseudonym`, `activity_pseudonym`, `state`, `confidence_band`, `conformal_disposition`, `continuity`, `receiver_commit_ref`, `delivery_status`, `evidence_refs`. Session и activity представлены односторонними domain-separated pseudonyms.

Запрещены raw IP/MAC/hostname/user/email, credentials, payload, feature vector, label, scenario/class metadata, private keys, absolute paths, traces и environment values. Проекция не содержит attack intent, MITRE mapping, свободный модельный текст, рекомендации блокировки или элементы управления действием.

Источник — только durable `receiver_events` через SQLite `mode=ro`. Операции `POST`, `PUT`, `DELETE` и `PATCH` всегда отклоняются с `405`; допустимы только `GET` и `HEAD`. Operator view не владеет writable volume и не получает receiver write credentials.

