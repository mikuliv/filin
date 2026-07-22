# connector_ingress_v1

HTTPS/mTLS `POST /staging-connector/v1/events`, не более 50 неизменённых `shadow_event_v2`. Обязательны request/sensor ID, commitment реестра и SHA-256 канонического тела. Compression и дополнительные поля запрещены.
