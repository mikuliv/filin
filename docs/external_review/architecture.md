# Архитектура внешней проверки

Процесс разделён на три плоскости:

1. Data plane содержит blind PCAP inputs, отдельные namespaces predictions и
   labels. Labels недоступны inference component.
2. Commitment plane фиксирует dataset, labels, candidate, evaluator и
   predictions canonical SHA-256 commitments.
3. Review plane проверяет package manifest, role attestations, chronology и
   результат frozen evaluator.

Review overview и reproducibility package не содержат model binary. Runtime-only
trial package может получить проверенную копию candidate artifact только после
сверки hash. Backend, Internet, published ports, notifications и automatic
actions отсутствуют.
