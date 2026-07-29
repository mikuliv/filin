"""Контекстно исправляет известные англоязычные конструкции в редактируемых документах."""
from __future__ import annotations

import re
from pathlib import Path

from tools.docs.validate_russian_narrative import ROOT, classify, protected_paths, tracked_paths

PHRASES = {
    "provenance side-by-side": "параллельное сопоставление происхождения",
    "independent human review": "независимая человеческая проверка",
    "admitted to separate validation": "допущено к отдельной проверке",
    "closed without candidate decision": "закрыто без решения о кандидате",
    "role-separated blind procedure": "слепая проверка с разделением ролей",
    "role-separated procedure": "процедура с разделением ролей",
    "role-separated": "с разделением ролей",
    "frozen inference": "зафиксированное применение модели",
    "blind procedure": "слепая проверка",
    "internal screening": "предварительная внутренняя проверка",
    "admission gate": "обязательные критерии допуска",
    "acceptance gate": "обязательные критерии приёмки",
    "comparability gate": "проверка сопоставимости",
    "overlap gate": "проверка отсутствия пересечений",
    "blindness gate": "проверка сохранения слепого режима",
    "prediction package": "пакет прогнозов",
    "prediction commitment": "предварительная фиксация пакета прогнозов",
    "label commitment": "предварительная фиксация эталонной разметки",
    "label unlock": "раскрытие эталонной разметки",
    "control pack": "контрольный набор",
    "runtime-only": "только в среде выполнения",
    "machine-readable": "машиночитаемый",
    "human-readable": "человекочитаемый",
    "source artifact": "исходный артефакт",
    "active candidate": "действующий кандидат",
    "candidate registry": "реестр кандидатов",
    "candidate proposal": "предложение кандидата",
    "evidence bundle": "комплект подтверждающих материалов",
    "dry run": "пробный запуск без выполнения",
    "allowlist dataset": "набор данных из перечня разрешённых значений",
    "semantic fingerprint": "семантический отпечаток",
    "review overlay": "изменяемый слой рассмотрения",
    "production backend": "промышленная серверная часть",
    "backend integration": "подключение к серверной части",
    "shadow mode": "пассивное наблюдение",
    "forced winner": "принудительный выбор победителя",
    "test oracle": "тестовый эталон",
    "read-only": "только для чтения",
    "source of truth": "авторитетный источник",
    "semantic SHA": "семантическая контрольная сумма",
    "blind validation": "слепая проверка",
}
WORDS = {
    "workflow": "порядок работы", "runner": "модуль запуска", "holdout": "отложенная контрольная выборка",
    "screening": "предварительная проверка", "backend": "серверная часть", "production": "промышленная эксплуатация",
    "proposal": "предложение кандидата", "reviewer": "эксперт", "review": "рассмотрение",
    "evidence": "подтверждающие материалы", "runtime": "среда выполнения", "overlay": "изменяемый слой",
    "registry": "реестр", "export": "экспорт", "current": "текущий", "historical": "исторический",
    "redirect": "перенаправление", "recovery": "восстановление", "provenance": "происхождение",
    "lineage": "история происхождения", "validation": "проверка", "evaluation": "оценка",
    "metrics": "показатели", "gaps": "разрывы", "hypotheses": "гипотезы", "timeline": "временная последовательность",
    "dataset": "набор данных", "split": "разбиение", "recipe": "рецепт", "claim": "утверждение",
    "scope": "область применимости", "ranking": "ранжирование", "consumer": "потребитель",
    "versioned": "версионированный", "feature": "признак", "model": "модель", "artifact": "артефакт",
    "manifest": "манифест", "bundle": "комплект",
}
MIXED = {
    "frozen-пакет": "зафиксированный пакет", "frozen-материал": "неизменяемый материал",
    "blind-процедура": "слепая проверка", "blind-проверка": "слепая проверка",
    "proposal-контур": "контур предложений кандидата", "proposal-пакет": "пакет предложения кандидата",
    "Python-модуль": "модуль Python", "offline-режим": "автономный режим",
    "offline-профиль": "автономный профиль", "runtime-каталог": "каталог среды выполнения",
    "review-сессия": "сеанс рассмотрения", "production-контур": "промышленный контур",
}
PREFIXES = {
    "Docker": "Docker", "HTTP": "HTTP", "GPL": "GPL", "Markdown": "Markdown", "Python": "Python",
    "DNS": "DNS", "Git": "Git", "VMware": "VMware", "Sigma": "Sigma", "YAML": "YAML", "SPDX": "SPDX",
    "API": "API", "JSON": "JSON", "GET": "GET", "POST": "POST", "SSH": "SSH", "FastAPI": "FastAPI",
    "Zeek": "Zeek", "Windows": "Windows", "GitHub": "GitHub", "PCAP": "PCAP", "README": "README",
    "HTML": "HTML", "WAL": "WAL", "DoS": "DoS", "ML": "машинного обучения",
    "SQLite": "SQLite", "URL": "URL", "JSONL": "JSONL", "MPL": "MPL", "CI": "CI",
    "SaaS": "SaaS", "Evergreen": "Evergreen", "Botnet": "Botnet", "Audit": "аудита",
}
LOWER_PREFIXES = {
    "runtime": "среды выполнения", "attack": "атак", "connect": "соединения", "web": "веб",
    "beacon": "маячкового обмена", "mock": "имитации", "payload": "полезной нагрузки", "benign": "безопасного поведения",
    "regression": "регрессии", "offline": "автономного режима", "production": "промышленной эксплуатации",
    "tracked": "отслеживаемый", "metadata": "метаданных", "replay": "воспроизведения",
    "provenance": "происхождения", "development": "разработки", "evidence": "подтверждающих материалов",
    "manifest": "манифеста", "migration": "миграции", "holdout": "отложенной выборки", "preflight": "предварительной проверки",
    "baseline": "исходного уровня", "session": "сеанса", "upstream": "исходного проекта", "protected": "защищённый",
    "external": "внешнего", "email": "электронной почты", "readiness": "готовности", "approved": "одобренный",
    "privacy": "конфиденциальности", "install": "установки", "resume": "возобновления", "probe": "проверки",
    "flow": "потока", "natural": "естественного поведения", "nginx": "nginx", "mutable": "изменяемый",
    "vendor": "поставщика", "rehearsal": "репетиции", "resolved": "разрешённый", "campaign": "кампании",
    "shell": "командной оболочки", "sensor": "датчика", "smoke": "дымовой проверки", "maintenance": "обслуживания",
}
HEADINGS = {
    "Guided wizard": "Пошаговая настройка", "Label unlock": "Раскрытие эталонной разметки",
    "Blindness gate": "Проверка сохранения слепого режима", "Acceptance gate": "Обязательные критерии приёмки",
    "Prediction commitments": "Предварительная фиксация пакетов прогнозов", "Overlap": "Пересечения",
    "Checklist": "Контрольный список", "Comparison ID": "Идентификатор сопоставления",
    "Semantic ID": "Семантический идентификатор", "Plan SHA": "Контрольная сумма плана",
    "Byte SHA": "Побайтовая контрольная сумма", "Verifier": "Средство проверки",
    "Exit code": "Код завершения", "Quality gates": "Обязательные проверки качества",
    "Delivery order": "Порядок доставки", "Protocol revision": "Редакция протокола",
    "Event contract": "Контракт события", "Candidate ID": "Идентификатор кандидата",
    "Precision": "Точность", "Recall": "Полнота", "Redaction": "Скрытие чувствительных данных",
    "passed": "пройдено", "failed": "ошибка", "completed": "завершено", "interrupted": "прервано",
    "skipped": "пропущено", "warnings": "предупреждения", "Frozen": "Зафиксировано",
    "Collectors": "Сборщики", "CSV collector": "Сборщик CSV", "Suricata collector": "Сборщик Suricata",
    "Zeek collector": "Сборщик Zeek", "Datasets": "Наборы данных", "Detection pipeline": "Конвейер обнаружения",
    "Stateful episode processing": "Обработка эпизодов с состоянием", "Documentation Maintenance v2": "Обслуживание документации v2",
    "Front matter": "Служебный заголовок", "Generated documents": "Генерируемые документы",
    "Stage documentation": "Документация этапа", "Compileall": "Проверка компиляции",
    "REUSE compliance": "Соответствие REUSE", "Storage pressure": "Недостаток места хранения",
    "Invalidation": "Признание результата недействительным", "GPU": "Графический ускоритель",
    "Third-party dependency notices": "Уведомления о сторонних зависимостях", "Campaigns": "Кампании",
    "Control API": "Управляющий программный интерфейс", "Robustness laboratory": "Лаборатория устойчивости",
    "Passive event contract": "Контракт пассивного события", "Allowlist": "Перечень разрешённых значений",
    "Blindness": "Слепой режим", "JSON": "Файлы JSON", "Commit": "Коммит",
    "Timeout": "Ограничение времени", "PID": "Идентификатор процесса",
}


