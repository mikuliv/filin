"""Однострочный progress reporter с ETA для долгих selection этапов."""
from __future__ import annotations
import argparse, json, time
from pathlib import Path


class StageProgress:
    def __init__(self, total: int, output: Path | None = None, started: float | None = None):
        self.total, self.output = total, output
        self.started = time.monotonic() if started is None else started

    def update(self, completed: int) -> dict:
        elapsed = max(time.monotonic() - self.started, 0.0)
        rate = completed / elapsed if elapsed and completed else 0.0
        eta = (self.total - completed) / rate if rate else None
        item = {"completed": completed, "total": self.total, "percent": 100 * completed / self.total,
                "elapsed_seconds": elapsed, "policies_per_second": rate, "eta_seconds": eta}
        if self.output:
            self.output.parent.mkdir(parents=True, exist_ok=True)
            self.output.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
        return item


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--total", type=int, required=True)
    parser.add_argument("--completed", type=int, required=True); parser.add_argument("--output")
    args = parser.parse_args(); print(json.dumps(StageProgress(args.total, Path(args.output) if args.output else None).update(args.completed), ensure_ascii=False))


if __name__ == "__main__": main()
