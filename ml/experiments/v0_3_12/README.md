# Филин v0.3.12

Этап выполняет только frozen multi-benchmark regression кандидата v0.3.11. Обучение, калибровка, conformal fit, tuning, Docker, Zeek и feature extraction запрещены. Исторические наборы оцениваются только при доказанной совместимости готовой 51-признаковой таблицы; отсутствие или расхождение authoritative counts фиксируется как блокировка, а не исправляется.

Порядок доступа fail-closed: input lock без labels, immutable prediction, post-hoc labels и лишь затем historical comparison. Все строковые predictions, traces и подробные отчёты остаются runtime-only в `ml/reports/v0_3_12`.

