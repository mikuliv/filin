# Политика приёма данных

Подтверждён только PCAP input. Dataset обязан иметь pseudonymous owner и
environment identity, legal-basis placeholder, capture period, provenance,
episode grouping, label origin, privacy/credential/malware checks, encryption,
retention/deletion и publication restrictions.

`frozen_external_evaluation`, `authorized_development` и
`synthetic_protocol_rehearsal` взаимно исключаются. Разделение выполняется по
episodes, времени, nodes, environments, organizations и capture origins.
Случайное деление feature rows не доказывает независимость.
