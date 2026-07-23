# Архитектура контролируемой локальной репетиции v0.3.17

Архитектура предназначена только для технической локальной репетиции на новых синтетических данных. Она не является реальным shadow mode, backend, SIEM, production-системой или внешней validation.

## Компоненты и границы доверия

`traffic-source` создаёт новые секундные PCAP-сегменты с заданным числом независимых синтетических окон. Host-side orchestration закрывает сегмент до обработки, строит 51 causal feature неизменного `network_features_v2`, выполняет единственный вызов frozen candidate для каждого окна и передаёт schema-valid `shadow_event_v2` в append-only sensor input.

`sensor-runtime` читает только завершённые JSONL-записи, хранит byte-offset checkpoint на выделенном volume и передаёт batches до 50 событий через TLS 1.3/mTLS. Checkpoint обновляется только после durable connector ACK.

`staging-connector` валидирует неизменные ingress/event contracts, выполняет SQLite WAL `FULL` commit до ACK и доставляет batches в `reference-receiver`. Bounded queue содержит до 200 batches; durable pending pump восстанавливает незавершённые записи после restart и исключает повторный inference.

В итоговой protocol revision 5 обе mTLS/TLS 1.3 границы повторно используют последовательные HTTP/1.1 соединения с переподключением после ошибки. Pending pump обращается к durable journal через индекс `(delivery_status, journal_durable_ns, event_id)`. Санитарные observability trace connector и receiver записываются в отдельные локальные SQLite WAL-файлы; они не участвуют в contractual commit или ACK. Основные journal, checkpoint и receiver storage сохраняют прежние схемы и `FULL` durability. Перед offline snapshot выполняется явный WAL checkpoint всех четырёх локальных баз.

Итоговая revision 6 закрепляет физическую независимость runs: общий campaign-каталог содержит только входной append-only поток, control и сертификаты, а каждый run монтирует собственный `<run_id>/volumes` для sensor checkpoint, connector journal и receiver storage. После завершения run его volumes больше не подключаются к последующим runs; offline snapshots остаются внутри корня соответствующего run.

`reference-receiver` валидирует immutable batch contract и registry commitment, выполняет durable SQLite transaction, обеспечивает idempotency и возвращает ACK только после commit.

`operator-view` подключает receiver volume только read-only, открывает SQLite через `mode=ro`, публикует только `operator_projection_v1`, поддерживает `GET`/`HEAD` и возвращает `405 read_only` для любых write methods. Writable database, receiver write credentials и action controls отсутствуют.

## Сети

Используются ровно три Docker network с `internal: true`:

- `filin_sensor_connector_internal`: traffic-source, sensor-runtime, staging-connector;
- `filin_connector_receiver_internal`: staging-connector, reference-receiver;
- `filin_receiver_operator_internal`: reference-receiver, operator-view.

Published ports, host network, внешние routes, внешняя DNS и backend route отсутствуют. Operator view не имеет пути к sensor или connector.

## Hardening и хранилища

Все контейнеры запускаются как UID/GID `65532`, с read-only root filesystem, `no-new-privileges`, `cap_drop: ALL`, без privileged mode, Docker socket и host filesystem. Writable области ограничены отдельными runtime bind/volumes и `/tmp` tmpfs. Каждый компонент имеет memory/CPU/PID limits, frozen `restart: no` и healthcheck. Синтетические private keys находятся только в gitignored runtime и имеют требуемый режим `0600` на поддерживающей его файловой системе.

Raw PCAP, features, predictions, events, journals, databases, snapshots, resource и latency traces не входят в Git. В evidence bundle допускаются только санитарные aggregates, manifests, hashes и причинно связанные отчёты.
# Уточнение границы runs в revision 7

До запуска нового контейнера источника оркестратор удаляет общий устаревший
`control.json` и marker предыдущего завершения. Новый control становится видимым
только после готовности нового стека с отдельным `<run_id>/volumes`. Это не даёт
источнику повторно выполнить расписание предыдущего run на переходной границе.
# Durable storage и maintenance в revision 8

Sensor, connector и receiver каждого run используют отдельные локальные Docker
named volumes. Они не переиспользуются между runs. После reconciliation
оркестратор выполняет WAL checkpoint и копирует main/trace databases в
`<run_id>/offline_storage`, после чего следующий run получает новые volumes.

Synthetic certificate files заменяются через временный файл и атомарный rename.
Перезапуск выполняется как ограниченный `stop`, затем `up --no-deps`, после чего
оркестратор ждёт running/healthy состояния всех затронутых компонентов.
