# Поток данных

## текущий implementation

Контролируемый input преобразуется в PCAP, затем в Zeek observations. Causal
признак builder формирует 51-признаковое окно без использования будущих событий.
Зафиксировано candidate создаёт prediction, а stateful слой агрегирует его на уровне
episode. Результат сериализуется как версионированный passive event и передаётся через
durable at-least-once transport в локальный verified sink.

## подтверждающие материалы flow

Каждая стадия связывается identifiers и hashes. Source, connector и receiver
sets сверяются, а raw среда выполнения остаётся вне Git. В Git входят только sanitized
contracts, aggregate reports, manifests и commitments.

## Не реализовано

Поток не подключён к промышленная эксплуатация capture, внешней организации, SIEM/серверная часть или
notification service.
