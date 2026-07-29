"""Русские подписи стабильных машинных статусов лабораторной консоли."""
from __future__ import annotations

STATUS_LABELS = {
    "failed_validation": "Проверка не пройдена",
    "role_separated_blind": "Слепая проверка с разделением ролей",
    "not_comparable": "Запуски несопоставимы",
    "conditionally_comparable": "Сопоставимы с ограничениями",
    "comparable": "Сопоставимы",
    "admitted_to_separate_validation": "Допущено к отдельной проверке",
    "closed_without_candidate_decision": "Закрыто без решения о кандидате",
    "runtime_only": "Только в среде выполнения",
    "prediction_frozen": "Пакет прогнозов зафиксирован",
    "not_started": "Не начато",
    "in_review": "На рассмотрении",
    "completed": "Завершено",
    "running": "Выполняется",
    "failed": "Завершено с ошибкой",
    "passed": "Пройдено",
    "rejected": "Отклонено",
    "frozen": "Зафиксирован",
    "clean": "Без изменений",
    "queued": "Ожидает запуска",
    "pending": "Ожидает проверки",
    "succeeded": "Завершено успешно",
    "cancelled": "Отменено",
    "interrupted": "Прервано",
    "resumable": "Можно восстановить",
    "reproducible": "Воспроизводимо",
    "not_reproducible": "Не воспроизводится",
    "not_checked": "Не проверено",
    "reviewed": "Рассмотрено",
    "not_reviewed": "Не рассмотрено",
    "needs_evidence": "Требуются сведения",
    "unresolved": "Не решено",
    "equally_supported": "Опора одинакова",
    "left_better_supported": "Левая гипотеза поддержана лучше",
    "right_better_supported": "Правая гипотеза поддержана лучше",
    "insufficient_evidence": "Недостаточно сведений",
    "source_confirmed": "Источник подтверждён",
    "indeterminate": "Неопределённо",
    "reviewed_without_determination": "Рассмотрено без окончательного определения",
    "verified": "Целостность подтверждена",
    "basic": "Начальная",
    "intermediate": "Средняя",
    "advanced": "Повышенная",
    "expert": "Экспертная",
    "normal": "Нормальная активность",
    "auth_failures": "Ошибки аутентификации",
    "clock_domain_mismatch": "Несогласованные источники времени",
    "delivery_anomaly": "Аномалия доставки",
    "duplicate_delivery": "Повторная доставка",
    "equal_support": "Равная поддержка",
    "incomplete_evidence": "Неполные сведения",
    "low_rate_dos": "Низкоинтенсивная нагрузка",
    "mixed": "Смешанный случай",
    "port_scan": "Сканирование портов",
    "web_probe": "Разведочные веб-запросы",
    "beacon": "Маячковая активность",
}


def status_label(value: object) -> str:
    """Возвращает русскую подпись, не изменяя исходное машинное значение."""
    text = str(value)
    return STATUS_LABELS.get(text, text)


def status_display(value: object) -> str:
    """Показывает русскую подпись и отделённый от неё точный идентификатор."""
    text = str(value)
    label = status_label(text)
    return label if label == text else f"{label} (`{text}`)"
