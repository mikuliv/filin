# Технические требования к публикации

## Граница применения

Publication plan согласуется до trial. Документ не предоставляет право
публикации и должен быть проверен компетентным юристом.

## Что согласовать заранее

- право публиковать protocol и methodology;
- допустимые aggregate metrics;
- публикацию negative/invalidated outcomes;
- обязательные limitations и dataset scope;
- review/approval process;
- anonymization и organization disclosure;
- срок embargo, если он законно требуется.

## Что не публикуется по умолчанию

- raw PCAP и payload;
- IP и organization identifiers;
- labels и episode mapping;
- credentials, keys и secrets;
- confidential manifests;
- runtime-only package.

## Требования к результату

Публикация указывает usage mode, candidate identity, dataset scope, coverage,
abstention, limitations и outcome. Selective accuracy не публикуется без
coverage. Package integrity не называется scientific validation.

## Отрицательные результаты

Negative, stopped и invalidated outcomes не удаляются ради narrative.
Исправленная revision публикуется отдельно и не заменяет исходный result.

## Контроль перед выпуском

- [ ] права подтверждены;
- [ ] summary совпадает с machine-readable result;
- [ ] limitations включены;
- [ ] confidential fields удалены по policy;
- [ ] reviewer findings учтены;
- [ ] approval outcome указан точно;
- [ ] production claims отсутствуют.

## Связанные документы

- [Известные ограничения](known_limitations.md)
- [Metric policy](metric_policy.md)
- [Правовой checklist](legal_requirements_checklist.md)
- [Руководство approver](result_approver_guide.md)
- [Текущий статус](../status/current-status.md)
