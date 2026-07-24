# Технический checklist правовых требований

## Ограничение документа

Это не договор и не юридическое заключение. Применимость, формулировки и
соглашения должен проверить компетентный юрист соответствующей юрисдикции.

## До первого обмена материалами

- [ ] определены owner и цель обработки;
- [ ] подтверждено право передачи;
- [ ] выбран единственный usage mode;
- [ ] определены controller/processor responsibilities, если применимо;
- [ ] проверены confidentiality и trade-secret restrictions;
- [ ] проверены personal data и communications secrecy;
- [ ] проверены credentials и sensitive payload;
- [ ] определены location и cross-border transfer;
- [ ] определены recipients и access control;
- [ ] определены incident notification responsibilities.

## До trial-plan agreement

- [ ] roles и независимость согласованы;
- [ ] retention и deletion согласованы;
- [ ] legal hold обработан;
- [ ] права на code, model и dataset проверены;
- [ ] повторное использование ограничено;
- [ ] negative-result handling согласован;
- [ ] publication rights согласованы;
- [ ] security controls и breach response проверены.

## До передачи данных

- [ ] dataset прошёл privacy/secret clearance;
- [ ] transfer channel и encryption согласованы;
- [ ] destination и получатели подтверждены;
- [ ] deletion evidence определено;
- [ ] raw PCAP, labels и identifiers минимизированы;
- [ ] письменное разрешение сохранено.

## Основания остановки

Unclear usage right, privacy clearance failure, credential finding или
неподтверждённый transfer запрещают приём dataset. Техническая команда не
заменяет юридическое решение предположением.

## Результат checklist

Сохраняются дата, проверившая компетентная сторона, scope, unresolved issues и
разрешённые действия. Checklist сам по себе не разрешает external trial.

## Связанные документы

- [Data acceptance](data_acceptance_policy.md)
- [Передача данных](data_transfer_requirements.md)
- [Хранение и удаление](retention_and_deletion_requirements.md)
- [Publication](publication_requirements.md)
- [Известные ограничения](known_limitations.md)
- [Текущий статус](../status/current-status.md)
