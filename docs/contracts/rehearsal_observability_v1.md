# Контракт `rehearsal_observability_v1`

Контракт описывает санитарные resource/health samples длительной локальной репетиции. Авторитетная JSON Schema находится в `rehearsal/contracts/rehearsal_observability_v1.schema.json`. Sampling cadence — не реже одного раза в 10 секунд.

Разрешены component/run identity, UTC и monotonic timestamps, health/readiness, CPU, normalized CPU, RSS/VMS, file descriptor/thread/process counts, bounded queue/backlog, journal/WAL/storage sizes, TLS connection/reconnect counters, batch size, retry и error counters.

Запрещены event payload, feature vector, label, raw network identifiers, credentials, private keys, absolute paths и production URLs. Raw time series остаются в `runtime/v0_3_17`; в Git включаются только aggregates, percentiles, trends и SHA-256 manifests.

