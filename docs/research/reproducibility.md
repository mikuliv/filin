# Воспроизводимость и evidence

Воспроизводимость строится на versioned protocols, deterministic serialization,
hash commitments, manifests, validators, test reports и claim-evidence ledgers.
Historical bundle не переписывается: исправление выпускается новой revision или
corrective stage.

## Термины Git HEAD

- `validated_source_head` — commit кода и документации, относительно которого
  выполнены validators.
- `final_evidence_commit` — commit, добавляющий итоговые reports и manifests.
- `final_repository_head` — фактический HEAD после всех последующих
  maintenance-коммитов.

Поле `final_head` в policy v0.3.18 имеет scope
`source_and_documentation_before_final_evidence_commit`. Поэтому оно является
validated source HEAD, а не окончательным HEAD всей истории репозитория.

Raw PCAP, labels, predictions, databases и traces остаются runtime-only. Tracked
evidence содержит aggregate reports и hashes, достаточные для заявленного
validation scope.
