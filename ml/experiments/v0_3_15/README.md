# Филин v0.3.15

Этап выполняет локальный controlled passive shadow trial frozen candidate v0.3.11. Конвейер обрабатывает каждое закрытое окно до завершения session, использует неизменный `shadow_event_v1` и допускает только локальный mock sink.

Основной запуск:

```powershell
python ml/experiments/v0_3_15/run_v0_3_15.py --protocol ml/experiments/v0_3_15/protocol.yaml --campaign ml/experiments/v0_3_15/campaign.yaml --candidate-manifest ml/experiments/v0_3_11/frozen_candidate_manifest.yaml --event-contract collectors/shadow/contracts/shadow_event_v1.schema.json --strict --resource-monitor
```

Runtime PCAP, Zeek logs, features, labels, predictions, events, spool, checkpoints и resource traces не входят в Git.
