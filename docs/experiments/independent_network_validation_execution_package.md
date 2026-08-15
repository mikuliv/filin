# Execution package независимой сетевой валидации

## Статус

`EXECUTION_PACKAGE_CANDIDATE_VALID`.

Superseding freeze `network-validation-superseding-249104f7e7536356` валиден и execution-complete. Его canonical digest равен `249104f7e7536356621433f1b635c46967729164c58d53479770768372629d86`, source Git SHA — `2377ab2cd12ead340d4f377aede9105635dbfe28`, содержащий freeze commit — `26222536d71aca898d382b46f6b1c59f1102bbd2`.

Exact Phase 1 run plan материализован только из frozen superseding inputs. Candidate валиден, но official package ещё не создан и исполнение запрещено до отдельного clean-tree commit, создания official package и будущего runtime preflight.

Научная кампания не запускалась. Scientific sessions, corpus, labels, model, predictions и metrics отсутствуют.

## Run plan

- 288 scenario templates;
- три repetitions на template;
- 864 execution units;
- repetition 0/1/2 соответствует development train/calibration/blind internal holdout;
- каждый split содержит 288 units;
- execution seed вычисляется как frozen base seed плюс `repetition_index × 100000`;
- execution tokens и полный identity digest уникальны;
- порядок соответствует ascending frozen order key;
- run-plan digest: `7f8109ed1b4d0216beae71c5999359bc67710629f66eedb977cb48d0142426df`;
- exact-order digest: `be63a536b89eadad7d97ff63a40a314c37052452a8ce460b5ef1ac5e067588c2`.

Матрица сохраняет шесть behaviors, две generator families, две infrastructure profiles, две target implementations, два service ports и три intensity bands. Все nuisance locks равны `false`. Background policies распределены по 72 templates, 24 frozen counterfactual pairs сохранены.

## Границы Phase 1

Runner получает frozen scenario metadata, timing, retry, image identities и exact execution identity. Sensor имеет только `NET_RAW`, `NET_ADMIN`, `SETUID`, `SETGID`; privileged mode, Docker socket и host network запрещены. Capture readiness должна предшествовать marker и scientific traffic. PCAP размером 24 bytes или с нулём пакетов является failure.

Evaluator до label unlock получает только opaque evaluation token, feature contract/order digests, feature row и session-integrity digest. Scenario, generator, infrastructure, target, port, seed, split, paths, markers и counterfactual metadata запрещены. Opaque mapping требует внешний secret, который не создаётся и не хранится в Git.

Label vault остаётся `absent_locked`: labels не созданы и не разблокированы. Blind internal holdout известен controller, но недоступен training, calibration, model selection и analyst tuning.

## Контракты

- `phase1_run_plan.json` — exact ordered list 864 execution units;
- `runner_contract.json` — runner visibility, isolation, capabilities и capture readiness;
- `evaluator_contract.json` — evaluator visibility и blind-holdout guard;
- `sealed_mapping_contract.json` — внешний key для opaque evaluation tokens;
- `session_integrity_contract.json` — обязательные SHA и session sealing;
- frozen `label_vault_contract.json`, `output_contract.json`, `campaign_ledger_contract.json` и `preflight_contract.json` используются без изменения;
- `phase1_preflight_contract.json` отделяет static package validation от будущего runtime preflight.

Package tooling выполняет только чтение, каноническую материализацию и валидацию. В нём отсутствуют команды запуска scientific sessions, создания labels, обучения и оценки.

## Безопасные команды

```powershell
python -m lab.network_validation.cli materialize-execution-package-inputs
python -m lab.network_validation.cli build-execution-package-preview
python -m lab.network_validation.cli inspect-run-plan
python -m lab.network_validation.cli inspect-label-boundary
python -m lab.network_validation.cli validate-execution-package
python -m lab.network_validation.cli audit-execution-preflight --help
python -m lab.network_validation.cli create-official-execution-package --help
```

## Следующее действие

Зафиксировать tooling и inputs отдельным чистым commit, затем из него создать immutable official Phase 1 execution package. Scientific campaign при этом не запускается.
