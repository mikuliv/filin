# Контракт `rehearsal_observability_v1`

Контракт описывает очищенные образцы использования ресурсов и состояния здоровья длительной локальной репетиции. Авторитетная схема JSON находится в `rehearsal/contracts/rehearsal_observability_v1.schema.json`. Частота выборки — не реже одного раза в 10 секунд.

Разрешены component/run identity, UTC и monotonic timestamps, health/readiness, CPU, normalized CPU, RSS/VMS, file descriptor/thread/process counts, bounded queue/backlog, journal/WAL/storage sizes, TLS connection/reconnect counters, batch size, retry и error counters.

Запрещены полезная нагрузка события, вектор признаков, метка, необработанные сетевые идентификаторы, учётные данные, закрытые ключи, абсолютные пути и URL промышленной среды. Исходные временные ряды остаются в `runtime/v0_3_17`; в Git включаются только агрегаты, процентили, тенденции и манифесты SHA-256.

