# Исторический freeze-review независимой сетевой проверки

> Документ описывает предшествующий freeze с 72 сценариями. Он сохранён для
> истории и не является текущим планом. Текущие 288 шаблонов и 864 единицы
> описаны в [методике Phase 1](../research/independent-network-validation.md).

## Границы

Review подготавливает декларативные входы будущей независимой проверки. Он не
запускает сетевые сценарии, не создаёт train, calibration или holdout, не открывает
labels, не загружает модель и не рассчитывает научные метрики. Official freeze
фиксирует только неизменяемые pre-experiment входы и не разрешает запуск кампании.

## Два разных плана

`technical_campaign.json` — disposable fixture технического пути. Он сохраняет 19
предупреждений: по три infrastructure/target/port lock для каждого из шести типов
поведения и одно предупреждение неперекрывающейся интенсивности.

`freeze_candidate_campaign.json` — отдельный scientific campaign plan без права
исполнения. Его назначение не меняет статус технического smoke и не делает fixture
freeze-ready.

## Факторная матрица

Freeze-candidate раскрывается детерминированно:

| Измерение | Покрытие |
|---|---|
| Поведение | 6 типов |
| Семейство генератора | `family_a`, `family_b` |
| Профиль инфраструктуры | `profile_a`, `profile_b` |
| Target | `target_a`, `target_b` |
| Внутренний порт | 8080, 9080 |
| Интенсивность | low, medium, high |
| Всего | 72 сценария |

Bands имеют общую основу для всех поведений: 2 действия за 4 секунды, 6 за 6 и
12 за 6. Для каждого поведения предусмотрено по три сценария `http`, `dns`,
`keepalive` и `combined`. Ортогональное назначение сохраняет покрытие каждой
политики в обеих families, обоих profiles и всех трёх bands.

## Proxy-risk и counterfactual coverage

Validator не ослаблялся. Freeze-candidate покрывает каждое поведение обеими
families, profiles, targets и ports, а также всеми тремя bands. Результат для пяти
блокирующих классов proxy-lock — ноль совпадений.

Детерминированно формируются 24 пары. Они проверяют смену family,
infrastructure/target/port, HTTP paths, response status profile и timing внутри
одного поведения, а также одинаковые port, target, action count и nominal rate
между разными поведениями. Каждая пара содержит `pair_id`, разрешённые различия и
обязательные равенства. Эти поля запрещены в 51-признаковом model input.

## Критерии принятия

Числовые исследовательские пороги находятся в `acceptance_criteria.json`. Они
заданы до корпуса, не могут подбираться по final holdout и не являются production
SLA. External corpus обязателен; отсутствие его результата блокирует scientific
pass. Провал любого обязательного критерия запрещает promotion.

## Image digest method

Для `zeek/zeek:7.0.5` раздельно зафиксированы переносимый `repository@sha256`,
linux/amd64 platform manifest, config и layer digests. Local image ID остаётся
`unresolved` и не используется как registry identity. Для локальных образов identity должна получаться из двух
независимых OCI builds с одинаковыми inputs, platform и отключёнными provenance и
SBOM. Сравниваются platform manifest, config и layers; SHA tar-архива не считается
достаточным.

Build-inputs digest включает только Dockerfile и фактически копируемые файлы в
каноническом порядке. Runtime output, PCAP, Zeek logs, caches и временные OCI
архивы не входят в digest.

Четыре локальных образа проверены двумя независимыми OCI-экспортами для
`linux/amd64`. Для каждой пары совпали index, platform manifest, config, ordered
layers и runtime-конфигурация. Базовые образы закреплены platform manifest digest,
а image lock имеет статус `resolved_reproducible` без локальных image ID.

## Pre-experiment seal

- подтверждённая воспроизводимость common-client, target-a, target-b и sensor-capture;
- чистое дерево коммита `a6a979aef803ba776933b39dbd7607bd0833cc63`;

Proxy-locks и числовые `TBD` не являются blockers freeze-candidate. Preview имеет
`seal_allowed: true`; официальный пакет сохранён в
`lab/network_validation/freeze/official_freeze.json`.

Отсутствующие научный корпус, внешний результат, обученная модель, evaluation и
открытые labels перечисляются как ожидаемые pre-experiment состояния и не блокируют
предварительный seal. После кампании scientific pass требует выполнения всех
критериев, включая результат обязательного external corpus. Scientific pass не
означает production approval. Официальный freeze не является scientific pass:
научная кампания не запускалась, corpus и labels не создавались, модель не
обучалась, метрики и внешняя валидность не оценивались.
