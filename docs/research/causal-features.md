# Causal feature extraction

Current representation содержит 51 признак, вычисляемый из наблюдений,
доступных к моменту prediction. Будущие события, labels и post-outcome
aggregates не используются.

Feature contract фиксирует имена, порядок, типы и preprocessing. Изменение
contract требует новой candidate lineage и отдельной evaluation; документация
не может расширять список поддерживаемых признаков.

Строки feature table не являются независимыми samples, если относятся к одному
episode или capture origin. Поэтому evidence использует group-aware separation.
