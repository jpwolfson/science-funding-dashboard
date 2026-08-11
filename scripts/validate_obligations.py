#!/usr/bin/env python3
"""Offline, fail-closed validation for the obligation ledger."""

import json
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from adapters.obligation_common import aggregate, load_store, period_info


def validate(repo=REPO, require_data=True):
    repo = Path(repo)
    errors = []
    config = json.loads((repo / "config" / "obligation_accounts.json").read_text())
    baseline = json.loads((repo / "reference" / "doe_sc_obligation_baseline.json").read_text())
    for account in config["accounts"]:
        store = repo / "data" / "obligations" / account["path"] / "events"
        events = load_store(store) if store.exists() else []
        if not events:
            if require_data:
                errors.append(f"{account['path']}: no obligation events")
            continue
        ids = [e["id"] for e in events]
        if len(ids) != len(set(ids)):
            errors.append(f"{account['path']}: duplicate event IDs")
        known = {pa["code"] for pa in account["programActivities"]}
        unknown = sorted({e["programActivityCode"] for e in events} - known)
        if unknown:
            errors.append(f"{account['path']}: unmapped Program Activities {unknown}")
        by_fy = defaultdict(list)
        for event in events:
            if (event["source"] == "file_c" and event["linked"] and
                    not event["awardUrl"].startswith(
                        "https://www.usaspending.gov/award/")):
                errors.append(f"{event['id']}: invalid public USAspending award URL")
            fy, period, end = period_info(event["submissionPeriod"])
            if (fy, period, end.isoformat()) != (
                    event["fiscalYear"], event["fiscalPeriod"], event["date"]):
                errors.append(f"{event['id']}: period metadata mismatch")
            by_fy[fy].append(event)
        for fy, rows in sorted(by_fy.items()):
            pin = baseline["fiscalYears"].get(str(fy))
            if not pin:
                errors.append(f"FY{fy}: missing GTAS baseline")
                continue
            actual = sum(e["amountCents"] for e in rows)
            if pin["status"] == "complete" and actual != pin["obligationsCents"]:
                errors.append(f"FY{fy}: {actual} cents != GTAS {pin['obligationsCents']} cents")
            if pin["status"] == "partial":
                last = max(e["fiscalPeriod"] for e in rows)
                if pin.get("asOfPeriod") != last:
                    errors.append(f"FY{fy}: latest P{last:02} has no same-period GTAS pin")
                elif actual != pin["obligationsCents"]:
                    errors.append(f"FY{fy} P{last:02}: {actual} cents != pinned {pin['obligationsCents']} cents")
        stats = aggregate(events, max(by_fy))
        if stats["netObligationsCents"] != sum(e["amountCents"] for e in events):
            errors.append(f"{account['path']}: aggregate total mismatch")
        for row in stats["fiscalYears"]:
            endpoint = next((s["points"][-1] for s in stats["fyCumulative"]
                             if s["fy"] == row["fy"] and s["points"]), None)
            if endpoint and endpoint["netObligationsCents"] != row["netObligationsCents"]:
                errors.append(f"FY{row['fy']}: cumulative endpoint mismatch")
        dashboard = repo / "data" / "obligations" / account["path"] / "dashboard.json"
        if dashboard.exists():
            page = json.loads(dashboard.read_text())
            if page.get("kind") != "obligations":
                errors.append(f"{account['path']}: dashboard kind mismatch")
            if page.get("warnings") or not page.get("dataComplete"):
                errors.append(f"{account['path']}: dashboard is not warning-free and complete")
            children = page.get("children", [])
            if round(sum(c.get("currentFYNetObligations", 0) for c in children) * 100) != next(
                    r["netObligationsCents"] for r in stats["fiscalYears"] if r["fy"] == stats["currentFY"]):
                errors.append(f"{account['path']}: child current-FY dollars do not add to parent")
        elif require_data:
            errors.append(f"{account['path']}: missing dashboard.json")
    return errors


def main():
    require = "--allow-empty" not in sys.argv
    errors = validate(require_data=require)
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        raise SystemExit(f"obligation validation failed with {len(errors)} error(s)")
    print("Obligation ledger validation passed" + ("" if require else " (empty stores allowed)"))


if __name__ == "__main__":
    main()
