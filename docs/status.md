# Текущий статус

## v0.3.6

Prospective holdout завершён с отрицательным результатом: 12 runs, 252 locked windows,
`candidate_ready_for_shadow_mode=false`, `model_refit_on_v036=false` и
`sensor_ready_for_backend_integration=false`. Shadow mode и backend integration запрещены.

> **v0.3.3 negative result:** benign recall `0.000`, false positive rate
> `1.000`, and backend ML integration is prohibited. The backend is a
> historical demonstration prototype. MITRE ATT&CK, Sigma, SIEM and analyst
> interface are not confirmed production pipelines.

| Компонент | Состояние | Последняя подтверждённая версия | Подтверждение | Ограничения |
| --- | --- | --- | --- | --- |
| Docker laboratory | Готово | v0.3 | Изолированные campaign runs | Только лабораторная сеть |
| Безопасные сценарии | Готово | v0.3 | Manifest и execution records | Не являются реальными атаками |
| Marker-aware executions | Готово | v0.3 | Start/end markers и sensor intervals | Markers не являются features |
| Passive capture | Готово | v0.3 | Capture-sidecar и PCAP audit | Нет production capture |
| PCAP storage | Готово | v0.3 | Docker-managed volume и hashes | Runtime artifacts вне Git |
| Zeek offline processing | Готово | v0.3 | PCAP→Zeek logs | Ограничено видимостью стенда |
| `network_sensor_v0_3` | Готово | v0.3 | Builders, validators, audits | Ограниченный набор сервисов |
| Independent train/test campaign | Готово | v0.3 | 6 train + 3 test runs | Лабораторный support |
| Frozen baseline evaluation | Экспериментально подтверждено | v0.3.1 | Pooled external test | Не production validation |
| Robustness evaluation | Экспериментально подтверждено | v0.3.2 | 12 external robustness-runs | Controlled shifts, identical metrics требуют осторожности |
| Environment evaluation v0.3.3 | Завершено с отрицательным результатом | v0.3.3 | Bridge validation и forensic audit | Benign recall `0.000`; backend integration запрещена |
| Backend model integration | Не начато | — | — | Нельзя считать backend готовым |
| v0.3.4 benign redesign | Реализована конфигурация research-этапа | v0.3.4 | Isolation policy, three profiles, grouped CV/freeze | Результаты кампаний являются runtime artifacts; backend не меняется |
| MITRE ATT&CK mapping | Запланировано | — | — | Будущая работа |
| Sigma generation | Запланировано | — | — | Будущая работа |
| SIEM integration | Запланировано | — | — | Будущая работа |
| Production validation | Не выполнено | — | — | Отсутствуют production data и deployment procedure |

## v0.3.7

Реализован новый изолированный training/validation cycle иерархического сенсора. Итоговый научный статус определяется frozen policy report; независимо от метрик `candidate_ready_for_shadow_mode=false` и `sensor_ready_for_backend_integration=false`. v0.3.6 остаётся неизменяемым regression benchmark для возможного v0.3.8, но в v0.3.7 не открывается для tuning.
