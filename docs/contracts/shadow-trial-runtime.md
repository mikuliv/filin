# Runtime-контракт локального shadow trial

Контракт определяет последовательную обработку закрытых causal windows без production-соединения. Источником телеметрии остаётся неизменный `shadow_event_v1` версии v0.3.14.

Для каждого scored window coordinator фиксирует SHA-256 PCAP, результат Zeek, immutable row ID, 51-feature row, causal order, pseudonymous activity key, frozen prediction, последнее event hash, delivery acknowledgement и atomic checkpoint. Labels в checkpoint отсутствуют.

Delivery имеет семантику at-least-once. Sink обязан дедуплицировать `idempotency_key`; exactly-once не заявляется. Queue и spool ограничены, alert/review имеют приоритет, каждый drop учитывается. Transport fault не вправе изменять prediction, state machine, causal order или thresholds.

Runtime-контракт запрещает внешние URL, production credentials, backend writes, host network, firewall changes и automatic enforcement. Все события проходят JSON Schema, privacy и data-minimization проверки.
