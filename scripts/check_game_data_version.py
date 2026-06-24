#!/usr/bin/env python3
"""Check language files against recorded source hashes without changing data."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path


DEFAULT_METADATA = (
    Path(__file__).resolve().parent.parent / "references" / "game-data-version.json"
)


def read_bytes(location: str) -> bytes:
    if location.startswith(("https://", "http://")):
        request = urllib.request.Request(
            location,
            headers={"User-Agent": "translate-splatoon-zh version checker"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read()
    return Path(location).read_bytes()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--jp")
    parser.add_argument("--zh")
    parser.add_argument("--en")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
    overrides = {"JPja": args.jp, "CNzh": args.zh, "EUen": args.en}
    changed = False

    for name, recorded in metadata["sources"].items():
        location = overrides[name] or recorded["url"]
        content = read_bytes(location)
        digest = hashlib.sha256(content).hexdigest()
        status = "OK"
        if digest != recorded["sha256"] or len(content) != recorded["bytes"]:
            status = "CHANGED"
            changed = True
        print(
            f"{status}: {name} bytes={len(content)} sha256={digest} "
            f"recorded_at={metadata['checked_at']}"
        )
    return 1 if changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
