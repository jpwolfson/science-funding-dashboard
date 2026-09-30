#!/usr/bin/env python3
"""Discover registry inputs for federal accounts before onboarding (CI-only).

Phase 3.2e. For each federal account and fiscal year it records, from the
same official sources the pull uses:

- the File B Program Activity identities (PAC, PAN, PARK) present in the
  final-period cumulative snapshot, with row counts and exact cents;
- the account's File A/GTAS fiscal-year snapshot obligations from the
  federal-account record (the value the pull's total check compares with);
- for the first fiscal year with File B activity, the first period whose
  snapshot is non-empty (the registry's availability boundary); and
- the official per-account Program Activity list (PARK names).

It writes one JSON report and never touches the registry, baselines, or
stores. The onboarding backfill remains the fail-closed alias-drift gate:
anything this snapshot view misses stops the pull there.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from adapters.obligation_common import cents
from adapters.usaspending_obligations import (
    API, _json, archive_rows, finish_download, request_download,
    resolve_account,
)
from scripts.pull_obligation_account import FILE_B_COLUMNS


def _file_b(account_id, fy, period):
    result, _scope = request_download(
        account_id, fy, period, "object_class_program_activity",
        FILE_B_COLUMNS)
    payload, status = finish_download(result)
    rows = [row for part in archive_rows(payload).values() for row in part]
    identities = {}
    for row in rows:
        key = (row.get("program_activity_code", ""),
               row.get("program_activity_name", ""),
               row.get("program_activity_reporting_key", ""))
        entry = identities.setdefault(key, {"rows": 0, "cents": 0})
        entry["rows"] += 1
        raw = row.get("obligations_incurred", "")
        if raw:
            entry["cents"] += cents(raw)
    return {
        "period": period,
        "statusRowCount": status.get("total_rows"),
        "totalCents": sum(v["cents"] for v in identities.values()),
        "programActivities": [
            {"code": c, "name": n, "park": p, **identities[(c, n, p)]}
            for (c, n, p) in sorted(identities)
        ],
    }


def _program_activity_list(account):
    rows, page = [], 1
    while True:
        data = _json(f"{API}/federal_accounts/{account}/program_activities/"
                     f"?limit=100&page={page}")
        rows.extend(data.get("results", []))
        if not (data.get("page_metadata") or {}).get("hasNext"):
            return rows
        page += 1


def discover(report, from_fy, to_fy, current_period, save):
    account = report["federalAccount"]
    report["fiscalYears"] = {}
    try:
        report["officialProgramActivities"] = _program_activity_list(account)
    except Exception as error:
        report["officialProgramActivitiesError"] = f"{type(error).__name__}: {error}"
    first_active = None
    for fy in range(from_fy, to_fy + 1):
        period = current_period if fy == to_fy else 12
        row = {}
        try:
            account_id, detail = resolve_account(account, fy)
            report.setdefault("title", detail.get("account_title"))
            row["accountId"] = account_id
            row["accountRecord"] = {
                k: v for k, v in detail.items()
                if not isinstance(v, (dict, list))}
            row["accountRecordNested"] = {
                k: v for k, v in detail.items() if isinstance(v, dict)}
            row["fileB"] = _file_b(account_id, fy, period)
            if first_active is None and row["fileB"]["statusRowCount"]:
                first_active = fy
                first_period = 6 if fy == 2017 else 2
                for probe in range(first_period, period):
                    early = _file_b(account_id, fy, probe)
                    if early["statusRowCount"]:
                        row["firstNonEmptyPeriod"] = probe
                        break
                else:
                    row["firstNonEmptyPeriod"] = period
        except Exception as error:
            row["error"] = f"{type(error).__name__}: {error}"
        report["fiscalYears"][str(fy)] = row
        save()
        print(account, fy, {k: v for k, v in row.items() if k != "fileB"},
              (row.get("fileB") or {}).get("totalCents"), flush=True)
    report["firstActiveFiscalYear"] = first_active
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--accounts", required=True)
    parser.add_argument("--from-fy", type=int, default=2017)
    parser.add_argument("--to-fy", type=int, required=True)
    parser.add_argument("--current-period", type=int, required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    out = Path(args.report)
    out.parent.mkdir(parents=True, exist_ok=True)
    result = {"generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "fromFy": args.from_fy, "toFy": args.to_fy,
              "currentPeriod": args.current_period, "accounts": {}}

    def save():
        out.write_text(json.dumps(result, indent=1) + "\n")

    for account in args.accounts.split(","):
        report = result["accounts"][account] = {"federalAccount": account}
        discover(report, args.from_fy, args.to_fy, args.current_period, save)
        save()


if __name__ == "__main__":
    main()
