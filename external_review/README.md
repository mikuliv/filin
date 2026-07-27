# Внешняя проверка: современная точка входа

## Статус

`v0.3.18` подготовил frozen package и синтетически отрепетировал procedure. Реальное
внешнее испытание не проводилось. Следующий допустимый `v0.3.19` ограничен независимым
review пакета и согласованием trial plan.

## Что находится в каталоге

`contracts/` содержит machine-readable schemas ролей, commitments, manifests и
results. Они не разрешают запуск trial автоматически.

## Frozen человекочитаемый пакет

Files в `docs/external_review/` входят в package manifest v0.3.18 и сохраняются
неизменными. Их текущая навигация: [README пакета](../docs/external_review/README.md).

## Роли

Data provider, label custodian, evaluator, trial operator и result approver имеют
разделённые обязанности. На первом контакте передаются package navigation, confirmed
scope, limitations и artifact list — не real data, labels, secrets или infrastructure access.

## Организационная граница

Колледж не является назначенной испытательной площадкой. Любая площадка, передача
данных и фактический trial требуют отдельного решения. Checklists не являются
юридическим заключением.

## Источники истины

- [точка входа независимого эксперта](../docs/getting-started/external-review-entrypoint.md);
- [package manifest](../ml/reports/v0_3_18/external_review_package_manifest.yaml);
- [current status](../docs/status/current-status.md);
- [contract index](../docs/contracts/index.md).
