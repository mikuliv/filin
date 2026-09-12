"""Реестр первой исполняемой волны и его межконтрактная проверка."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from tools.vnext.contracts import CONTRACT_ROOT, ContractError, load_json, validate_json_schema_instance
from tools.vnext.telemetry import GROUND_TRUTH_KEYS, load_vnext_catalogs, validate_scenario_definition, verify_digest, with_digest

from .runtime import GENERATORS, assert_generator_family_independence


REGISTRY_PATH = CONTRACT_ROOT / "wave1_scenario_registry_v1.json"
FORBIDDEN_MARKERS = ["filin", "scenario_", "generator_", "taxonomy_node_id", "attack_label"]
GROUND_POLICY = {"storage_class": "external_sealed_ground_truth", "observable_access": "forbidden", "prediction_access": "forbidden"}


def build_generator_catalog() -> dict[str, Any]:
    """Строит каталог runtime-возможностей; исторические адаптеры остаются planned."""
    common = {"parameter_schema_ref": "filin://vnext/experimental_dimension_v1", "seed_policy": {"deterministic": True, "algorithm": "sha256_seeded_python_v1", "same_seed_same_realization": True}}
    def row(generator_id, ref, status, nodes, caps, telemetry, emitted, dimensions, limitation):
        return {"generator_id": generator_id, "implementation_ref": ref, "adapter_status": status,
                "supported_taxonomy_nodes": nodes, "required_environment_capabilities": caps,
                "required_telemetry": telemetry, **common, "emitted_observable_activity": emitted,
                "supported_dimensions": dimensions, "limitations": [limitation]}
    recon_nodes = ["malicious.reconnaissance.host_discovery", "malicious.reconnaissance.port_scanning"]
    credential_nodes = ["malicious.credential_abuse", "malicious.credential_abuse.brute_force", "malicious.credential_abuse.password_spraying"]
    beacon_nodes = ["malicious.command_and_control.beaconing"]
    rows = [
        row("wave1_recon_family_a", "tools.vnext.scenarios.runtime.ReconFamilyA", "implemented", recon_nodes, ["generic_tcp_services"], ["network.flow"], ["network.flow"], ["request_count", "scan_ordering", "spacing_ms"], "Только loopback disposable target."),
        row("wave1_recon_family_b", "tools.vnext.scenarios.runtime.ReconFamilyB", "implemented", recon_nodes, ["generic_tcp_services"], ["network.flow"], ["network.flow"], ["request_count", "scan_ordering", "spacing_ms"], "Независимая interleaved-реализация ограничена локальным стендом."),
        row("wave1_web_enumerator", "tools.vnext.scenarios.runtime.WebEnumerationGenerator", "implemented", ["malicious.reconnaissance.web_path_enumeration"], ["http_service"], ["network.flow"], ["network.flow", "http.request"], ["request_count", "spacing_ms"], "Использует небольшой безопасный словарь обычных путей."),
        row("wave1_credential_family_a", "tools.vnext.scenarios.runtime.CredentialFamilyA", "implemented", credential_nodes, ["http_service", "authentication_service"], ["auth.attempt"], ["http.request", "auth.attempt"], ["request_count", "account_count", "attempts_per_account", "source_count", "delay_model"], "Только вымышленные локальные учётные записи."),
        row("wave1_credential_family_b", "tools.vnext.scenarios.runtime.CredentialFamilyB", "implemented", credential_nodes, ["http_service", "authentication_service"], ["auth.attempt"], ["http.request", "auth.attempt"], ["request_count", "account_count", "attempts_per_account", "source_count", "delay_model"], "Round-robin реализация не создаёт независимые сетевые источники."),
        row("wave1_beacon_family_a", "tools.vnext.scenarios.runtime.BeaconFamilyA", "implemented", beacon_nodes, ["http_service", "http_callback"], ["network.flow", "http.request"], ["network.flow", "http.request"], ["request_count", "interval_ms", "jitter_ratio", "callback_protocol", "session_persistence"], "Интервалы сокращены для smoke-проверки."),
        row("wave1_beacon_family_b", "tools.vnext.scenarios.runtime.BeaconFamilyB", "implemented", beacon_nodes, ["http_service", "http_callback"], ["network.flow", "http.request"], ["network.flow", "http.request"], ["request_count", "interval_ms", "jitter_ratio", "callback_protocol", "session_persistence"], "Отдельная persistent-session реализация работает только по HTTP."),
        row("wave1_dns_callback_planned", "tools.vnext.scenarios.future.DnsCallbackGenerator", "planned", ["malicious.command_and_control.dns_c2"], ["dns_resolver"], ["network.flow", "dns.query"], ["dns.query"], ["request_count", "callback_protocol", "interval_ms"], "Нет честного локального DNS telemetry path."),
        row("wave1_benign_operations", "tools.vnext.scenarios.runtime.BenignOperationsGenerator", "implemented", ["benign.interactive.normal_navigation", "benign.operations.monitoring", "benign.security_testing", "benign.automation.api_polling", "benign.authentication", "benign.automation.synchronization"], ["http_service"], ["network.flow", "http.request", "auth.attempt"], ["network.flow", "http.request", "auth.attempt"], ["request_count", "scan_ordering", "spacing_ms", "interval_ms", "account_count", "attempts_per_account"], "Операционная логика отделена от malicious generators."),
        row("legacy_network_family_a_adapter", "lab.network_validation.generators.family_a.FamilyA", "planned", ["benign.interactive.normal_navigation", "malicious.reconnaissance.port_scanning", "malicious.reconnaissance.web_path_enumeration", "malicious.credential_abuse.brute_force", "malicious.command_and_control.beaconing", "malicious.impact_availability.application_pressure"], ["http_target", "tcp_target"], ["network.flow"], ["network.flow", "http.request"], ["request_count", "spacing_ms", "interval_ms", "jitter_ratio", "payload_size", "target_profile", "protocol_implementation"], "Исторический генератор не изменён; это только planned-адаптер."),
        row("legacy_network_family_b_adapter", "lab.network_validation.generators.family_b.FamilyB", "planned", ["benign.interactive.normal_navigation", "malicious.reconnaissance.port_scanning", "malicious.reconnaissance.web_path_enumeration", "malicious.credential_abuse.brute_force", "malicious.command_and_control.beaconing", "malicious.impact_availability.application_pressure"], ["http_target", "tcp_target"], ["network.flow"], ["network.flow", "http.request"], ["request_count", "spacing_ms", "interval_ms", "jitter_ratio", "payload_size", "target_profile", "protocol_implementation"], "Исторический генератор не изменён; это только planned-адаптер."),
    ]
    return with_digest({"schema_version": "generator_capability_v1", "registry_id": "generators_filin_vnext_v1", "status": "implemented", "generators": rows})


def _definition(
    scenario_id: str, purpose: str, status: str, node: str, variant: str,
    generators: list[str], required: list[str], expected: list[str], capabilities: list[str],
    dimensions: list[str], defaults: dict[str, Any], analogues: list[str], counterfactuals: list[str],
    observables: list[str], limitation: str,
) -> dict[str, Any]:
    constraints = {}
    for name in dimensions:
        if name in {"request_count", "account_count", "attempts_per_account", "source_count"}: constraints[name] = [1, 48]
        elif name == "scan_ordering": constraints[name] = ["ascending", "seeded", "interleaved"]
        elif name == "callback_protocol": constraints[name] = ["http", "dns"]
        elif name == "jitter_ratio": constraints[name] = [0, 0.5]
        else: constraints[name] = [0, 1000]
    value = {
        "schema_version": "scenario_definition_v2", "scenario_id": scenario_id, "purpose_ru": purpose, "status": status,
        "taxonomy_node_id": node, "scenario_variant": variant,
        "generator_requirements": {"allowed_generator_ids": generators, "implementation_separation_required": len(generators) > 1},
        "telemetry_expectations": {"required": required, "useful": [], "expected_event_types": expected},
        "environment_requirements": {"services": capabilities, "target_capabilities": capabilities},
        "parameter_constraints": constraints, "intensity_model": {"dimension_ids": dimensions, "default_profile": defaults},
        "expected_observable_behavior": observables, "forbidden_observable_fields": sorted(GROUND_TRUTH_KEYS),
        "forbidden_marker_patterns": FORBIDDEN_MARKERS, "counterfactual_refs": counterfactuals,
        "hard_benign_analogue_refs": analogues, "ground_truth_policy": GROUND_POLICY,
        "limitations": [limitation],
    }
    return with_digest(value)


def build_wave1_registry() -> dict[str, Any]:
    r_a, r_b, web = "wave1_recon_family_a", "wave1_recon_family_b", "wave1_web_enumerator"
    c_a, c_b = "wave1_credential_family_a", "wave1_credential_family_b"
    b_a, b_b, benign = "wave1_beacon_family_a", "wave1_beacon_family_b", "wave1_benign_operations"
    recon_obs = ["Короткие попытки TCP-соединений к нескольким портам локальной цели."]
    auth_obs = ["Повторяющиеся результаты аутентификации для одной или нескольких учётных записей."]
    beacon_obs = ["Повторяющиеся небольшие HTTP-запросы к стабильной локальной конечной точке."]
    rows = [
        _definition("scenario_host_discovery", "Проверить обнаружение доступности локального узла через реальные соединения.", "implemented", "malicious.reconnaissance.host_discovery", "host_discovery", [r_a, r_b], ["network.flow"], ["network.flow"], ["generic_tcp_services"], ["request_count", "scan_ordering"], {"request_count": 3, "scan_ordering": "seeded"}, ["scenario_service_monitoring"], ["scenario_service_monitoring"], recon_obs, "Один loopback-узел не моделирует сетевую топологию."),
        _definition("scenario_service_discovery", "Получить наблюдаемую картину проверки набора локальных сервисов.", "implemented", "malicious.reconnaissance.port_scanning", "service_discovery", [r_a, r_b], ["network.flow"], ["network.flow"], ["generic_tcp_services"], ["request_count", "scan_ordering"], {"request_count": 6, "scan_ordering": "seeded"}, ["scenario_approved_scanner"], ["scenario_approved_scanner"], recon_obs, "Техническая проверка не устанавливает злонамеренное намерение."),
        _definition("scenario_sequential_port_scan", "Выполнить последовательную проверку локальных портов.", "implemented", "malicious.reconnaissance.port_scanning", "sequential_port_scan", [r_a], ["network.flow"], ["network.flow"], ["generic_tcp_services"], ["request_count", "scan_ordering"], {"request_count": 6, "scan_ordering": "ascending"}, ["scenario_approved_scanner"], ["scenario_approved_scanner"], recon_obs, "Малый локальный диапазон служит только smoke-проверке."),
        _definition("scenario_randomized_port_scan", "Выполнить детерминированно перемешанную проверку локальных портов.", "implemented", "malicious.reconnaissance.port_scanning", "randomized_port_scan", [r_b], ["network.flow"], ["network.flow"], ["generic_tcp_services"], ["request_count", "scan_ordering"], {"request_count": 6, "scan_ordering": "seeded"}, ["scenario_approved_scanner"], ["scenario_approved_scanner"], recon_obs, "Порядок детерминирован seed и не является экспериментальной выборкой."),
        _definition("scenario_sparse_port_scan", "Проверить разреженный профиль локальных соединений в безопасном сокращённом времени.", "implemented", "malicious.reconnaissance.port_scanning", "sparse_port_scan", [r_b], ["network.flow"], ["network.flow"], ["generic_tcp_services"], ["request_count", "spacing_ms"], {"request_count": 3, "spacing_ms": 2}, ["scenario_service_monitoring"], ["scenario_service_monitoring"], recon_obs, "Smoke-профиль с миллисекундными интервалами не подтверждает low-rate detection."),
        _definition("scenario_web_path_enumeration", "Проверить реальные ответы на набор обычных веб-путей.", "implemented", "malicious.reconnaissance.web_path_enumeration", "web_path_enumeration", [web], ["network.flow"], ["network.flow", "http.request"], ["http_service"], ["request_count", "spacing_ms"], {"request_count": 6, "spacing_ms": 0}, ["scenario_legitimate_bulk_requests"], ["scenario_legitimate_bulk_requests"], ["Серия HTTP-запросов к существующим и отсутствующим путям."], "Небольшой словарь не представляет полноразмерное перечисление."),
        _definition("scenario_credential_brute_force", "Создать концентрированную серию неуспешных входов на малом наборе учётных записей.", "implemented", "malicious.credential_abuse.brute_force", "brute_force", [c_a, c_b], ["auth.attempt"], ["http.request", "auth.attempt"], ["http_service", "authentication_service"], ["request_count", "account_count", "attempts_per_account"], {"request_count": 8, "account_count": 1, "attempts_per_account": 4}, ["scenario_auth_misconfiguration"], ["scenario_auth_misconfiguration"], auth_obs, "Пароли не сохраняются в сырой телеметрии."),
        _definition("scenario_password_spraying", "Создать малое число неуспешных входов по нескольким учётным записям.", "implemented", "malicious.credential_abuse.password_spraying", "password_spraying", [c_a, c_b], ["auth.attempt"], ["http.request", "auth.attempt"], ["http_service", "authentication_service"], ["request_count", "account_count", "attempts_per_account"], {"request_count": 8, "account_count": 4, "attempts_per_account": 1}, ["scenario_user_password_mistakes"], ["scenario_user_password_mistakes"], auth_obs, "Малый стенд не моделирует распределённую идентичность пользователей."),
        _definition("scenario_credential_stuffing", "Воспроизвести распределённый по учётным записям профиль проверок разных пар реквизитов.", "implemented", "malicious.credential_abuse", "credential_stuffing", [c_a, c_b], ["auth.attempt"], ["http.request", "auth.attempt"], ["http_service", "authentication_service"], ["request_count", "account_count", "attempts_per_account"], {"request_count": 8, "account_count": 4, "attempts_per_account": 1}, ["scenario_user_password_mistakes"], ["scenario_user_password_mistakes"], auth_obs, "Используются только вымышленные локальные реквизиты."),
        _definition("scenario_distributed_credential_guessing", "Зарезервировать корректную проверку нескольких независимых источников.", "planned", "malicious.credential_abuse", "distributed_credential_guessing", [c_b], ["auth.attempt"], ["auth.attempt"], ["http_service", "authentication_service", "multiple_source_identities"], ["request_count", "source_count"], {"request_count": 8, "source_count": 2}, ["scenario_user_password_mistakes"], ["scenario_user_password_mistakes"], auth_obs, "Текущий loopback-стенд не даёт честных независимых источников."),
        _definition("scenario_periodic_beacon", "Создать повторяющиеся локальные HTTP-обращения с постоянной структурой.", "implemented", "malicious.command_and_control.beaconing", "periodic_beacon", [b_a, b_b], ["network.flow", "http.request"], ["network.flow", "http.request"], ["http_service", "http_callback"], ["request_count", "interval_ms"], {"request_count": 4, "interval_ms": 2}, ["scenario_legitimate_periodic_callback", "scenario_health_checks"], ["scenario_legitimate_periodic_callback"], beacon_obs, "Сокращённые интервалы предназначены только для smoke-проверки."),
        _definition("scenario_jittered_beacon", "Создать детерминированный callback-профиль с изменяемым интервалом.", "implemented", "malicious.command_and_control.beaconing", "jittered_beacon", [b_a, b_b], ["network.flow", "http.request"], ["network.flow", "http.request"], ["http_service", "http_callback"], ["request_count", "interval_ms", "jitter_ratio"], {"request_count": 4, "interval_ms": 2, "jitter_ratio": 0.25}, ["scenario_api_polling"], ["scenario_api_polling"], beacon_obs, "Runtime не воспроизводит длительные интервалы в инженерном тесте."),
        _definition("scenario_low_frequency_callback", "Проверить повторяющиеся обращения, концептуально разделённые увеличенным интервалом.", "implemented", "malicious.command_and_control.beaconing", "low_frequency_callback", [b_a, b_b], ["network.flow", "http.request"], ["network.flow", "http.request"], ["http_service", "http_callback"], ["request_count", "interval_ms"], {"request_count": 3, "interval_ms": 5}, ["scenario_service_monitoring"], ["scenario_service_monitoring"], beacon_obs, "Smoke-тест не валидирует наблюдаемость настоящих многочасовых интервалов."),
        _definition("scenario_http_callback", "Проверить callback-поведение через локальный HTTP-сервис.", "implemented", "malicious.command_and_control.beaconing", "http_callback", [b_a, b_b], ["network.flow", "http.request"], ["network.flow", "http.request"], ["http_service", "http_callback"], ["request_count", "callback_protocol"], {"request_count": 4, "callback_protocol": "http"}, ["scenario_api_polling"], ["scenario_api_polling"], beacon_obs, "HTTP без TLS выбран только для изолированного стенда."),
        _definition("scenario_dns_callback", "Зарезервировать DNS-callback после появления честного DNS telemetry path.", "planned", "malicious.command_and_control.dns_c2", "dns_callback", ["wave1_dns_callback_planned"], ["network.flow", "dns.query"], ["dns.query"], ["dns_resolver"], ["request_count", "callback_protocol"], {"request_count": 4, "callback_protocol": "dns"}, ["scenario_legitimate_periodic_callback"], ["scenario_legitimate_periodic_callback"], ["Повторяющиеся DNS-запросы к стабильному имени."], "Локальный DNS-сборщик отсутствует; исполнение закрыто."),
        _definition("scenario_normal_navigation", "Выполнить обычную последовательность переходов по локальным веб-ресурсам.", "implemented", "benign.interactive.normal_navigation", "normal_navigation", [benign], ["http.request"], ["network.flow", "http.request"], ["http_service"], ["request_count", "spacing_ms"], {"request_count": 4, "spacing_ms": 1}, ["scenario_web_path_enumeration"], ["scenario_web_path_enumeration"], ["Последовательные успешные запросы к небольшому набору обычных веб-путей."], "Короткий технический маршрут не представляет пользовательскую сессию."),
        _definition("scenario_service_monitoring", "Выполнить разрешённый контроль доступности известных сервисов.", "implemented", "benign.operations.monitoring", "service_monitoring", [benign], ["network.flow"], ["network.flow"], ["generic_tcp_services"], ["request_count", "spacing_ms"], {"request_count": 3, "spacing_ms": 2}, ["scenario_host_discovery", "scenario_sparse_port_scan"], ["scenario_sparse_port_scan"], recon_obs, "Намерение хранится только во внешней разметке."),
        _definition("scenario_approved_scanner", "Выполнить разрешённую локальную инвентаризацию сервисов.", "implemented", "benign.security_testing", "approved_scanner", [benign], ["network.flow"], ["network.flow"], ["generic_tcp_services"], ["request_count", "scan_ordering"], {"request_count": 6, "scan_ordering": "ascending"}, ["scenario_service_discovery"], ["scenario_service_discovery"], recon_obs, "Сетевой профиль намеренно похож на scan-like traffic."),
        _definition("scenario_api_polling", "Выполнить штатный опрос локального API.", "implemented", "benign.automation.api_polling", "api_polling", [benign], ["http.request"], ["network.flow", "http.request"], ["http_service"], ["request_count", "interval_ms"], {"request_count": 4, "interval_ms": 2}, ["scenario_http_callback", "scenario_jittered_beacon"], ["scenario_http_callback"], beacon_obs, "Инженерный прогон не моделирует бизнес-контекст API."),
        _definition("scenario_health_checks", "Выполнить штатные проверки работоспособности локального сервиса.", "implemented", "benign.operations.monitoring", "health_checks", [benign], ["http.request"], ["network.flow", "http.request"], ["http_service"], ["request_count", "interval_ms"], {"request_count": 4, "interval_ms": 2}, ["scenario_periodic_beacon"], ["scenario_periodic_beacon"], beacon_obs, "Короткая длительность достаточна только для pipeline smoke-теста."),
        _definition("scenario_legitimate_periodic_callback", "Выполнить разрешённый периодический callback приложения.", "implemented", "benign.automation.api_polling", "legitimate_periodic_callback", [benign], ["http.request"], ["network.flow", "http.request"], ["http_service", "http_callback"], ["request_count", "interval_ms"], {"request_count": 4, "interval_ms": 2}, ["scenario_periodic_beacon"], ["scenario_periodic_beacon"], beacon_obs, "Наблюдаемые признаки частично совпадают с beaconing."),
        _definition("scenario_auth_misconfiguration", "Воспроизвести повторные отказы из-за неверной настройки штатного клиента.", "implemented", "benign.authentication", "auth_misconfiguration", [benign], ["auth.attempt"], ["http.request", "auth.attempt"], ["http_service", "authentication_service"], ["request_count", "attempts_per_account"], {"request_count": 3, "attempts_per_account": 3}, ["scenario_credential_brute_force"], ["scenario_credential_brute_force"], auth_obs, "Причина отказа задана внешним контекстом, не observable label."),
        _definition("scenario_user_password_mistakes", "Воспроизвести единичные ошибки пользователя при вводе пароля.", "implemented", "benign.authentication", "password_mistakes", [benign], ["auth.attempt"], ["http.request", "auth.attempt"], ["http_service", "authentication_service"], ["request_count", "attempts_per_account"], {"request_count": 2, "attempts_per_account": 1}, ["scenario_password_spraying", "scenario_credential_stuffing"], ["scenario_password_spraying"], auth_obs, "Малый стенд не содержит поведенческого профиля реального пользователя."),
        _definition("scenario_legitimate_bulk_requests", "Выполнить разрешённую пакетную выборку нескольких локальных ресурсов.", "implemented", "benign.automation.synchronization", "bulk_multi_request", [benign], ["http.request"], ["network.flow", "http.request"], ["http_service"], ["request_count", "spacing_ms"], {"request_count": 6, "spacing_ms": 0}, ["scenario_web_path_enumeration"], ["scenario_web_path_enumeration"], ["Серия запросов к нескольким обычным ресурсам."], "Назначение операции не выводится только из сетевого fan-out."),
    ]
    return with_digest({"schema_version": "wave1_scenario_registry_v1", "registry_id": "filin_vnext_wave1", "status": "implemented", "scenarios": rows})


def load_wave1_registry() -> dict[str, Any]:
    return load_json(REGISTRY_PATH)


def validate_wave1_registry(value: dict[str, Any] | None = None) -> dict[str, Any]:
    value = deepcopy(value or load_wave1_registry()); validate_json_schema_instance("wave1_scenario_registry_v1.schema.json", value); verify_digest(value)
    catalogs = load_vnext_catalogs(); rows = value["scenarios"]; by_id = {row["scenario_id"]: row for row in rows}
    if len(by_id) != len(rows): raise ContractError("duplicate wave 1 scenario ID")
    for row in rows:
        validate_scenario_definition(row, catalogs["taxonomy"], catalogs["generators"], catalogs["requirements"])
        if row["status"] == "experimentally_validated": raise ContractError("smoke tests are not experimental validation")
        refs = set(row["counterfactual_refs"] + row["hard_benign_analogue_refs"])
        if refs - set(by_id): raise ContractError("unresolved counterfactual or analogue reference")
        if row["status"] == "implemented" and set(row["generator_requirements"]["allowed_generator_ids"]) - set(GENERATORS): raise ContractError("implemented scenario has no runtime generator")
        for dimension, default in row["intensity_model"]["default_profile"].items():
            constraint = row["parameter_constraints"].get(dimension)
            if not isinstance(constraint, list) or len(constraint) < 2: raise ContractError("dimension constraint is missing")
            if isinstance(default, (int, float)) and all(isinstance(item, (int, float)) for item in constraint[:2]):
                if not constraint[0] <= default <= constraint[1]: raise ContractError("dimension default is outside its range")
            elif default not in constraint: raise ContractError("categorical dimension default is not allowed")
        observable_text = " ".join(row["expected_observable_behavior"]).lower()
        if any(marker.lower() in observable_text for marker in row["forbidden_marker_patterns"]): raise ContractError("forbidden marker appears in observable description")
    for ids in (["wave1_recon_family_a", "wave1_recon_family_b"], ["wave1_credential_family_a", "wave1_credential_family_b"], ["wave1_beacon_family_a", "wave1_beacon_family_b"]):
        assert_generator_family_independence(ids)
    return value
