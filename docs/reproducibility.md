# Воспроизводимость

## Команды проверки целостности после v0.3.7

Автоматический CI не использует защищённые runtime-артефакты:

```text
python tools/docs/validate_documentation.py --strict
python tools/check_release_images.py --compose lab/docker/docker-compose.lab.yml --release
python tools/audit/check_repository_artifacts.py
python -m compileall tools ml backend lab
python -m unittest discover -s ml/tests -p "test_*.py"
python -m unittest discover -s backend/tests -p "test_*.py"
git diff --check
```

Проверка защищённого кандидата выполняется отдельной локальной командой:

```text
python tools/audit/verify_secure_artifacts.py --root "%FILIN_SECURE_ARTIFACT_ROOT%" --strict
```

Если защищённое хранилище недоступно, результатом будет
`not_executed_secure_artifacts_unavailable`; это не считается успешной проверкой, а
`--strict` завершится кодом 2. Реальная
проверка управления условиями среды также выполняется вручную и ограничивается
конкретным контейнером:

```text
python tools/audit/apply_environment_profile.py --catalog lab/holdout/v036_environment_profiles.yaml --profile observation_stress --container traffic-client --seed 1
```

Команда управления средой всегда пытается выполнить откат и проверяет, что
netem больше не активен. Её разрешено запускать только в изолированной
лабораторной Docker-сети.

## Требования

Нужны Docker Engine/Docker Desktop и Python с зависимостями проекта. PCAP создаётся и проверяется внутри Docker-managed storage; runtime artifacts находятся в `lab/output/` и `ml/reports/` и не коммитятся.

## Быстрые проверки

```powershell
python tools/docs/validate_documentation.py --strict
python -m compileall tools ml/tests
python -m unittest discover -s ml/tests -p "test_*.py"
```

## Ручная Docker-приёмка перед v0.3.8

Эта команда не входит в обычный CI и не выполняет model training или predict:

```powershell
python lab/campaigns/run_pre_v038_runtime_smoke.py --output lab/output/pre_v038_runtime_smoke/attempt_local
```

Каждый запуск требует нового output directory и отдельного Compose project
`filin_pre_v038_smoke`. PCAP, Zeek logs, normalized events, dataset и runtime
report остаются в ignored storage.

## Проверка CLI

```powershell
python lab/sensor/run_v0_3_sensor_stage.py --help
python lab/robustness/run_v0_3_2_stage.py --help
python ml/features/validators.py --help
```

Campaign runners поддерживают `--resume`; он предназначен для проверки и продолжения существующих attempts. Не запускайте исторические 9 sensor-runs или 12 robustness-runs повторно только ради документации.

## Контроль целостности

Capture и Zeek processing сопоставляются по SHA-256 PCAP. Dataset indexes, provenance и split audits проверяют итоговые артефакты. Команды тяжёлых кампаний документируются в README соответствующих подсистем, а не выполняются как часть быстрой проверки.
