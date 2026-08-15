# Superseding-freeze review независимой сетевой валидации

## Статус

`OFFICIAL_SUPERSEDING_FREEZE_CREATED`.

Official superseding freeze `network-validation-superseding-249104f7e7536356` создан из чистого commit `2377ab2cd12ead340d4f377aede9105635dbfe28`. Его canonical payload digest равен `249104f7e7536356621433f1b635c46967729164c58d53479770768372629d86`.

Predecessor `network-validation-d6e946188d870a7f` и его canonical digest `870946390f9ca8a5fe0ac2c53e7855e979ef242d9486815ef67d6d47ca9cbe41` не изменены. Superseding inputs прошли обязательную техническую проверку до создания official superseding freeze.

Научная кампания не запускалась. Scientific sessions, corpus, labels, model, predictions и metrics отсутствуют.

## Factor audit

Старая 72-template matrix имеет строгие связи:

| Relation | Predecessor | Draft superseding matrix |
| --- | --- | --- |
| infrastructure → target | locked | orthogonal |
| infrastructure → port | locked | orthogonal |
| target → port | locked | orthogonal |

Predecessor содержит только комбинации `profile_a + target_a + 8080` и `profile_b + target_b + 9080`. Поэтому его unseen-infrastructure и unseen-target criteria нельзя интерпретировать независимо.

Draft matrix содержит полный factorial basis:

```text
6 behaviors × 2 families × 2 profiles × 2 targets × 2 ports × 3 intensity bands
= 288 scenario templates
```

Каждый behavior имеет 48 templates. Background policy распределена по 12 templates каждого из четырёх вариантов внутри каждого behavior и не увеличивает factorial basis. Все mappings profile/target/port имеют обе альтернативы; три nuisance locks равны `false`.

## Draft execution policy

- три repetitions на template, всего 864 execution units;
- repetition 0/1/2 соответствует train/calibration/blind internal holdout;
- execution seed равен base seed плюс `repetition_index × 100000`;
- execution token и order key вычисляются SHA-256 без времени и системной случайности;
- concurrency равна 1;
- каждый session требует новый Compose project, containers, networks, state и output directory;
- warmup 2.0 s, capture lead/lag 0.5 s, cooldown 1.0 s;
- maximum clock offset 500 ms;
- максимум один technical retry по frozen allowlist;
- substitution и replacement seed запрещены;
- exclusion разрешён только по пяти integrity reason codes;
- exact primary splits и development stress views материализованы до сбора данных;
- 24 predecessor counterfactual pairs сохранены.

Acceptance criteria, feature contract, feature order и predecessor image identities не менялись. Target implementations уже принимали параметр `--port`, поэтому Dockerfiles и их build inputs не изменены.

## Technical orthogonality smoke

Первопричиной пустого PCAP был немедленный отказ `tcpdump` при privilege transition: sensor оставлял только `NET_RAW` и `NET_ADMIN`, тогда как запуск с `-Z root` также требует `SETUID` и `SETGID`. Глобальный PCAP header создавался до этого отказа, поэтому файл имел ровно 24 bytes. Runtime topology, interface `any` и BPF не являлись первопричиной.

После минимального исправления sensor и common client имеют одинаковый network namespace, capture readiness подтверждается до client actions, а `tcpdump` завершается graceful `SIGINT` до чтения PCAP. Сначала отдельно прошла комбинация `profile_a + target_a + 8080`, затем полный disposable smoke прошёл 8/8 комбинаций profile/target/port.

Для каждой комбинации подтверждены target health, HTTP actions, фактический TCP endpoint, непустой PCAP, Zeek `conn.log` и `http.log`, parameter realization, 51 конечный числовой признак, causal guard и capture manifest. PCAP содержали 88–93 packets; каждый Zeek result содержал 13 connection rows и 6 HTTP rows. Runtime locks infrastructure→target, infrastructure→port и target→port равны `false`.

Disposable PCAP, Zeek logs и session outputs после проверки удалены. Это техническая проверка исполнимости, а не научная сессия и не результат валидации модели.

## Следующее действие

Superseding freeze используется как единственный источник exact Phase 1 execution package. Подготовка package не запускает кампанию; сам freeze сохраняет `scientific_pass_allowed=false` и `production_approval=false`.
