#!/usr/bin/env python3
"""Measure one account-year's File B/File C download cost (CI-only probe).

Phase 3.2e sizing probe. It issues exactly the production custom-account
requests (same columns as scripts/pull_obligation_account.py) for one
federal account, fiscal year, and final period, and reports what the
onboarding plan needs to know: generation wait, archive bytes, member row
counts, parse time, peak memory, normalized-event count, and the Program
Activity identities present. It never writes the obligation store,
registry, or baselines; its only output is a JSON report.

It does not apply the adapter's 2 h status cap: the point is to measure
how long generation actually takes, so the cap is a CLI parameter.
"""

import argparse
import json
import resource
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from adapters.obligation_common import canonical_period, cents
from adapters.usaspending_obligations import (
    archive_rows, finish_download, request_download, resolve_account,
)
from scripts.pull_obligation_account import FILE_B_COLUMNS, FILE_C_COLUMNS


def _peak_rss_mb():
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _first(row, *names):
    for name in names:
        if row.get(name) not in (None, ""):
            return row[name]
    return ""


def _measure(account_id, fy, period, kind, columns, timeout_seconds):
    started = time.monotonic()
    result, _scope = request_download(account_id, fy, period, kind, columns)
    accepted = time.monotonic()
    payload, status = finish_download(result, timeout=timeout_seconds)
    retrieved = time.monotonic()
    members = archive_rows(payload)
    parsed = time.monotonic()
    return members, {
        "kind": kind,
        "fiscalYear": fy,
        "period": period,
        "requestSeconds": round(accepted - started, 1),
        "generateAndRetrieveSeconds": round(retrieved - accepted, 1),
        "parseSeconds": round(parsed - retrieved, 1),
        "zipBytes": len(payload),
        "statusRowCount": status.get("total_rows"),
        "statusSeconds": status.get("seconds_elapsed"),
        "statusFileName": status.get("file_name"),
        "memberRowCounts": {name: len(rows) for name, rows in members.items()},
        "peakRssMbAfterParse": _peak_rss_mb(),
    }


def _pa_identities(rows):
    counts = Counter()
    totals = defaultdict(int)
    for row in rows:
        key = (
            _first(row, "program_activity_code"),
            _first(row, "program_activity_name"),
            _first(row, "program_activity_reporting_key"),
        )
        counts[key] += 1
        raw = _first(row, "obligations_incurred", "transaction_obligated_amount")
        if raw:
            totals[key] += cents(raw)
    return [
        {"code": c, "name": n, "park": p, "rows": counts[(c, n, p)],
         "cents": totals[(c, n, p)]}
        for (c, n, p) in sorted(counts)
    ]


def _file_c_shape(members):
    rows = [row for part in members.values() for row in part]
    awards = set()
    events = set()
    periods = Counter()
    total = 0
    nonzero = 0
    for row in rows:
        raw = _first(row, "transaction_obligated_amount")
        if raw == "" or cents(raw) == 0:
            continue
        nonzero += 1
        total += cents(raw)
        award = _first(row, "award_unique_key", "award_id_piid", "award_id_fain",
                       "award_id_uri")
        period = canonical_period(_first(row, "submission_period"))
        awards.add(award)
        events.add((award, _first(row, "program_activity_code"),
                    _first(row, "program_activity_reporting_key"), period))
        periods[period] += 1
    return {
        "rows": len(rows),
        "nonzeroRows": nonzero,
        "distinctAwards": len(awards),
        "normalizedEventEstimate": len(events),
        "rowsBySubmissionPeriod": dict(sorted(periods.items())),
        "totalCents": total,
        "programActivities": _pa_identities(rows),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--federal-account", required=True)
    parser.add_argument("--fy", type=int, required=True)
    parser.add_argument("--period", type=int, required=True)
    parser.add_argument("--kinds", default="file_b,file_c")
    parser.add_argument("--timeout-hours", type=float, default=5.0)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    report = {
        "federalAccount": args.federal_account,
        "fiscalYear": args.fy,
        "period": args.period,
        "startedAt": _now(),
        "timeoutHours": args.timeout_hours,
        "measurements": [],
    }
    out = Path(args.report)
    out.parent.mkdir(parents=True, exist_ok=True)

    def save():
        report["peakRssMb"] = _peak_rss_mb()
        out.write_text(json.dumps(report, indent=2) + "\n")

    account_id, detail = resolve_account(args.federal_account, args.fy)
    report["accountId"] = account_id
    report["accountTitle"] = detail.get("account_title") or detail.get("title")
    timeout = int(args.timeout_hours * 3600)
    kinds = args.kinds.split(",")
    try:
        if "file_b" in kinds:
            members, m = _measure(account_id, args.fy, args.period,
                                  "object_class_program_activity",
                                  FILE_B_COLUMNS, timeout)
            rows = [row for part in members.values() for row in part]
            m["programActivities"] = _pa_identities(rows)
            m["totalCents"] = sum(p["cents"] for p in m["programActivities"])
            report["measurements"].append(m)
            del members, rows
            save()
            print(json.dumps({k: v for k, v in m.items()
                              if k != "programActivities"}), flush=True)
        if "file_c" in kinds:
            members, m = _measure(account_id, args.fy, args.period,
                                  "award_financial", FILE_C_COLUMNS, timeout)
            shape_started = time.monotonic()
            m.update(_file_c_shape(members))
            m["shapeSeconds"] = round(time.monotonic() - shape_started, 1)
            m["peakRssMbAfterShape"] = _peak_rss_mb()
            report["measurements"].append(m)
            save()
            print(json.dumps({k: v for k, v in m.items()
                              if k != "programActivities"}), flush=True)
    except Exception as error:  # the partial report is the diagnosis
        report["error"] = f"{type(error).__name__}: {error}"
        report["finishedAt"] = _now()
        save()
        raise
    report["finishedAt"] = _now()
    save()


if __name__ == "__main__":
    main()
