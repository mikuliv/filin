from __future__ import annotations

import argparse
import json
import os
import queue
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from staging.contracts import canonical_bytes, digest, validate_ingress, validate_receiver_ack
from staging.contracts.models import REGISTRY_COMMITMENT
from staging.http_runtime import client_context, serve, server_context
from staging.storage import ConnectorJournal


class DurableDelivery:
    """Bounded sender that continuously rehydrates pending durable journal rows."""

    def __init__(self, journal: ConnectorJournal, endpoint: str, instance_id: str) -> None:
        self.journal, self.endpoint, self.instance_id = journal, endpoint, instance_id
        self.queue: queue.Queue[list[dict]] = queue.Queue(maxsize=200)
        self.context = client_context(os.environ["DELIVERY_TLS_CERT"], os.environ["DELIVERY_TLS_KEY"], os.environ["DELIVERY_TLS_CA"])
        self.previous: str | None = None
        self.sequence = 0
        self.lock = threading.Lock()
        self.in_flight: set[str] = set()
        self.metrics = {"worker_count": 2, "batch_request_count": 0, "max_batch_size": 0, "retry_count": 0, "queue_capacity_batches": 200}
        for index in range(2):
            threading.Thread(target=self._worker, args=(index,), daemon=True, name=f"sender-{index}").start()
        threading.Thread(target=self._pump, daemon=True, name="durable-pending-pump").start()

    def submit(self, events: list[dict]) -> None:
        for start in range(0, len(events), 50):
            chunk = events[start:start + 50]
            with self.lock:
                fresh = [event for event in chunk if event["event_id"] not in self.in_flight]
                self.in_flight.update(event["event_id"] for event in fresh)
            if fresh:
                self.queue.put(fresh, timeout=2)

    def _pump(self) -> None:
        while True:
            try:
                self.submit(self.journal.pending(50))
            except queue.Full:
                pass
            time.sleep(0.1)

    def _batch(self, events: list[dict], worker: int, attempt: int) -> dict:
        with self.lock:
            self.sequence += 1
            token = digest([self.instance_id, self.sequence, worker, [event["event_id"] for event in events]])
            batch = {
                "batch_contract_version": "staging_event_batch_v1",
                "batch_id": "bat_" + token,
                "attempt_id": f"att_{token[:48]}_{attempt}",
                "connector_instance_id": self.instance_id,
                "candidate_registry_commitment_sha256": REGISTRY_COMMITMENT,
                "event_contract_version": "shadow_event_v2",
                "events": events,
                "event_count": len(events),
                "previous_batch_commitment_sha256": self.previous,
            }
            batch["request_body_sha256"] = digest(batch)
            self.previous = digest(batch)
            self.metrics["batch_request_count"] += 1
            self.metrics["max_batch_size"] = max(self.metrics["max_batch_size"], len(events))
            self.journal.trace(events, "connector_batch_created")
            return batch

    def _worker(self, worker: int) -> None:
        while True:
            events = self.queue.get()
            delivered = False
            for attempt in range(1, 6):
                batch = self._batch(events, worker, attempt)
                request = urllib.request.Request(self.endpoint, data=canonical_bytes(batch), headers={"Content-Type": "application/json"}, method="POST")
                try:
                    self.journal.trace(events, "connector_send_started")
                    with urllib.request.urlopen(request, context=self.context, timeout=min(5, attempt + 1)) as response:
                        ack = json.loads(response.read())
                    self.journal.trace(events, "connector_ack_received")
                    validate_receiver_ack(ack, batch)
                    checkpoint = self.journal.checkpoint(batch, ack)
                    self.journal.trace(events, "connector_checkpoint_committed", checkpoint)
                    delivered = True
                    break
                except (OSError, urllib.error.URLError, ValueError, json.JSONDecodeError):
                    self.metrics["retry_count"] += 1
                    time.sleep(min(0.5, 0.05 * (2**attempt)))
            if delivered:
                with self.lock:
                    self.in_flight.difference_update(event["event_id"] for event in events)
            else:
                try:
                    self.queue.put(events, timeout=1)
                except queue.Full:
                    with self.lock:
                        self.in_flight.difference_update(event["event_id"] for event in events)
            self.queue.task_done()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8443)
    parser.add_argument("--db", type=Path, default=Path("/var/lib/filin/connector.sqlite"))
    parser.add_argument("--receiver", default="https://reference-receiver:9443/reference-receiver/v1/event-batches")
    args = parser.parse_args()
    instance = os.environ.get("CONNECTOR_INSTANCE_ID", "connector-v0317")
    journal = ConnectorJournal(args.db)
    delivery = DurableDelivery(journal, args.receiver, instance)

    def ingress(value):
        received = time.monotonic_ns()
        request = validate_ingress(value)
        commit = journal.append(request["request_id"], request["events"])
        journal.trace(request["events"], "connector_ingress_received", received)
        accepted_ids = set(commit["accepted"])
        accepted = [event for event in request["events"] if event["event_id"] in accepted_ids]
        if accepted:
            delivery.submit(accepted)
        ack = {
            "ack_contract_version": "connector_ingress_ack_v1",
            "request_id": request["request_id"],
            "connector_instance_id": instance,
            "connector_journal_commit_id": commit["commit_id"],
            "connector_journal_commit_sha256": commit["commit_sha256"],
            "accepted_event_ids": commit["accepted"],
            "duplicate_event_ids": commit["duplicates"],
            "rejected_events": [],
            "durable": True,
            "error_code": None,
        }
        journal.trace(request["events"], "connector_ingress_ack_sent")
        return 200, ack

    context = server_context(os.environ["INGRESS_TLS_CERT"], os.environ["INGRESS_TLS_KEY"], os.environ["INGRESS_TLS_CLIENT_CA"])
    serve(args.host, args.port, context, {"/staging-connector/v1/events": ingress}, lambda: args.db.exists() and journal.counts()["pending"] < 200_000)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
