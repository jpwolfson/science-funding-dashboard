#!/usr/bin/env python3
"""Plan registry-driven obligation account × fiscal-year refreshes."""

import argparse
import json
from datetime import date
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent


def source_period(today, lag_months):
    """Return the newest reporting FY/period expected after a whole-month lag."""
    month_index = today.year * 12 + today.month - 1 - int(lag_months)
    year, zero_month = divmod(month_index, 12)
    month = zero_month + 1
    fiscal_year = year + 1 if month >= 10 else year
    fiscal_period = ((month - 10) % 12) + 1
    return fiscal_year, fiscal_period


def _accounts(config, selectors):
    accounts = config["accounts"]
    if selectors == "all":
        return accounts
    wanted = [value.strip().strip("/") for value in selectors.split(",") if value.strip()]
    unknown = [value for value in wanted if not any(
        row["path"] == value or row["path"].startswith(value + "/")
        for row in accounts
    )]
    if unknown:
        raise ValueError(f"unknown obligation account paths/prefixes: {unknown}")
    return [row for row in accounts if any(
        row["path"] == value or row["path"].startswith(value + "/")
        for value in wanted
    )]


def _load_baseline(repo, account):
    path = repo / account["baseline"]
    baseline = json.loads(path.read_text())
    if baseline.get("schemaVersion") != 2:
        raise ValueError(f"{account['path']}: baseline schema must be v2")
    if baseline.get("federalAccount") != account["federalAccount"]:
        raise ValueError(f"{account['path']}: baseline account mismatch")
    return baseline


def plan(repo=REPO, mode="weekly", selectors="all", today=None,
         from_fy=None, to_fy=None, current_period=None):
    repo = Path(repo)
    today = today or date.today()
    config = json.loads((repo / "config" / "obligation_accounts.json").read_text())
    if config.get("schemaVersion") != 2:
        raise ValueError("obligation account registry schema must be v2")
    defaults = config.get("refreshDefaults", {})
    jobs = []
    for account in _accounts(config, selectors):
        desired_fy, desired_period = source_period(
            today, account.get(
                "reportingLagMonths", defaults.get("reportingLagMonths", 2)
            )
        )
        baseline = _load_baseline(repo, account)
        available = {
            int(fy): row for fy, row in baseline["fiscalYears"].items()
            if row.get("status") in {"complete", "partial"}
        }
        selected = []
        if mode == "full":
            selected = [(fy, int(row.get("asOfPeriod", 12)), "historical")
                        for fy, row in sorted(available.items())]
        elif mode == "custom":
            if from_fy is None or to_fy is None or to_fy < from_fy:
                raise ValueError("custom mode requires a valid --from-fy/--to-fy range")
            for fy in range(from_fy, to_fy + 1):
                row = available.get(fy)
                if not row:
                    raise ValueError(f"{account['path']}: FY{fy} is not source-available")
                period = (int(current_period) if fy == to_fy and current_period
                          else int(row.get("asOfPeriod", 12)))
                selected.append((fy, period, "custom"))
        elif mode == "weekly":
            # P01 is not a public submission. Until P02 is expected, refresh
            # the prior P12 snapshot so corrections are still observed.
            if desired_period == 1:
                current_fy = max(fy for fy in available if fy < desired_fy)
                period = 12
            else:
                current_fy, period = desired_fy, desired_period
                existing = available.get(current_fy)
                if existing:
                    period = max(period, int(existing.get("asOfPeriod", 2)))
            selected.append((current_fy, period, "current"))
            historical = sorted(fy for fy in available if fy != current_fy)
            if historical:
                index = today.isocalendar().week % len(historical)
                fy = historical[index]
                selected.append((fy, int(available[fy].get("asOfPeriod", 12)),
                                 "rotating-historical"))
        else:
            raise ValueError(f"unsupported refresh mode: {mode}")

        for fy, period, purpose in selected:
            if not 2 <= period <= 12:
                raise ValueError(f"{account['path']} FY{fy}: invalid period P{period:02}")
            jobs.append({
                "account": account["path"],
                "artifact": account["path"].replace("/", "--"),
                "fiscalYear": fy,
                "period": period,
                "purpose": purpose,
                "baseline": account["baseline"],
            })
    jobs.sort(key=lambda row: (row["account"], row["fiscalYear"]))
    return {"include": jobs}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("weekly", "full", "custom"),
                        default="weekly")
    parser.add_argument("--accounts", default="all")
    parser.add_argument("--from-fy", type=int)
    parser.add_argument("--to-fy", type=int)
    parser.add_argument("--current-period", type=int)
    parser.add_argument("--as-of")
    args = parser.parse_args()
    today = date.fromisoformat(args.as_of) if args.as_of else None
    print(json.dumps(plan(
        mode=args.mode, selectors=args.accounts, today=today,
        from_fy=args.from_fy, to_fy=args.to_fy,
        current_period=args.current_period,
    ), separators=(",", ":")))


if __name__ == "__main__":
    main()
