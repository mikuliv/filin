# Поток данных

## Current implementation

Контролируемый input преобразуется в PCAP, затем в Zeek observations. Causal
feature builder формирует 51-признаковое окно без использования будущих событий.
Frozen candidate создаёт prediction, а stateful слой агрегирует его на уровне
episode. Результат сериализуется как versioned passive event и передаётся через
durable at-least-once transport в локальный verified sink.

## Evidence flow

Каждая стадия связывается identifiers и hashes. Source, connector и receiver
sets сверяются, а raw runtime остаётся вне Git. В Git входят только sanitized
contracts, aggregate reports, manifests и commitments.

## Не реализовано

Поток не подключён к production capture, внешней организации, SIEM/backend или
notification service.
