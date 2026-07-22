from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from rehearsal.common import append_jsonl, digest, read_json, write_json
from staging.contracts import canonical_bytes
from staging.contracts.models import REGISTRY_COMMITMENT
from staging.http_runtime import client_context


def _lines_from(path: Path, offset: int, limit: int) -> tuple[list[dict], int]:
    if not path.is_file():
        return [], offset
    values: list[dict] = []
    with path.open("rb") as stream:
        stream.seek(offset)
        complete_offset = offset
        while len(values) < limit:
            line = stream.readline()
            if not line or not line.endswith(b"\n"):
                break
            values.append(json.loads(line))
            complete_offset = stream.tell()
        return values, complete_offset


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", type=Path, default=Path("/run/rehearsal/events.jsonl"))
    parser.add_argument("--checkpoint", type=Path, default=Path("/var/lib/filin/sensor-checkpoint.json"))
    parser.add_argument("--trace", type=Path, default=Path("/var/lib/filin/sensor-trace.jsonl"))
    parser.add_argument("--endpoint", default="https://staging-connector:8443/staging-connector/v1/events")
    parser.add_argument("--batch-size", type=int, default=50)
    args = parser.parse_args()
    context = client_context(os.environ["TLS_CERT"], os.environ["TLS_KEY"], os.environ["TLS_CA"])
    instance = os.environ.get("SENSOR_INSTANCE_ID", "sensor-v0317")
    offset = int(read_json(args.checkpoint).get("byte_offset", 0)) if args.checkpoint.is_file() else 0
    while True:
        events, next_offset = _lines_from(args.events, offset, args.batch_size)
        if not events:
            time.sleep(0.05)
            continue
        now = time.monotonic_ns()
        append_jsonl(args.trace, [{
            "event_id": event["event_id"],
            "sensor_event_created": now + index,
            "sensor_outbox_durable": now + len(events) + index,
            "connector_request_started": now + 2 * len(events) + index,
        } for index, event in enumerate(events)])
        request_id = "req_" + digest([instance, offset, [item["event_id"] for item in events]])
        body = {
            "ingress_contract_version": "connector_ingress_v1",
            "request_id": request_id,
            "sensor_instance_id": instance,
            "candidate_registry_commitment_sha256": REGISTRY_COMMITMENT,
            "events": events,
        }
        body["request_body_sha256"] = digest(body)
        request = urllib.request.Request(args.endpoint, data=canonical_bytes(body), headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, context=context, timeout=10) as response:
                ack = json.loads(response.read())
            accounted = len(ack.get("accepted_event_ids", [])) + len(ack.get("duplicate_event_ids", []))
            if not ack.get("durable") or accounted != len(events):
                raise RuntimeError("connector_ingress_ack_invalid")
            offset = next_offset
            write_json(args.checkpoint, {"byte_offset": offset, "last_request_id": request_id, "last_ack_monotonic_ns": time.monotonic_ns()})
        except (OSError, urllib.error.URLError, RuntimeError, json.JSONDecodeError):
            time.sleep(0.2)


if __name__ == "__main__":
    raise SystemExit(main())
