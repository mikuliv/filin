# Границы доверия

Основные границы:

- input и labels разделены;
- candidate, protocol и evaluator read-only после commitment;
- inference не имеет доступа к labels;
- runtime package не имеет внешнего маршрута;
- backend отсутствует в current execution path;
- raw evidence отделено от tracked aggregate reports;
- result approval отделено от trial operation.

Validators работают fail-safe: unknown file, commitment mismatch, path
traversal, secret/privacy finding или chronology violation отклоняют package или
trial. SHA-256 commitment подтверждает целостность, но не является цифровой
подписью и не доказывает правовой статус данных.
