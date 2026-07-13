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
