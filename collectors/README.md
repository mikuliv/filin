# Collectors

`collectors/shadow` реализует локальный passive contract `shadow_event_v1`: deterministic event generation, schema/privacy validation, bounded queue, checkpoint, checksum spool, retry и mock sinks. Внешние и production connections отсутствуют; события не имеют action authority.

`collectors/shadow_trial` связывает этот контракт с последовательным capture/Zeek/feature/frozen-inference pipeline v0.3.15. Каждый scored window получает immutable row ID, causal state transition, passive events, sink acknowledgement и atomic checkpoint до завершения session.
