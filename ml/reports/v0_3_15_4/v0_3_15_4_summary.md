# Итоги этапа v0.3.15.4

Этап контролируемой смешанной переработки завершён. Использована revision 2: первый corpus сохранён как недействительный после обнаружения неполного class balance в calibration; заменяющая кампания получила новые ID и seeds.

- 25 сессий, 5 000 новых уникальных PCAP, 250 warmup и 4 750 scored-окон.
- Zeek 7.0.5: 5 000 контейнерных обработок, fallback 0, внешние цели 0.
- Feature contract v2: 51 признак, provenance 100%, запрещённые источники 0.
- Training gate: `true`; проверены ровно три HGB-конфигурации, выбран вариант C.
- Candidate: `v03154:65a3dd912d845bc1`; sigmoid calibration и Mondrian conformal использовали только calibration split.
- Единственный internal audit: benign recall 1.000, FPR 0.000, attack macro recall/F1 1.000/1.000.
- Этап прошёл: `true`.
- Candidate готов только к prospective evaluation v0.3.15.5: `true`.
- Backend integration, shadow mode, production, automatic enforcement, external validation и v0.3.16: запрещены.
