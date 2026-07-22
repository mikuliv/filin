# Архитектура staging connector v0.3.16

Три изолированных контейнера образуют цепочку `sensor-runtime → staging-connector → reference-receiver`. Sensor и receiver не состоят в общей сети. Connector — единственный участник обеих внутренних сетей. Порты на host не публикуются.

Connector подтверждает ingress только после SQLite/WAL/FULL commit, доставляет события двумя worker пакетами до 50 и фиксирует checkpoint только после строгого durable ACK. Reference receiver — отдельный эталонный компонент, не backend: он не импортирует backend, не использует его конфигурацию, БД или endpoints и не выполняет production-действий.
