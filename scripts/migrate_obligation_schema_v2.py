#!/usr/bin/env python3
"""One-way migration of committed obligation data to schema v2."""

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from adapters.obligation_common import (
    event_fingerprint, file_sha256, load_store, partition_diff,
    rebuild_manifest, write_partition_provenance,
)
from scripts.rollup_obligations import build


def migrate(repo=REPO):
    repo = Path(repo)
    config = json.loads((repo / "config" / "obligation_accounts.json").read_text())
    migrated = 0
    for account in config["accounts"]:
        base = repo / "data" / "obligations" / account["path"]
        store = base / "events"
        if not store.exists():
            continue
        events = load_store(store)
        by_fy = {}
        for event in events:
            by_fy.setdefault(event["fiscalYear"], []).append(event)
        generated = "1970-01-01"
        dashboard = base / "dashboard.json"
        if dashboard.exists():
            generated = json.loads(dashboard.read_text()).get("generated", generated)
        baseline = json.loads((repo / account["baseline"]).read_text())
        old_manifest = store / "manifest.json"
        old_manifest_sha = file_sha256(old_manifest) if old_manifest.exists() else None
        for fy, rows in sorted(by_fy.items()):
            provenance_path = store / f"FY{fy}.provenance.json"
            if provenance_path.exists():
                existing = json.loads(provenance_path.read_text())
                if existing.get("collectionStatus") == "legacy-migrated":
                    existing["migratedAt"] = existing.pop(
                        "acceptedAt", existing.get("migratedAt", f"{generated}T12:00:00+00:00")
                    )
                    write_partition_provenance(store, fy, existing)
                continue
            pin = baseline["fiscalYears"].get(str(fy))
            value = {
                "schemaVersion": 2,
                "collectionStatus": "legacy-migrated",
                "migratedAt": f"{generated}T12:00:00+00:00",
                "accountPath": account["path"],
                "federalAccount": account["federalAccount"],
                "fiscalYear": fy,
                "asOfPeriod": max(row["fiscalPeriod"] for row in rows),
                "downloads": [],
                "normalized": {
                    "recordCount": len(rows),
                    "eventFingerprint": event_fingerprint(rows),
                    "netObligationsCents": sum(row["amountCents"] for row in rows),
                },
                "replacement": {
                    "previousEventFingerprint": None,
                    "previousProvenanceSha256": None,
                },
                "diff": {**partition_diff([], rows), "kind": "schema-v2-migration"},
                "baselinePin": pin,
                "migration": {
                    "sourceManifestSha256": old_manifest_sha,
                    "note": "Pre-v2 normalized shard; raw request/status/archive facts were not retained and are not reconstructed.",
                },
            }
            write_partition_provenance(store, fy, value)
            migrated += 1
        rebuild_manifest(store, metadata={
            "federalAccount": account["federalAccount"],
            "baseline": account["baseline"],
        })
    build(repo)
    return migrated


if __name__ == "__main__":
    print(f"Migrated {migrate()} obligation partitions to schema v2")
