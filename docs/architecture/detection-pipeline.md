# Конвейер обнаружения

## Реализация

Pipeline принимает подтверждённый PCAP input, строит Zeek-derived causal
observations и применяет Зафиксировано candidate `v03154:65a3dd912d845bc1`.
признак contract фиксирует порядок и семантику 51 признака.

## Проверенный область применимости

Candidate прошёл development, процедурно отделённый holdout того же синтетического
generator family и последующие runtime compatibility gates. Это подтверждает
технический конвейер и воспроизводимость frozen-метрик, но не семантически независимый
holdout, внешнюю валидность или практическую точность. Подробности приведены в
[переоценке методологии](../experiments/v0_3_15_4_v0_3_15_5_methodology_reassessment.md).

## Границы

Fit, calibration, conformal fit, признак selection и threshold selection не
выполняются в текущий оценка path. Неподдерживаемые форматы не
интерпретируются как PCAP.
