# История основной линии v0.3.x

| Период | Этапы | Результат | Ключевое ограничение |
|---|---|---|---|
| Базовые эксперименты | `v0.3.1–v0.3.7` | сформированы baseline, robustness и ранние training cycles | неоднородные/отрицательные результаты, исторические методики |
| Неопределённость и ordering | `v0.3.8–v0.3.12.2` | class-conditional uncertainty, episode policy, causal-order correction | internal/frozen benchmarks |
| Prospective environment | `v0.3.13–v0.3.15.3` | holdout, passive runtime и corrective evidence audits | runtime/scientific claims неоднократно ограничивались |
| Текущий candidate | `v0.3.15.4–v0.3.15.5.1` | создан `v03154`, frozen-метрики синтетического корпуса и compatible runtime воспроизводимы | holdout использует то же generator family; внешняя validation отсутствует |
| Transport/rehearsal | `v0.3.16–v0.3.17.1` | staging transport, длительная rehearsal и corrective audit | только локальная synthetic среда |
| External procedure | `v0.3.18` | frozen package и synthetic rehearsal процедуры | trial не проводился |

Следующий разрешённый этап — `v0.3.19` package review и trial-plan agreement.
Stage-specific reports доступны через [индекс](../reports/index.md). Актуальное ограничение научного вывода приведено в [переоценке v0.3.15.4–v0.3.15.5](../experiments/v0_3_15_4_v0_3_15_5_methodology_reassessment.md).
