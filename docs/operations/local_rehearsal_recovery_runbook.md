# Recovery runbook локальной репетиции v0.3.17

## Restart и backlog

Sensor возобновляет чтение с последнего durable byte-offset. Повтор записи, ACK которой был получен до checkpoint, допускает только transport duplicate: connector idempotency не создаёт второй semantic event. Connector после старта непрерывно поднимает pending journal batches и прекращает повтор только после receiver durable ACK/checkpoint. Receiver восстанавливает SQLite WAL до приёма новых batches.

При receiver unavailability sensor outbox и connector journal остаются bounded. После восстановления сначала запускается receiver, затем connector; backlog должен полностью исчезнуть в frozen recovery interval. Повторный inference, изменение prediction, causal reorder и потеря event запрещены.

## Storage pressure

Pressure fixture создаётся только в выделенном container volume и ограничен 45 MiB при declared объёме 64 MiB. Host filesystem целенаправленно не заполняется. На critical threshold readiness должна быть false; ACK до durable commit и silent drop запрещены. Cleanup удаляет только файл `pressure.fixture`, затем проверяются SQLite integrity, event-set equality и chain roots.

## Invalidation

Ошибка protocol/code до первого event требует новой сохранённой protocol revision. Любая необходимая правка после первого event инвалидирует текущую campaign. Её runtime не переписывается; повтор получает новые session/run IDs, seeds, runtime IDs и synthetic certificates. Strict resume никогда не повторяет capture, feature extraction, inference, event generation, maintenance или certificate generation.