def replace_plain(text: str) -> str:
    for source, target in HEADINGS.items():
        text = re.sub(rf"(?<![\w`]){re.escape(source)}(?![\w`])", target, text, flags=re.I)
    for source, target in sorted(PHRASES.items(), key=lambda item: -len(item[0])):
        text = re.sub(rf"(?i)(?<![\w`]){re.escape(source)}(?![\w`])", target, text)
    for source, target in MIXED.items():
        text = re.sub(re.escape(source), target, text, flags=re.I)
    for source, target in PREFIXES.items():
        text = re.sub(rf"\b{re.escape(source)}-([А-Яа-яЁё][А-Яа-яЁё-]*)", rf"\1 {target}", text)
    for source, target in LOWER_PREFIXES.items():
        text = re.sub(rf"(?i)\b{re.escape(source)}-([А-Яа-яЁё][А-Яа-яЁё-]*)", rf"\1 {target}", text)
    text = re.sub(r"\bв-Git\b", "в Git", text)
    text = re.sub(r"\b([А-Яа-яЁё]+)-status\b", r"состояние \1", text, flags=re.I)
    text = re.sub(r"\b([А-Яа-яЁё]+)-snapshot\b", r"снимок \1", text, flags=re.I)
    text = re.sub(r"\b([А-Яа-яЁё]+)-based\b", r"основанный на \1", text, flags=re.I)
    text = re.sub(r"\b([А-Яа-яЁё]+)-required\b", r"требующий \1", text, flags=re.I)
    text = re.sub(r"\b([А-Яа-яЁё]+)-only\b", r"только \1", text, flags=re.I)
    text = re.sub(r"(?i)\bblind-([А-Яа-яЁё][А-Яа-яЁё-]*)", r"слепая \1", text)
    for source, target in WORDS.items():
        text = re.sub(rf"(?i)(?<![\w`]){re.escape(source)}(?![\w`])", target, text)
    return text


