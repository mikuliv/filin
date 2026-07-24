# Руководство independent evaluator

## Назначение роли

Independent evaluator проверяет reveal и детерминированно рассчитывает frozen
metrics. Он не запускает inference, не выбирает thresholds и не утверждает
итог trial.

## Место роли в процессе испытания

Evaluator identity фиксируется до blind handoff. После prediction commitment
и label reveal он выполняет `reveal_verification`, `frozen_evaluation` и
создаёт machine-readable result для result bundle.

## Требования к независимости

- evaluator не участвует в candidate development;
- labels недоступны ему до prediction freeze;
- source, metric policy, taxonomy, seed и output schema committed заранее;
- calculation отделён от approval.

## Допустимое совмещение ролей

Frozen matrix не разрешает молчаливое совмещение. Технический повтор evaluator
другим actor является reproducibility check, а не совмещением ролей.

## Запрещённое совмещение ролей

Evaluator конфликтует с `project_owner`, `data_provider`, `trial_operator`,
`label_custodian` и `result_approver`.

## Входные материалы

- frozen prediction submission и commitment;
- label reveal и label commitment;
- holdout/dataset commitments;
- evaluator commitment;
- frozen metric и sample-sufficiency policies;
- class taxonomy и episode mapping;
- chronology;
- external evaluation result schema.

## Подготовка к работе

1. Создать чистую изолированную среду.
2. Проверить evaluator source hash и version.
3. Сверить metric policy hash и class taxonomy.
4. Сверить deterministic seed и output schema.
5. Отключить сеть и backend.
6. Зафиксировать входные commitments и environment metadata.

## Порядок действий

1. Провалидировать prediction commitment.
2. Пересчитать submission hash.
3. Провалидировать label commitment и reveal.
4. Проверить, что reveal следует после prediction commitment.
5. Сопоставить holdout IDs.
6. Проверить полноту ожидаемых prediction IDs.
7. Посчитать missing, duplicate и invalid predictions.
8. Не заменять missing prediction классом по умолчанию.
9. Сохранить abstentions как отдельный outcome.
10. Построить confusion matrix.
11. Рассчитать per-class precision, recall и F1.
12. Рассчитать macro и weighted F1.
13. Рассчитать balanced accuracy.
14. Рассчитать abstention count/rate и coverage.
15. Рассчитать selective accuracy.
16. Рассчитать false-positive и false-negative counts по policy.
17. Выполнить episode-level aggregation.
18. Рассчитать uncertainty intervals по frozen plan.
19. Включить dataset composition.
20. Canonically serialize result.
21. Повторить execution и сравнить результат byte-for-byte.

## Обязательные проверки

- commitments проверены до расчёта;
- taxonomy не объединялась post-reveal;
- threshold selection не выполнялся;
- неудобные samples не исключались;
- abstention не считается правильным prediction;
- coverage и selective accuracy представлены вместе;
- все counts согласованы с manifests;
- повторный запуск идентичен.

## Метрики и их интерпретация

Confusion matrix и per-class metrics показывают ошибки каждого класса.
Macro F1 одинаково учитывает классы, weighted F1 учитывает support, balanced
accuracy усредняет recall. Coverage показывает долю не-abstained результатов,
а selective accuracy относится только к покрытой части.

Ни одна метрика не заменяет другую. Frozen policy не задаёт новые
organization-specific acceptance thresholds: они должны быть согласованы до
holdout commitment.

## Создаваемые артефакты

- schema-valid external evaluation result;
- canonical result hash;
- deterministic execution log;
- evaluator role attestations;
- chronology events;
- discrepancy report при mismatch или nondeterminism.

## Передача материалов следующей роли

Reviewer получает result bundle, commitments и reproducibility evidence.
Approver получает неизменённый machine-readable result и findings reviewer.
Evaluator не пишет approval decision.

## Основания для остановки

- commitment или reveal mismatch;
- incomplete prediction set;
- chronology violation;
- evaluator source/policy mismatch;
- unsupported taxonomy или mapping;
- попытка post-hoc threshold/class/sample change;
- nondeterministic result.

## Основания для признания испытания недействительным

Early reveal, changed evaluator, prediction/label commitment mismatch,
post-hoc exclusions и unauthorized retry после reveal относятся к frozen
invalidation conditions.

## Работа с ошибками и расхождениями

Schema или completeness error фиксируется как operational finding; input не
исправляется evaluator. Если summary расходится с canonical result,
machine-readable result сохраняется, а расхождение передаётся reviewer.

## Повторный запуск и новая ревизия

Идентичный input обязан дать идентичный canonical result. Расхождение
останавливает процесс. Изменение evaluator, policy, taxonomy, seed или inputs
требует новой revision и не заменяет прежний outcome.

## Scientific и operational result

Scientific failure означает непрохождение заранее согласованных научных gates
на валидном trial. Operational failure означает невозможность корректно
завершить процедуру. Их нельзя смешивать или использовать для скрытия
negative result.

## Защита данных и конфиденциальность

Evaluator получает только необходимые frozen predictions и revealed labels.
Raw PCAP, credentials и organization identifiers не копируются без
необходимости. Logs очищаются от secrets без удаления evidence об ошибке.

## Ограничения интерпретации

Evaluator детерминированно рассчитывает показатели, но не доказывает
репрезентативность dataset. Для v0.3.18 результат относится только к synthetic
rehearsal и имеет `scientific_evidence=false`.

## Контрольный список

- [ ] evaluator commitment совпал;
- [ ] predictions и labels verified;
- [ ] chronology корректна;
- [ ] completeness counts рассчитаны;
- [ ] abstention и coverage сохранены;
- [ ] все frozen metrics рассчитаны;
- [ ] episode metrics и intervals включены;
- [ ] thresholds/samples/classes не менялись;
- [ ] повторный запуск идентичен;
- [ ] result schema и canonical hash проверены;
- [ ] result передан без approval claim.

## Связанные документы

- [Metric policy](metric_policy.md)
- [Руководство custodian](label_custodian_guide.md)
- [Руководство approver](result_approver_guide.md)
- [Metric policy JSON](../../ml/reports/v0_3_18/metric_policy.json)
- [Evaluator commitment schema](../../external_review/contracts/evaluator_commitment_v1.schema.json)
- [Result schema](../../external_review/contracts/external_evaluation_result_v1.schema.json)
