"""Reject mutable image tags when preparing a declared release configuration."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

IMAGE = re.compile(r"^\s*image:\s*([^\s#]+)", re.MULTILINE)


def find_mutable_images(path: Path) -> list[str]:
    return [reference for reference in IMAGE.findall(path.read_text(encoding="utf-8")) if reference.endswith(":latest") or ":" not in reference.split("@", 1)[0]]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--compose", required=True)
    parser.add_argument("--release", action="store_true", help="Fail instead of only reporting mutable images.")
    args = parser.parse_args()
    mutable = find_mutable_images(Path(args.compose))
    if mutable:
        print("Mutable image references: " + ", ".join(mutable))
        if args.release:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
