# Runbook эталонного приёмника

Приёмник запускается только через `staging/docker-compose.v0_3_16.yml` во внутренней сети без опубликованных портов. Readiness требует доступной SQLite, registry snapshot и действующего TLS. Диагностика ограничена агрегированными count/hash/fingerprint; raw events, ACK, ключи и БД не добавляются в Git. Компонент не является backend и не разрешён для production.
