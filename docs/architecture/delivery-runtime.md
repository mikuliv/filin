# среда выполнения доставки

текущий delivery среда выполнения использует локальный staging connector и reference
receiver. Доставка имеет at-least-once semantics, idempotency и ACK после
durable Коммит. Reference receiver предназначен для проверки protocol и не
является промышленная серверная часть.

Validated behavior включает retry/restart handling, bounded backlog, final
drain, source/connector/receiver reconciliation и timing traces в лабораторных
испытаниях.

Raw databases, WAL, journals, certificates и timing traces являются
только в среде выполнения artifacts.
