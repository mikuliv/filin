from __future__ import annotations

import argparse
import json
import os
import time
import urllib.request
from pathlib import Path

from staging.contracts import canonical_bytes, digest
from staging.contracts.models import REGISTRY_COMMITMENT
from staging.http_runtime import client_context


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("events", type=Path)
    parser.add_argument("--endpoint", default="https://staging-connector:8443/staging-connector/v1/events")
    parser.add_argument("--batch-size", type=int, default=50)
    args = parser.parse_args()
    events = [json.loads(line) for line in args.events.read_text(encoding="utf-8").splitlines() if line]
    context = client_context(os.environ["TLS_CERT"], os.environ["TLS_KEY"], os.environ["TLS_CA"])
    instance = os.environ.get("SENSOR_INSTANCE_ID", "sensor_v0316_local")
    trace_path = Path(os.environ.get("SENSOR_TRACE", "/var/lib/filin/sensor_trace.jsonl"))
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    trace = trace_path.open("a", encoding="utf-8", buffering=1)
    for index in range(0, len(events), args.batch_size):
        chunk = events[index:index + args.batch_size]
        created = time.monotonic_ns()
        for offset, event in enumerate(chunk):
            record = {"event_id": event["event_id"], "sensor_event_created": created + offset, "sensor_outbox_durable": created + len(chunk) + offset, "connector_request_started": created + 2 * len(chunk) + offset}
            trace.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
        request_id = "req_" + digest([instance, index, [item["event_id"] for item in chunk]])
        body = {"ingress_contract_version": "connector_ingress_v1", "request_id": request_id, "sensor_instance_id": instance, "candidate_registry_commitment_sha256": REGISTRY_COMMITMENT, "events": chunk}
        body["request_body_sha256"] = digest(body)
        request = urllib.request.Request(args.endpoint, data=canonical_bytes(body), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(request, context=context, timeout=10) as response:
            ack = json.loads(response.read())
        if not ack.get("durable") or len(ack.get("accepted_event_ids", [])) + len(ack.get("duplicate_event_ids", [])) != len(chunk):
            raise RuntimeError("connector_ingress_ack_invalid")
        print(json.dumps({"request_id": request_id, "event_count": len(chunk), "durable": True}, sort_keys=True), flush=True)
    trace.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
