# Collectors

`collectors/shadow` реализует локальный passive contract `shadow_event_v1`: deterministic event generation, schema/privacy validation, bounded queue, checkpoint, checksum spool, retry и mock sinks. Внешние и production connections отсутствуют; события не имеют action authority.
