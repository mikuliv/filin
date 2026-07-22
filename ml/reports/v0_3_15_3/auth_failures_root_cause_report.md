# Аудит `auth_failures`

Все 12 эпизодов (42 окна) прослежены от capture до final state. Gate относил каждое окно к attack, но subtype во всех 42 окнах выбирал `web_probe`; conformal set был пустым, поэтому итогом стал review.

Подтверждён сценарный дефект: профиль v0.3.15.2 задаёт `failed=0`, а PCAP содержит односторонние TCP-пакеты без ответа сервиса. Raw Zeek `conn.log` показывает `OTH`, нулевые response packets, отсутствие service и отсутствие `http.log`. Следовательно, факт отказа аутентификации из сетевого наблюдения не следует. Дополнительно extractor присваивает HTTP status/error признаки по эвристически угаданному профилю, а не по HTTP log; это подтверждённый feature-extraction defect.

Причина классифицирована как `mixed_cause`, confidence `confirmed`: `scenario_generation_defect` плюс `feature_extraction_defect`. Ошибка subtype наблюдается, но не доказывает model-generalization failure на корректном auth-сценарии. Counter-evidence: gate уверенно обнаруживал аномальную активность, поэтому binary gate не является механизмом пропуска. Требуется исправление сценария и extraction semantics; необходимость обучения остаётся unresolved до корректных наблюдаемых labels.
