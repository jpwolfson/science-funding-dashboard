#!/usr/bin/env python3
"""Offline invariant checks for every committed award-ledger dashboard.json.

Award-ledger pages (NSF, NIH, and any future award-based source; distinct
from obligation-ledger pages, which carry ``"kind": "obligations"``, and the
sentinel page, which carries ``"kind": "sentinel"``) publish the same total
three different ways: a top-level ``totalAwards`` count, a per-fiscal-year
breakdown, and a monthly time series. They also publish a cumulative
FY-to-date overlay (``fyCumulative``) whose final point is supposed to equal
the corresponding fiscal-year row exactly. Nothing before this script
checked that those redundant figures agree with each other after every
regeneration.

This is the checker that would have caught the 2026-08-12 ``nih/od/od``
bug (a future-dated award pushed the ``fyCumulative`` endpoint one award
below its FY row; see docs/phase-history.md, "Post-completion notes"). It
must be committed and run every time, not re-derived ad hoc during a review
sweep.

No agency-conditional code paths: every check here reads only the generic
award-ledger dashboard schema (totalAwards, fiscalYears, monthly,
fyCumulative, children, node.level) that NSF, NIH, and any future
award-ledger source share. There is nothing agency-specific to declare, so
there is no registry/baseline parameter surface for this file (contrast
scripts/validate_obligations.py, whose per-account parameters live in
config/obligation_accounts.json and reference/*_obligation_baseline.json).
"""

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Dashboard "kind" values that are NOT award ledgers and must be skipped.
NON_AWARD_KINDS = {"obligations", "sentinel"}


def is_award_ledger(page):
    """Award-ledger dashboards have no "kind" field (the site JS defaults
    it to "awards") and carry a totalAwards figure; obligation and sentinel
    pages are explicitly kinded and structured differently."""
    return page.get("kind") not in NON_AWARD_KINDS and "totalAwards" in page


def check_dashboard(label, page):
    errors = []
    total = page.get("totalAwards")
    fy_rows = page.get("fiscalYears") or []
    monthly_rows = page.get("monthly") or []
    fy_sum = sum(row.get("awards", 0) for row in fy_rows)
    monthly_sum = sum(row.get("awards", 0) for row in monthly_rows)

    if total != fy_sum:
        errors.append(
            f"{label}: totalAwards {total} != sum(fiscalYears.awards) {fy_sum}"
        )
    if total != monthly_sum:
        errors.append(
            f"{label}: totalAwards {total} != sum(monthly.awards) {monthly_sum}"
        )

    fy_by_year = {row.get("fy"): row for row in fy_rows}
    for series in page.get("fyCumulative") or []:
        fy = series.get("fy")
        points = series.get("points") or []
        if not points:
            continue
        endpoint = points[-1]
        row = fy_by_year.get(fy)
        if row is None:
            errors.append(
                f"{label} FY{fy}: fyCumulative series has no matching fiscalYears row"
            )
            continue
        if (endpoint.get("awards"), endpoint.get("dollars")) != (
                row.get("awards"), row.get("dollars")):
            errors.append(
                f"{label} FY{fy}: fyCumulative endpoint "
                f"(awards={endpoint.get('awards')}, dollars={endpoint.get('dollars')}) "
                f"!= fiscalYears row (awards={row.get('awards')}, dollars={row.get('dollars')})"
            )

    # Rollup-equals-children check: only where cheaply and exactly verifiable
    # from committed data without re-deriving source overlap rules, i.e. the
    # root node, whose children (agencies) are a disjoint union by construction.
    node = page.get("node") or {}
    children = page.get("children") or []
    if node.get("level") == "root" and children:
        child_total = sum(child.get("totalAwards", 0) for child in children)
        if total != child_total:
            errors.append(
                f"{label}: root totalAwards {total} != "
                f"sum(children.totalAwards) {child_total}"
            )

    return errors


def validate(repo=REPO):
    repo = Path(repo)
    errors = []
    checked = []
    data_root = repo / "data"
    for path in sorted(data_root.rglob("dashboard.json")) if data_root.exists() else []:
        page = json.loads(path.read_text())
        if not is_award_ledger(page):
            continue
        label = str(path.relative_to(repo))
        checked.append(label)
        errors.extend(check_dashboard(label, page))
    return errors, checked


def main():
    errors, checked = validate()
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        raise SystemExit(
            f"award invariant validation failed with {len(errors)} error(s) "
            f"across {len(checked)} award-ledger dashboard(s)"
        )
    print(
        f"Award invariant validation passed "
        f"({len(checked)} award-ledger dashboard(s): totalAwards == "
        f"sum(fiscalYears) == sum(monthly); fyCumulative endpoints exact; "
        f"root == sum(children))"
    )


if __name__ == "__main__":
    main()
