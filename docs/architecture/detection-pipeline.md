# Detection pipeline

## Реализация

Pipeline принимает подтверждённый PCAP input, строит Zeek-derived causal
observations и применяет frozen candidate `v03154:65a3dd912d845bc1`.
Feature contract фиксирует порядок и семантику 51 признака.

## Проверенный scope

Candidate прошёл development, independent scientific holdout и последующие
runtime compatibility gates в лабораторных условиях. Эти результаты не
экстраполируются на реальный организационный трафик.

## Границы

Fit, calibration, conformal fit, feature selection и threshold selection не
выполняются в current evaluation path. Неподдерживаемые форматы не
интерпретируются как PCAP.
