#!/usr/bin/env python3
"""Fetch and accept registered funding-action sources without review gates."""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from adapters.funding_sentinel import (
    accept_source_snapshot,
    load_sentinel_stores,
    record_source_failure,
    write_source_stores,
)
from adapters.funding_source_adapters import parse_source


USER_AGENT = "science-funding-dashboard/phase-3.2c2 (+https://github.com/jpwolfson/science-funding-dashboard)"


def fetch_source(source):
    request = Request(source["url"], headers={
        "User-Agent": USER_AGENT,
        "Accept": source.get("accept", "*/*"),
    })
    with urlopen(request, timeout=int(source.get("timeoutSeconds", 60))) as response:
        raw = response.read(int(source.get("maximumBytes", 5_000_000)) + 1)
    if len(raw) > int(source.get("maximumBytes", 5_000_000)):
        raise ValueError(f"{source['id']}: response exceeds maximumBytes")
    return raw


def update_sources(repo=REPO, accepted_at=None, fetcher=fetch_source):
    repo = Path(repo)
    accepted_at = accepted_at or datetime.now(timezone.utc).isoformat()
    config = json.loads((repo / "config" / "funding_sentinel.json").read_text())
    stores = load_sentinel_stores(repo)
    events = stores["events"]["events"]
    statuses = stores["sources"]["sources"]
    results = []
    for source in config.get("sources", []):
        try:
            parsed = parse_source(fetcher(source), source)
            events, statuses = accept_source_snapshot(
                events,
                statuses,
                source["id"],
                parsed["events"],
                parsed["snapshotSha256"],
                accepted_at,
                parsed["metadata"],
            )
            results.append({
                "id": source["id"], "status": "current",
                "recordCount": len(parsed["events"]),
            })
        except Exception as error:  # A source failure is a publishable state.
            statuses = record_source_failure(
                statuses, source["id"], accepted_at, error
            )
            results.append({
                "id": source["id"], "status": "error", "error": str(error),
            })
    write_source_stores(repo, events, statuses)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=REPO)
    parser.add_argument("--accepted-at", help="ISO timestamp for deterministic tests")
    args = parser.parse_args()
    results = update_sources(args.repo, args.accepted_at)
    for result in results:
        if result["status"] == "current":
            print(f"Accepted {result['id']}: {result['recordCount']} records")
        else:
            print(f"WARNING: retained last good {result['id']}: {result['error']}")


if __name__ == "__main__":
    main()
