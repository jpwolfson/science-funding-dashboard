#!/usr/bin/env python3
"""Offline, fail-closed validation for the obligation ledger."""

import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from adapters.obligation_common import aggregate, load_store, period_info


def load_baseline(repo, account):
    path = account.get("baseline")
    if not path:
        raise ValueError(f"{account['path']}: missing baseline path")
    baseline = json.loads((repo / path).read_text())
    if baseline.get("federalAccount") != account["federalAccount"]:
        raise ValueError(f"{account['path']}: baseline account mismatch")
    return baseline


def validate(repo=REPO, require_data=True):
    repo = Path(repo)
    errors = []
    config = json.loads((repo / "config" / "obligation_accounts.json").read_text())
    for account in config["accounts"]:
        store = repo / "data" / "obligations" / account["path"] / "events"
        events = load_store(store) if store.exists() else []
        try:
            baseline = load_baseline(repo, account)
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
            errors.append(str(error))
            continue
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
        residual_buckets = defaultdict(int)
        file_c_buckets = set()
        for event in events:
            if event["federalAccount"] != account["federalAccount"]:
                errors.append(f"{event['id']}: federal account mismatch")
            if event["source"] not in {"file_c", "file_b_residual"}:
                errors.append(f"{event['id']}: unsupported source {event['source']!r}")
            if event["grossPositiveCents"] < 0 or event["grossNegativeCents"] > 0 or (
                    event["grossPositiveCents"] + event["grossNegativeCents"] !=
                    event["amountCents"]):
                errors.append(f"{event['id']}: signed gross amounts do not reconcile")
            bucket = (event["submissionPeriod"], event["programActivityCode"])
            if event["source"] == "file_b_residual":
                residual_buckets[bucket] += 1
                if event["linked"] or event["awardId"]:
                    errors.append(f"{event['id']}: residual must not be award-linked")
            else:
                file_c_buckets.add(bucket)
            if (event["source"] == "file_c" and event["linked"] and
                    not event["awardUrl"].startswith(
                        "https://www.usaspending.gov/award/")):
                errors.append(f"{event['id']}: invalid public USAspending award URL")
            fy, period, end = period_info(event["submissionPeriod"])
            if (fy, period, end.isoformat()) != (
                    event["fiscalYear"], event["fiscalPeriod"], event["date"]):
                errors.append(f"{event['id']}: period metadata mismatch")
            by_fy[fy].append(event)
        for bucket in sorted(file_c_buckets):
            if residual_buckets[bucket] != 1:
                errors.append(
                    f"{account['path']}: {bucket} has {residual_buckets[bucket]} "
                    "File B residual rows"
                )
        manifest_path = store / "manifest.json"
        if not manifest_path.exists():
            errors.append(f"{account['path']}: missing obligation manifest")
        else:
            manifest = json.loads(manifest_path.read_text())
            actual_sha = hashlib.sha256("\n".join(sorted(ids)).encode()).hexdigest()
            if manifest.get("recordCount") != len(events):
                errors.append(f"{account['path']}: manifest record count mismatch")
            if manifest.get("fiscalYears") != sorted(by_fy):
                errors.append(f"{account['path']}: manifest fiscal years mismatch")
            if manifest.get("sha256") != actual_sha:
                errors.append(f"{account['path']}: manifest fingerprint mismatch")
            if manifest.get("federalAccount") != account["federalAccount"]:
                errors.append(f"{account['path']}: manifest account mismatch")
        expected_fys = {
            int(fy): row for fy, row in baseline["fiscalYears"].items()
            if row["status"] in {"complete", "partial"}
        }
        for fy in sorted(set(expected_fys) - set(by_fy)):
            errors.append(f"FY{fy}: required {expected_fys[fy]['status']} snapshot is missing")
        for fy, row in baseline["fiscalYears"].items():
            if row["status"] == "unavailable" and int(fy) in by_fy:
                errors.append(f"FY{fy}: events exist for a source-unavailable year")
        for fy, rows in sorted(by_fy.items()):
            pin = baseline["fiscalYears"].get(str(fy))
            if not pin:
                errors.append(f"FY{fy}: missing GTAS baseline")
                continue
            actual = sum(e["amountCents"] for e in rows)
            if pin["status"] == "complete" and actual != pin["obligationsCents"]:
                errors.append(f"FY{fy}: {actual} cents != GTAS {pin['obligationsCents']} cents")
            if pin["status"] == "partial":
                first = min(e["fiscalPeriod"] for e in rows)
                last = max(e["fiscalPeriod"] for e in rows)
                if pin.get("firstPeriod") is not None and pin["firstPeriod"] != first:
                    errors.append(
                        f"FY{fy}: first P{first:02} != pinned P{pin['firstPeriod']:02}"
                    )
                if pin.get("asOfPeriod") != last:
                    errors.append(f"FY{fy}: latest P{last:02} has no same-period GTAS pin")
                elif actual != pin["obligationsCents"]:
                    errors.append(f"FY{fy} P{last:02}: {actual} cents != pinned {pin['obligationsCents']} cents")
        partial_fys = {fy for fy, pin in expected_fys.items() if pin["status"] == "partial"}
        covered_periods = {event["submissionPeriod"] for event in events}
        stats = aggregate(events, max(by_fy), covered_periods, partial_fys)
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
            if page.get("totalNetObligationsCents") != stats["totalNetObligationsCents"]:
                errors.append(f"{account['path']}: dashboard total is stale")
            if page.get("currentFY") != stats["currentFY"] or page.get("asOfPeriod") != stats["asOfPeriod"]:
                errors.append(f"{account['path']}: dashboard coverage period is stale")
            page_fys = {row["fy"]: row for row in page.get("fiscalYears", [])}
            for row in stats["fiscalYears"]:
                actual = page_fys.get(row["fy"])
                if not actual or (actual.get("netObligationsCents"), actual.get("partial")) != (
                        row["netObligationsCents"], row["partial"]):
                    errors.append(f"FY{row['fy']}: dashboard fiscal-year status is stale")
            if [row.get("submissionPeriod") for row in page.get("reportingPeriods", [])] != [
                    row["submissionPeriod"] for row in stats["reportingPeriods"]]:
                errors.append(f"{account['path']}: dashboard reporting periods are stale")
            children = page.get("children", [])
            if round(sum(c.get("currentFYNetObligations", 0) for c in children) * 100) != next(
                    r["netObligationsCents"] for r in stats["fiscalYears"] if r["fy"] == stats["currentFY"]):
                errors.append(f"{account['path']}: child current-FY dollars do not add to parent")
            for pa in account["programActivities"]:
                child = repo / "data" / "obligations" / account["path"] / pa["slug"] / "dashboard.json"
                if not child.exists():
                    errors.append(f"{account['path']}/{pa['slug']}: missing dashboard.json")
                    continue
                child_page = json.loads(child.read_text())
                child_events = [
                    event for event in events
                    if event["programActivityCode"] == pa["code"]
                ]
                child_stats = aggregate(
                    child_events, stats["currentFY"], covered_periods, partial_fys
                )
                if child_page.get("totalNetObligationsCents") != child_stats["totalNetObligationsCents"]:
                    errors.append(f"{account['path']}/{pa['slug']}: dashboard total is stale")
                if child_page.get("asOfPeriod") != stats["asOfPeriod"]:
                    errors.append(f"{account['path']}/{pa['slug']}: coverage period is stale")
                if [row.get("submissionPeriod") for row in child_page.get("reportingPeriods", [])] != [
                        row["submissionPeriod"] for row in stats["reportingPeriods"]]:
                    errors.append(f"{account['path']}/{pa['slug']}: reporting periods are incomplete")
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
