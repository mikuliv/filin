# staging_transport_security_v1

Обе внутренние границы используют только TLS 1.3 и mTLS с разными синтетическими CA. Проверяются SAN, EKU, trust, срок, отзыв и fingerprint. Plaintext, downgrade, слабые suites и отсутствующий client certificate отклоняются. Закрытые ключи находятся только в gitignored runtime-каталоге.
