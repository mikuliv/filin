# Campaigns

## v0.3.6

`v0_3_6_blind_holdout.yaml` задаёт 12 prospective runs и 252 окна. Повтор допускается только до lock
при infrastructure/integrity ошибке; metric-driven rerun запрещён.

## Назначение

Campaign manifest задаёт независимые laboratory runs, seeds, роли train/test/robustness и безопасные параметры сценариев.

## Что реализовано

Campaign runners сохраняют status и checksums; `--resume` предназначен для продолжения незавершённых attempts без повторения успешных фаз.

## Основные файлы

- `v0_3_zeek_sensor.yaml` — независимая sensor campaign v0.3;
- `v0_3_2_zeek_robustness.yaml` — robustness campaign v0.3.2;
- `run_sensor_campaign.py` — запуск/продолжение sensor campaign.
- `v0_3_4_training.yaml` и `v0_3_4_internal_validation.yaml` — раздельные
  кампании 12/6 для v0.3.4;
- `run_v034_campaign.py` — последовательный resume-runner v0.3.4.

## Входные данные и выходные данные

Вход — manifest; выход — run statuses и runtime artifacts в `lab/output/`.

## Запуск

Параметры runner: `python lab/campaigns/run_sensor_campaign.py --help`.

## Проверки

Наличие каталога не равно успеху: учитываются statuses, hashes и последующие audits.

## Ограничения

Campaign roles разделяют данные, но не подтверждают production applicability.
`v0.3.3` не является входом v0.3.4; его runtime dataset не допускается в
training или model selection.

## Связанные документы

[Происхождение данных](../../docs/data-provenance.md), [воспроизводимость](../../docs/reproducibility.md).

## v0.3.7

- `v0_3_7_training.yaml`: 12 runs, seeds 12701–13003, 336 scored окон.
- `v0_3_7_internal_validation.yaml`: 6 validation-only runs, seeds 13101–13302, 168 scored окон.
- `run_v0_3_7_training.py` и `run_v0_3_7_validation.py`: strict resumable Docker runners.
- `v0_3_7_preflight.py`: проверка safety, capture, marker mapping, profiles и warm-up isolation без открытия validation rows.
- `v037_runner.py`: resumable Docker runner; для validation изолирует каждый execution в собственный PCAP и объединяет только нормализованные Zeek observations, исключая marker flows.

Успешные runs при `--resume` не выполняются повторно. Validation runner требует frozen candidate manifest.

## v0.3.8

- `v0_3_8_training.yaml`: 12 новых runs, 72 warm-up и 432 scored окна.
- `v0_3_8_internal_validation.yaml`: 6 новых runs, 36 warm-up и 216 scored окон.
- `run_v0_3_8_training.py` и `run_v0_3_8_validation.py`: strict resumable runners.
- `v0_3_8_preflight.py`: fail-closed проверка изоляции, capability и integrity.
- `v038_runner.py`: per-run Docker capture, нормализация вывода subprocess и безопасное возобновление без повторения успешных запусков.

Validation runner требует frozen candidate, а evaluation — дополнительно frozen validation lock. Ни один validation row не доступен nested selection.

## v0.3.9

- `v0_3_9_training.yaml`: 12 runs, 72 warm-up, 504 scored windows, 168 episodes.
- `v0_3_9_internal_validation.yaml`: 6 runs, 36 warm-up, 252 scored windows, 84 episodes.
- `v039_runner.py`: strict/resumable per-execution capture без повторения success.
- Validation collection требует frozen candidate; prediction требует immutable lock.

Background и routes не зависят от labels. Rate limits, internal DNS allowlist и target responsiveness проверяются до принятия run.
