#!/usr/bin/env python3
"""Pull one File B/File C account into the independent obligation ledger."""

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from adapters.obligation_common import write_store
from adapters.usaspending_obligations import (
    alias_map, archive_rows, combine_file_b_file_c, file_b_period_events,
    finish_download, parse_file_b_snapshot, parse_file_c, request_download,
    resolve_account,
)
from scripts.rollup_obligations import build


FILE_B_COLUMNS = [
    "submission_period", "federal_account_symbol", "program_activity_reporting_key",
    "program_activity_code", "program_activity_name", "obligations_incurred",
]
FILE_C_COLUMNS = [
    "submission_period", "federal_account_symbol", "program_activity_reporting_key",
    "program_activity_code", "program_activity_name", "transaction_obligated_amount",
    "award_unique_key", "award_id_piid", "parent_award_id_piid", "award_id_fain",
    "award_id_uri", "recipient_uei", "recipient_name",
    "prime_award_base_transaction_description", "usaspending_permalink",
]


def _download(account_id, fy, period, kind, columns):
    print(f"requesting FY{fy} P{period:02} {kind}", flush=True)
    request, _ = request_download(account_id, fy, period, kind, columns)
    payload, status = finish_download(request)
    members = archive_rows(payload)
    expected = status.get("total_rows")
    parsed = sum(len(rows) for rows in members.values())
    if expected is not None and parsed != int(expected):
        raise ValueError(f"FY{fy} P{period:02} {kind}: parsed {parsed} rows, status says {expected}")
    print(f"accepted FY{fy} P{period:02} {kind}: {parsed:,} rows", flush=True)
    return members


def pull(account, years, current_period=12, repo=REPO, rollup=True):
    repo = Path(repo)
    aliases = alias_map(account)
    all_events = []
    audit = {}
    for fy in years:
        last_period = current_period if fy == max(years) else 12
        account_id, detail = resolve_account(account["federalAccount"], fy)
        snapshots = {}
        first_period = 6 if fy == 2017 else 2
        for period in range(first_period, last_period + 1):
            members = _download(account_id, fy, period, "object_class_program_activity",
                                FILE_B_COLUMNS)
            rows = [row for part in members.values() for row in part]
            snapshots[f"FY{fy}P{period:02}"] = parse_file_b_snapshot(
                rows, account["federalAccount"], aliases)
        file_b = file_b_period_events(snapshots, account["federalAccount"])
        c_members = _download(account_id, fy, last_period, "award_financial", FILE_C_COLUMNS)
        file_c = parse_file_c(c_members, account["federalAccount"], aliases)
        events = combine_file_b_file_c(file_b, file_c, account["federalAccount"])
        file_b_total = sum(e["amountCents"] for e in file_b)
        from adapters.obligation_common import cents
        detail_total = cents(detail.get("total_obligated_amount") or 0)
        if last_period == 12 and detail_total and file_b_total != detail_total:
            raise ValueError(f"FY{fy}: File B {file_b_total} cents != account snapshot {detail_total}")
        all_events.extend(events)
        audit[str(fy)] = {"asOfPeriod": last_period, "eventCount": len(events),
                          "fileBObligationsCents": file_b_total,
                          "fileCObligationsCents": sum(e["amountCents"] for e in file_c)}
    store = repo / "data" / "obligations" / account["path"] / "events"
    existing = []
    if store.exists():
        from adapters.obligation_common import load_store
        existing = [e for e in load_store(store) if e["fiscalYear"] not in set(years)]
    write_store(store, existing + all_events,
                {"federalAccount": account["federalAccount"], "pulls": audit})
    if rollup:
        build(repo)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", default="doe/sc")
    parser.add_argument("--from-fy", type=int, default=2017)
    parser.add_argument("--to-fy", type=int, required=True)
    parser.add_argument("--current-period", type=int, default=12)
    parser.add_argument("--no-rollup", action="store_true")
    args = parser.parse_args()
    config = json.loads((REPO / "config" / "obligation_accounts.json").read_text())
    account = next((a for a in config["accounts"] if a["path"] == args.account), None)
    if not account:
        raise SystemExit(f"unknown obligation account {args.account}")
    pull(account, range(args.from_fy, args.to_fy + 1), args.current_period,
         rollup=not args.no_rollup)


if __name__ == "__main__":
    main()
