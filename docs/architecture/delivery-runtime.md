# Runtime доставки

Current delivery runtime использует локальный staging connector и reference
receiver. Доставка имеет at-least-once semantics, idempotency и ACK после
durable commit. Reference receiver предназначен для проверки protocol и не
является production backend.

Validated behavior включает retry/restart handling, bounded backlog, final
drain, source/connector/receiver reconciliation и timing traces в лабораторных
испытаниях.

Raw databases, WAL, journals, certificates и timing traces являются
runtime-only artifacts.