def transform_markdown(text: str) -> str:
    # Ранее ошибочно разделённые участки кода объединяются без изменения содержимого.
    nested = re.compile(r"`([^`\n]*)`([a-z][a-z0-9]*(?:_[a-z0-9]+)+)`([^`\n]*)`")
    while nested.search(text):
        text = nested.sub(r"`\1\2\3`", text)
    out = []
    in_fence = False
    for line in text.splitlines(keepends=True):
        if re.match(r"^\s*(```|~~~)", line):
            in_fence = not in_fence; out.append(line); continue
        if in_fence:
            out.append(line); continue
        parts = re.split(r"(`[^`\n]+`|https?://\S+|\]\([^)]+\))", line)
        rendered_parts = []
        for part in parts:
            if re.match(r"^`|^https?://|^\]\(", part):
                rendered_parts.append(part)
            else:
                value = replace_plain(part)
                value = re.sub(r"(?<![`\w])([a-z][a-z0-9]*(?:_[a-z0-9]+)+)(?![`\w])", r"`\1`", value)
                rendered_parts.append(value)
        rendered = "".join(rendered_parts)
        for literal, explanation in (("network_features_v2", "контракт сетевых признаков"), ("shadow_event_v2", "контракт пассивного события")):
            if f"`{literal}`" in rendered and not re.search(rf"[А-Яа-яЁё].*`{literal}`", rendered):
                rendered = rendered.replace(f"`{literal}`", f"{explanation} (`{literal}`)", 1)
        out.append(rendered)
    return "".join(out)


def transform_html(text: str) -> str:
    parts = re.split(r"(<[^>]+>|{{.*?}}|{%.*?%}|{#.*?#})", text, flags=re.S)
    rendered = []
    for part in parts:
        if part.startswith(("<", "{{", "{%", "{#")):
            rendered.append(part)
        else:
            value = transform_markdown(part)
            value = re.sub(r"`([a-z][a-z0-9]*(?:_[a-z0-9]+)+)`", r"<code>\1</code>", value)
            rendered.append(value)
    return "".join(rendered)


def transform_machine(text: str) -> str:
    pattern = re.compile(r"^(\s*(?:title|display_name|description|summary|message|rationale|limitation|operator_hint|reviewer_note|user_message)(?:_ru)?\s*[:=]\s*)(.*)$", re.M)
    return pattern.sub(lambda m: m.group(1) + replace_plain(m.group(2)), text)


def main() -> int:
    protected = protected_paths(ROOT)
    changed = []
    for path in tracked_paths(ROOT):
        kind, human = classify(path, protected)
        if not human or kind in {"frozen_evidence", "official_standard_text", "historical_document", "generated_document"}:
            continue
        target = ROOT / path
        try: text = target.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError): continue
        suffix = target.suffix.lower()
        if kind == "current_human_document": updated = transform_html(text) if suffix in {".html", ".jinja", ".j2"} else transform_markdown(text)
        elif kind == "current_machine_document": updated = transform_machine(text)
        elif path.startswith("lab_console/templates/"): updated = transform_html(text)
        else: continue
        if updated != text:
            target.write_text(updated, encoding="utf-8", newline="")
            changed.append(path)
    print(f"Исправлено файлов: {len(changed)}")
    for path in changed: print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
