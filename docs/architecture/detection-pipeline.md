# Конвейер обнаружения

## Реализация

Pipeline принимает подтверждённый PCAP input, строит Zeek-derived causal
observations и применяет Зафиксировано candidate `v03154:65a3dd912d845bc1`.
признак contract фиксирует порядок и семантику 51 признака.

## Проверенный область применимости

Candidate прошёл development, independent scientific отложенная контрольная выборка и последующие
среда выполнения compatibility gates в лабораторных условиях. Эти результаты не
экстраполируются на реальный организационный трафик.

## Границы

Fit, calibration, conformal fit, признак selection и threshold selection не
выполняются в текущий оценка path. Неподдерживаемые форматы не
интерпретируются как PCAP.
