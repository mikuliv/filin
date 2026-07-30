# Происхождение данных

## Источники

Client observations формируются traffic-client и используются только как отдельный контрольный источник. Sensor observations проходят цепочку:

```text
PCAP -> Zeek logs -> Zeek parser -> normalized sensor events -> marker-based correlation -> network_sensor_v0_3
```

События `network_sensor_v0_3` формируются только из фактически захваченного сетевого трафика. Traffic-client events используются для контрольного сравнения и не являются источником событий Zeek или сетевых признаков.

Для v0.3.15.4–v0.3.15.5 действует отдельное ограничение: PCAP содержит сетевые пакеты, но они непосредственно построены class-conditioned Scapy-шаблоном, а не захвачены при исполнении Docker traffic-client против target service. Docker в этих стадиях использован для Zeek. Поэтому подтверждена цепочка `PCAP → Zeek → признаки`, но не происхождение от реального client-to-service обмена; см. [переоценку методологии](experiments/v0_3_15_4_v0_3_15_5_methodology_reassessment.md).

## Markers и интервалы

Каждое execution получает реальные start/end HTTP markers внутри лабораторной сети. Они создают half-open sensor interval `[start, end)`. Execution markers используются только для корреляции и исключаются из модель features. Корреляция не использует label, ожидаемые признаки или готовые client features.

## Контроль происхождения

Campaign roles разделяют train, test и robustness runs. Для PCAP, Zeek logs, normalized events и Наборы данных сохраняются SHA-256. происхождение, разбиение и duplicate audits проверяют отсутствие пересечений и leakage fields. Raw IP, hostname, URI, Zeek UID, marker metadata, label и execution identifiers не являются модель features.
