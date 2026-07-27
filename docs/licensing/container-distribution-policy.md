# Политика контейнерного распространения

- Suricata — optional third-party component, GPL-2.0-only; образ и исходники не входят в core/offline bundle.
- Elasticsearch, Kibana и Filebeat — optional laboratory references; пользователь получает их самостоятельно, они исключены из distribution.
- Zeek — сторонняя ссылка и не является собственным компонентом.
- Docker Desktop — внешний инструмент разработки, не часть дистрибутива.
- Python/nginx base images и apt packages учитываются как внешние build/runtime prerequisites; source profiles содержат лишь декларации ссылок.

Сборка offline third-party bundle запрещена до отдельной проверки лицензий, notices, исходников и условий каждого образа.

