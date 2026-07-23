from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

from rehearsal.storage import RehearsalReceiverStore
from staging.contracts import validate_batch
from staging.http_runtime import serve, server_context


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=9443)
    parser.add_argument("--db", type=Path, default=Path("/var/lib/filin/receiver.sqlite"))
    parser.add_argument("--trace-db", type=Path, default=Path("/var/lib/filin/receiver-trace.sqlite"))
    args = parser.parse_args()
    instance = os.environ.get("RECEIVER_INSTANCE_ID", "receiver_v0317_local")
    store = RehearsalReceiverStore(args.db, instance, args.trace_db)

    def receive(value):
        received = time.monotonic_ns()
        batch = validate_batch(value)
        store.trace(batch["events"], "receiver_received", received)
        store.trace(batch["events"], "receiver_validation_completed")
        ack = store.commit(batch)
        store.trace(batch["events"], "receiver_ack_sent")
        return 200, ack

    context = server_context(os.environ["TLS_CERT"], os.environ["TLS_KEY"], os.environ["TLS_CLIENT_CA"])
    serve(
        args.host,
        args.port,
        context,
        {"/reference-receiver/v1/event-batches": receive},
        lambda: store.count() >= 0 and args.db.exists(),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
