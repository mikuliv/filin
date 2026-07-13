# Воспроизводимость

## Post-v0.3.7 integrity commands

Automatic CI uses no protected runtime artifacts:

```text
python tools/docs/validate_documentation.py --strict
python tools/check_release_images.py --compose lab/docker/docker-compose.lab.yml --release
python tools/audit/check_repository_artifacts.py
python -m compileall tools ml backend lab
python -m unittest discover -s ml/tests -p "test_*.py"
python -m unittest discover -s backend/tests -p "test_*.py"
git diff --check
```

Protected candidate verification is a separate local command:

```text
python tools/audit/verify_secure_artifacts.py --root "%FILIN_SECURE_ARTIFACT_ROOT%" --strict
```

If the secure root is unavailable the result is
`secure_artifacts_not_available`; it is not a pass. A real environment-control
check is also manual and container-scoped:

```text
python tools/audit/apply_environment_profile.py --catalog lab/holdout/v036_environment_profiles.yaml --profile observation_stress --container traffic-client --seed 1
```

The environment command always attempts rollback and verifies that netem is no
longer active. It must run only in the isolated laboratory Docker network.

## Требования

Нужны Docker Engine/Docker Desktop и Python с зависимостями проекта. PCAP создаётся и проверяется внутри Docker-managed storage; runtime artifacts находятся в `lab/output/` и `ml/reports/` и не коммитятся.

## Быстрые проверки

```powershell
python tools/docs/validate_documentation.py --strict
python -m compileall tools ml/tests
python -m unittest discover -s ml/tests -p "test_*.py"
```

## Проверка CLI

```powershell
python lab/sensor/run_v0_3_sensor_stage.py --help
python lab/robustness/run_v0_3_2_stage.py --help
python ml/features/validators.py --help
```

Campaign runners поддерживают `--resume`; он предназначен для проверки и продолжения существующих attempts. Не запускайте исторические 9 sensor-runs или 12 robustness-runs повторно только ради документации.

## Контроль целостности

Capture и Zeek processing сопоставляются по SHA-256 PCAP. Dataset indexes, provenance и split audits проверяют итоговые артефакты. Команды тяжёлых кампаний документируются в README соответствующих подсистем, а не выполняются как часть быстрой проверки.
