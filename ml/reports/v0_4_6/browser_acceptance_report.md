# Браузерная приёмка v0.4.6

Приёмка выполнена реальным Codex in-app browser против локальной консоли на `127.0.0.1`. Создано 30 runtime-снимков; изображения не входят в Git и находятся в `runtime/lab_console/v0_4_6/browser/`.

| Режим | CSS viewport | Снимков |
|---|---:|---:|
| desktop | 1920×1080 | 10 |
| compact | 1366×768 | 10 |
| effective 125% | 1536×864, эквивалент 1920×1080 при 125% | 10 |

В каждом режиме проверены catalog, overview, lineage, training, artifact, screening, comparison, admission gate, manual review и read-only candidate versions.

Подтверждено:

- официальный proposal восстанавливается после перезапуска консоли;
- manual review показывает `manual_review_completed = true`, gate `20 passed / 0 failed`;
- русские ограничения отображаются читаемо, без Unicode escape-последовательностей;
- длинные SHA и JSON остаются внутри прокручиваемых панелей;
- proposal отсутствует в candidate catalog;
- register/activate/promote controls отсутствуют;
- browser console: 0 errors, 0 warnings.

Машиночитаемый результат: [browser_acceptance_result.json](browser_acceptance_result.json).
