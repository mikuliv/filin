# Стиль и терминология документации

## Правила

- Один H1 на документ; далее последовательная hierarchy.
- Версии пишутся как `v0.3.18`.
- Статусы используют `completed`, `passed`, `failed`, `superseded`,
  `corrected`.
- Английский technical term при первом употреблении получает краткое русское
  пояснение.
- Passed stage не равен production readiness.
- Claim сопровождается scope, limitation и ссылкой на evidence.
- Current status не копируется: authoritative machine-readable источник —
  `docs/status/project-status.yaml`.

## Термины

- **Candidate** — конкретная model lineage с identity и contracts.
- **Frozen candidate** — candidate, который нельзя изменять во время evaluation.
- **Development candidate** — результат training/development, ещё не production.
- **Holdout** — набор, не использованный для разработки проверяемого candidate.
- **Blind holdout** — holdout, labels которого скрыты до prediction commitment.
- **Prospective trial** — evaluation на заранее не использованных inputs.
- **Targeted trial** — ограниченная проверка конкретных исправлений.
- **Endurance campaign** — длительный runtime workload.
- **Passive event** — событие без полномочий на воздействие.
- **Shadow mode** — реальная пассивная эксплуатация; сейчас запрещена.
- **Staging** — изолированная проверочная среда, не production.
- **Runtime** — execution artifacts и процессы конкретного запуска.
- **Evidence** — проверяемое подтверждение claim.
- **Evidence bundle** — manifest и связанные aggregate artifacts.
- **Commitment** — canonical hash фиксации содержимого, не цифровая подпись.
- **Semantic duplicate** — повтор логического события.
- **Transport duplicate** — повторная доставка того же события.
- **Abstention** — отказ от class decision, не правильный ответ.
- **Coverage** — доля episodes без abstention.
- **Backend integration** — подключение current runtime к backend; запрещено.
- **Production readiness** — готовность к эксплуатации; не заявлена.
