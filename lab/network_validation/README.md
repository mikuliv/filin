# Инфраструктура независимой сетевой проверки

## Статус

Каталог содержит технический каркас будущей проверки. Конфигурация и контракты
проверены модульными тестами. Научный эксперимент не запускался, корпуса и метки
не создавались, модель не обучалась, внешний результат не оценивался.
Real-network capture path реализован и подтверждён одноразовым техническим Docker
smoke. Disposable output не является корпусом или научным результатом.

## Сетевой путь

```text
scenario -> common-client -> Docker network -> target -> sensor-capture
         -> PCAP -> Zeek -> SessionFeatureAdapter -> 51 features
```

`common-client` использует единую identity, образ, набор заголовков и сетевой стек
для всех поведений. Два семейства сценариев реализованы в независимых модулях и
выдают только сетевые действия. Метка не входит в schema сценария, execution event,
capture manifest или model input.

`target-a` и `target-b` имеют разные реализации HTTP-сервера, порты, DNS aliases,
подсети и response templates. `sensor-capture` использует существующий capture
sidecar и видит namespace клиента. Привилегированный режим и Docker socket не
используются.

## Контракты и предохранители

- `contracts.py` строго проверяет сценарии, события, markers и capture manifests;
- `parameter_verification.py` сравнивает requested параметры с наблюдениями Zeek;
- `feature_adapter.py` изолирует state по session и сохраняет причинный порядок;
- `causal_guard.py` допускает только точный числовой вектор из 51 признака;
- `planning.py` проверяет counterfactual pairs, whole-session split и proxy risks;
- `freeze.py` формирует preview и environment lock, но отклоняет seal при `TBD`;
- `candidate_identity.py` связывает внутренний и внешний ID с SHA финальных bytes.

`technical_campaign.json` остаётся disposable fixture и намеренно сохраняет 19
proxy-risk предупреждений. Отдельный `freeze_candidate_campaign.json` задаёт
декларативную факторную матрицу из 72 сценариев, но не разрешает их запуск.
Числовые критерии находятся в `acceptance_criteria.json`, переносимые идентификаторы
образов — в `image_lock.json`. Научный корпус этими файлами не создаётся.
Отсутствие корпуса, модели, evaluation, открытых labels и внешнего результата до
эксперимента не блокирует seal протокола. Эти результаты необходимы позже для
scientific pass; внешний корпус остаётся обязательным критерием.

## Безопасные команды

```powershell
python -m lab.network_validation.cli validate-config
python -m lab.network_validation.cli plan-campaign
python -m lab.network_validation.cli validate-counterfactuals
python -m lab.network_validation.cli render-compose
python -m lab.network_validation.cli inspect-environment
python -m lab.network_validation.cli validate-parameter-contract
python -m lab.network_validation.cli validate-capture-manifest
python -m lab.network_validation.cli validate-split
python -m lab.network_validation.cli validate-freeze-candidate
python -m lab.network_validation.cli inspect-proxy-risks
python -m lab.network_validation.cli inspect-image-lock
python -m lab.network_validation.cli verify-image-reproducibility --help
python -m lab.network_validation.cli build-freeze-preview
python -m lab.network_validation.cli validate-official-freeze
python -m lab.network_validation.cli audit-execution-readiness
python -m lab.network_validation.cli build-execution-package-preview
python -m lab.network_validation.cli validate-execution-package
python -m lab.network_validation.cli inspect-run-plan
python -m lab.network_validation.cli inspect-label-boundary
python -m lab.network_validation.cli materialize-superseding-inputs
python -m lab.network_validation.cli validate-superseding-inputs
python -m lab.network_validation.cli run-factor-orthogonality-smoke --help
python -m lab.network_validation.cli create-official-superseding-freeze --help
python -m lab.network_validation.cli validate-official-superseding-freeze --help
```

Для проверки capture path только на первой комбинации используется флаг `--diagnostic-first-only`; такой запуск не устанавливает общий статус полного orthogonality smoke.

Эти команды не запускают эксперимент. `run-technical-smoke` требует явного
`--confirm-disposable` и каталога вне репозитория; он предназначен только для
проверки сетевого plumbing и не рассчитывает научные метрики.

## Тестирование

```powershell
python -m pytest ml/tests/test_network_validation_infrastructure.py -q
docker compose -f lab/network_validation/compose.yaml config
```

Перед будущим freeze владелец отдельно завершает воспроизводимые OCI-сборки,
проверяет чистое рабочее дерево и только затем рассматривает разрешение запуска.
Официальный pre-experiment freeze сохранён в `freeze/official_freeze.json` и связан с
коммитом image lock. Он фиксирует план, критерии, порядок признаков, окружение и
воспроизводимые OCI-идентичности, но не подтверждает качество модели.
`requirements.lock` фиксирует зависимости host-side Zeek/feature validation;
client и target images используют только стандартную библиотеку Python.
