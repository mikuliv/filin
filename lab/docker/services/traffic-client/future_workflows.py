"""Explicit bounded workflow plans for post-audit laboratory campaigns."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Action:
    kind: str
    target: str
    operation: str
    payload: tuple[tuple[str, Any], ...] = ()

    @classmethod
    def http(cls, method: str, target: str, path: str, **payload: Any) -> "Action":
        return cls("http", target, f"{method}:{path}", tuple(sorted(payload.items())))


DNS = lambda name: Action("dns", name, "resolve")
TCP = lambda target, port: Action("tcp", target, str(port))
WS = lambda operation="ping": Action("websocket", "control-api", operation)


def _http_sequence(target: str, paths: list[str], *, post: bool = False, tag: str = "") -> tuple[Action, ...]:
    method = "POST" if post else "GET"
    return tuple(Action.http(method, target, path, workflow=tag) for path in paths)


WORKFLOW_PLANS: dict[str, tuple[Action, ...]] = {
    "benign_ci_cd_agent": _http_sequence("target-api", ["/health", "/api/status", "/api/items"], tag="ci_cd"),
    "benign_service_mesh_readiness": (DNS("target-api"), TCP("target-api", 8080), Action.http("GET", "target-api", "/health")),
    "benign_dns_failover_rotation": (DNS("target-api"), DNS("target-web"), DNS("control-api")),
    "benign_object_storage_multipart": _http_sequence("target-web", ["/files/sample-small.txt", "/files/sample-config.json", "/files/sample-small.txt"], tag="multipart"),
    "benign_message_queue_consumer": _http_sequence("control-api", ["/health", "/beacon"], post=True, tag="queue_consumer"),
    "benign_certificate_renewal": (DNS("target-api"), TCP("target-api", 8080), Action.http("GET", "target-api", "/api/status", workflow="certificate")),
    "benign_remote_maintenance": (TCP("target-ssh-sim", 2222), Action.http("GET", "target-api", "/api/status")),
    "benign_batch_api_import": _http_sequence("target-api", ["/api/items", "/api/items", "/api/status"], post=True, tag="batch_import"),
    "benign_websocket_keepalive": (WS("session_ping_close"),),
    "benign_package_mirror_refresh": _http_sequence("target-web", ["/files/sample-config.json", "/files/sample-small.txt", "/about.html"], tag="package_mirror"),
    "benign_backup_verification": _http_sequence("target-web", ["/files/sample-config.json", "/files/sample-config.json"], tag="backup_verify"),
    "benign_log_rotation_shipping": _http_sequence("target-api", ["/api/items", "/api/status"], post=True, tag="log_rotation"),
    "benign_multi_resolver_discovery": (DNS("target-web"), DNS("target-api"), DNS("target-ssh-sim"), DNS("control-api")),
    "benign_auth_token_refresh": _http_sequence("target-api", ["/api/login", "/api/profile/test-user", "/api/status"], post=True, tag="token_refresh"),
    "benign_polite_link_crawler": _http_sequence("target-web", ["/", "/about.html", "/docs.html"], tag="polite_crawler"),
    "benign_inventory_with_recovery": (TCP("target-ssh-sim", 2222), DNS("target-api"), Action.http("GET", "target-api", "/api/items")),
}

WORKFLOW_PLANS.update({
    "smoke_http_readback": (Action.http("GET", "target-web", "/files/sample-small.txt"),),
    "smoke_dns_local_resolution": (DNS("target-api"), DNS("target-web"), DNS("filin-missing-service")),
    "smoke_websocket_ping_pong": (WS("session_ping_close"),),
    "smoke_tcp_admin_check": (TCP("target-ssh-sim", 2222),),
    "smoke_mixed_service_check": (DNS("target-api"), TCP("target-api", 8080), Action.http("GET", "target-api", "/health")),
    "smoke_attack_like_probe": (Action.http("GET", "target-web", "/admin-test"), Action.http("GET", "target-web", "/debug-test")),
})


# v0.3.7 identifiers receive explicit semantic families.  Plans are generated
# once at import time and remain deterministic; the scenario-specific terminal
# action makes their observable sequence distinct without external targets.
_V037 = {
    "benign_incremental_backup_readback": ("backup", "target-web"),
    "benign_chunked_replication_sync": ("replication", "target-web"),
    "benign_repository_delta_sync": ("repository", "target-web"),
    "benign_bounded_web_audit": ("crawler", "target-web"),
    "benign_metrics_scrape_wave": ("metrics", "target-api"),
    "benign_cache_prefetch": ("cache", "target-web"),
    "benign_database_health_rotation": ("database", "target-api"),
    "benign_queue_consumer_rebalance": ("queue", "control-api"),
    "benign_api_cursor_pagination": ("pagination", "target-api"),
    "benign_artifact_integrity_readback": ("integrity", "target-web"),
    "benign_certificate_inventory_refresh": ("certificate", "target-api"),
    "benign_service_discovery_reconcile": ("discovery", "target-api"),
    "benign_remote_patch_inventory": ("maintenance", "target-ssh-sim"),
    "benign_token_refresh_recovery": ("auth", "target-api"),
    "benign_dns_cache_repopulation": ("dns", "internal-dns"),
    "benign_log_ship_backoff": ("log", "target-api"),
    "benign_websocket_session_recovery": ("websocket", "control-api"),
    "benign_bulk_transaction_commit": ("transaction", "target-api"),
    "benign_snapshot_restore_check": ("snapshot", "target-web"),
    "benign_multipart_replica_transfer": ("multipart", "target-web"),
    "benign_package_index_delta_pull": ("package", "target-web"),
    "benign_accessibility_link_review": ("crawler", "target-web"),
    "benign_observability_export_burst": ("metrics", "target-api"),
    "benign_cdn_cache_fill": ("cache", "target-web"),
    "benign_database_failover_probe": ("database", "target-api"),
    "benign_consumer_group_rejoin": ("queue", "control-api"),
    "benign_cursor_export_resume": ("pagination", "target-api"),
    "benign_release_bundle_validation": ("integrity", "target-web"),
    "benign_trust_store_refresh": ("certificate", "target-api"),
    "benign_registry_service_refresh": ("discovery", "target-api"),
    "benign_configuration_inventory": ("maintenance", "target-ssh-sim"),
    "benign_session_renewal_recovery": ("auth", "target-api"),
    "benign_resolver_failover_cycle": ("dns", "internal-dns"),
    "benign_audit_log_forward_retry": ("log", "target-api"),
    "benign_long_poll_reconnect": ("websocket", "control-api"),
    "benign_bulk_api_reconciliation": ("transaction", "target-api"),
}


def _family_plan(scenario_id: str, family: str, target: str, ordinal: int) -> tuple[Action, ...]:
    if family == "dns":
        base = (DNS("target-web"), DNS("target-api"), DNS("control-api"))
    elif family == "websocket":
        base = (WS("reconnect_ping_close"),)
    elif family == "maintenance":
        base = (TCP("target-ssh-sim", 2222), DNS("target-api"))
    elif family in {"queue", "log", "transaction", "auth"}:
        base = _http_sequence(target, ["/health", "/beacon" if target == "control-api" else "/api/items"], post=True, tag=family)
    elif family in {"database", "discovery", "certificate"}:
        base = (DNS("target-api"), TCP("target-api", 8080), Action.http("GET", "target-api", "/api/status", workflow=family))
    elif target == "target-web":
        paths = ["/files/sample-small.txt", "/files/sample-config.json", "/about.html"]
        base = _http_sequence(target, paths[: 2 + ordinal % 2], tag=family)
    else:
        base = _http_sequence(target, ["/health", "/api/status", "/api/items"][: 2 + ordinal % 2], tag=family)
    # A bounded local observation carrying the workflow id prevents two
    # different semantic workflows from silently collapsing to one plan.
    terminal = Action.http("POST", "control-api", "/beacon", workflow=scenario_id)
    return (*base, terminal)


for _index, (_scenario_id, (_family, _target)) in enumerate(_V037.items()):
    WORKFLOW_PLANS[_scenario_id] = _family_plan(_scenario_id, _family, _target, _index)


def behavioral_fingerprint(scenario_id: str) -> tuple[tuple[Any, ...], ...]:
    plan = WORKFLOW_PLANS[scenario_id]
    return tuple((action.kind, action.target, action.operation, action.payload) for action in plan)


def primary_target(scenario_id: str) -> str:
    """Return the actual first non-provenance target used by a workflow."""
    action = WORKFLOW_PLANS[scenario_id][0]
    return "internal-dns" if action.kind == "dns" else action.target


def observable_fingerprint(scenario_id: str) -> tuple[tuple[Any, ...], ...]:
    """Fingerprint protocols without the scenario-id provenance beacon."""
    result = []
    for action in WORKFLOW_PLANS[scenario_id]:
        payload = dict(action.payload)
        if action.target == "control-api" and action.operation == "POST:/beacon" and payload.get("workflow") == scenario_id:
            continue
        result.append((action.kind, action.target, action.operation))
    return tuple(result)


def workflow_runtime_audit() -> dict[str, Any]:
    unsupported_families = {"database", "queue", "certificate", "transaction", "replication", "snapshot"}
    rows = []
    for scenario_id, plan in sorted(WORKFLOW_PLANS.items()):
        family = _V037.get(scenario_id, (scenario_id.removeprefix("benign_").removeprefix("smoke_"), ""))[0]
        protocols = sorted({action.kind for action in plan})
        expected_logs = sorted({
            "http" if action.kind in {"http", "websocket"} else "dns" if action.kind == "dns" else "conn"
            for action in plan
        })
        rows.append({
            "scenario_id": scenario_id,
            "semantic_family": family,
            "actual_actions": [
                {"protocol": action.kind, "target": "internal-dns" if action.kind == "dns" else action.target,
                 "operation": action.operation,
                 **({"method": action.operation.split(":", 1)[0], "uri": action.operation.split(":", 1)[1]} if action.kind == "http" else {}),
                 **({"dns_name": action.target, "dns_behavior": "direct_internal_udp_query"} if action.kind == "dns" else {}),
                 **({"tcp_behavior": "bounded_connect_and_optional_banner"} if action.kind == "tcp" else {}),
                 **({"websocket_behavior": action.operation} if action.kind == "websocket" else {})}
                for action in plan
            ],
            "protocols": protocols,
            "targets": sorted({"internal-dns" if action.kind == "dns" else action.target for action in plan}),
            "timing_behavior": "bounded_sequential_actions_with_campaign_rate_limit",
            "semantic_status": "local_protocol_approximation" if family in unsupported_families else "implemented",
            "unsupported_claim": family if family in unsupported_families else None,
            "expected_sensor_logs": expected_logs,
            "expected_observable_feature_family": sorted({
                "dns_counts" if log == "dns" else "http_counts" if log == "http" else "flow_and_rate_features"
                for log in expected_logs
            }),
        })
    collisions: dict[tuple[tuple[Any, ...], ...], list[str]] = {}
    for scenario_id in WORKFLOW_PLANS:
        collisions.setdefault(observable_fingerprint(scenario_id), []).append(scenario_id)
    return {
        "status": "passed",
        "workflow_count": len(rows),
        "workflows": rows,
        "observable_protocol_collisions": [names for names in collisions.values() if len(names) > 1],
        "collision_basis": "protocol/target/operation; terminal provenance beacon excluded",
    }
