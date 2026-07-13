# Roadmap

## После v0.3.6

Prospective holdout policy не пройдена, поэтому v0.3.7 shadow mode не разрешён. Следующий допустимый
шаг — новый training cycle с новой internal validation и новым holdout. Данные v0.3.6 нельзя
использовать для настройки текущего candidate или threshold.

## v0.3.4 research boundary

v0.3.3 is completed with a negative environment-evaluation result. The active
next stage is **v0.3.4 — redesign training campaign, benign representation and
feature pipeline**. A new blind/external holdout belongs to **v0.3.5** and must
not be used during v0.3.4 development.

## Current roadmap status

v0.3.3 is completed with a negative environment-evaluation result. The active
next stage is **v0.3.4 — redesign training campaign, benign representation and
feature pipeline**. A new blind/external holdout belongs to **v0.3.5** and must
not be used during v0.3.4 development.

## Завершённые этапы

- v0.2.2 — source-aware feature profiles и actual execution windows.
- v0.2.3 — независимые laboratory executions с train/test separation.
- v0.2.4 — baseline evaluation client profiles.
- v0.3 — независимый Zeek sensor pipeline и marker-aware correlation.
- v0.3.1 — baseline evaluation `network_sensor_v0_3`.
- v0.3.2 — frozen robustness evaluation.
- v0.3.3 — completed negative environment evaluation; benign recall `0.000`.
- v0.3.3 — completed negative environment evaluation; benign recall `0.000`.

## Текущий документационный этап

Нормализация и актуализация документации проекта «Филин»: единые термины, проверяемые ссылки, разделение реализованного и запланированного, фиксация ограничений.

## Ближайший технический этап

**Филин v0.3.3 — расширение проверки на изменённой сетевой среде и более разнообразном фоновом трафике.** Этап не начат. Его цель — расширить независимую внешнюю проверку, не подменяя её дополнительными связанными окнами.

## Филин v0.3.4

Redesign training campaign и benign representation. Причина: frozen baseline
воспроизводит source test, но имеет benign recall `0.000` на 204 external
windows. Новое обучение и tuning не относятся к v0.3.3.

## Среднесрочные этапы

- дополнительная validation на иной инфраструктуре и сервисной топологии;
- более разнообразные безопасные background patterns;
- воспроизводимая процедура deployment validation после накопления данных;
- отдельная оценка наблюдаемости encrypted traffic metadata.

## Долгосрочная концепция

Incident representation, MITRE ATT&CK mapping, Sigma drafts, test bench validation, SIEM integration и analyst interface остаются будущими направлениями. Они не реализованы в текущем pipeline.
