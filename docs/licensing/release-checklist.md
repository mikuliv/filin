# Контрольный список распространяемого состава

1. `python -m tools.licensing.validate_all --strict` завершён без ошибок.
2. `review_required_file_count`, `unknown_license_file_count` и `unassigned_file_count` равны нулю.
3. Protected hashes и baseline серверная часть/candidate совпадают.
4. Профиль `source-core` не содержит images, PCAP, models, Наборы данных, среда выполнения DB, `.env` или secrets.
5. Notices и три SBOM регенерированы и не содержат абсолютных путей/секретов.
6. Positive и negative Кампании прошли; отрицательные проверки выполнялись только во временных копиях.
7. Документационные validators, console verification, Проверка компиляции и pytest прошли.
8. Push выполняется только владельцем после просмотра итогового Коммит.

