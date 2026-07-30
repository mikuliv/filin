# Инфраструктура независимой сетевой проверки

## Статус

Каталог содержит технический каркас будущей проверки. Конфигурация и контракты
проверены модульными тестами. Научный эксперимент не запускался, корпуса и метки
не создавались, модель не обучалась, внешний результат не оценивался.
Real-network capture path реализован и статически проверен; end-to-end Docker smoke
остаётся невыполненным.

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

Техническая конфигурация намеренно содержит предупреждения proxy-risk и
неутверждённые критерии принятия. До их устранения freeze нельзя запечатать.

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
python -m lab.network_validation.cli build-freeze-preview
```

Эти команды не запускают эксперимент. `run-technical-smoke` требует явного
`--confirm-disposable` и каталога вне репозитория; он предназначен только для
проверки сетевого plumbing и не рассчитывает научные метрики.

## Тестирование

```powershell
python -m pytest ml/tests/test_network_validation_infrastructure.py -q
docker compose -f lab/network_validation/compose.yaml config
```

Перед будущим freeze владелец отдельно утверждает числовые критерии принятия,
устраняет предупреждения proxy-risk, фиксирует image digests и разрешает запуск.
`requirements.lock` фиксирует зависимости host-side Zeek/feature validation;
client и target images используют только стандартную библиотеку Python.
