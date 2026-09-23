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

Also fail-closed on data/refresh_status.json (Phase 3.2d remediation W17,
the award-ledger analogue of scripts/validate_obligations.py's
data/obligations/refresh_status.json checks): the file must parse to
schema 1, every stale entry must be properly disclosed (a YYYY-MM-DD
staleSince and a non-empty reason -- an unmarked/bare stale is an error),
every unit key must be a configured leaf, and every dashboard's own
refreshStatus field must match what data/refresh_status.json says it
should be. See docs/nih-data-validation.md, "Award refresh, freshness,
and publication (W17)".
"""

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from adapters.award_refresh import node_leaf_map  # noqa: E402

# Dashboard "kind" values that are NOT award ledgers and must be skipped.
NON_AWARD_KINDS = {"obligations", "sentinel"}

STALE_SINCE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


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


def check_refresh_status_file(repo, leaf_set):
    """Parse and validate data/refresh_status.json itself (Phase 3.2d
    remediation W17): schema, well-formed stale entries, configured unit
    keys. Missing entirely is fine -- it means every unit is fresh.
    Returns (errors, units-dict)."""
    errors = []
    path = Path(repo) / "data" / "refresh_status.json"
    if not path.exists():
        return errors, {}
    try:
        raw = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return [f"data/refresh_status.json: invalid JSON: {exc}"], {}
    if raw.get("schemaVersion") != 1:
        errors.append(
            f"data/refresh_status.json: schemaVersion "
            f"{raw.get('schemaVersion')!r}, expected 1"
        )
    units = raw.get("units")
    if not isinstance(units, dict):
        errors.append("data/refresh_status.json: units must be an object")
        return errors, {}
    for unit_path, entry in units.items():
        if leaf_set and unit_path not in leaf_set:
            errors.append(
                f"data/refresh_status.json: unit key {unit_path!r} is not "
                "a configured leaf in config/orgs.json"
            )
        if not isinstance(entry, dict):
            errors.append(
                f"data/refresh_status.json: {unit_path}: entry must be an object"
            )
            continue
        if entry.get("status") != "stale":
            continue
        stale_since = entry.get("staleSince")
        if not (isinstance(stale_since, str) and STALE_SINCE_RE.match(stale_since)):
            errors.append(
                f"data/refresh_status.json: {unit_path}: stale entry has "
                f"invalid staleSince {stale_since!r} (expected YYYY-MM-DD) "
                "-- an unmarked/bare stale is not allowed"
            )
        if not entry.get("reason"):
            errors.append(
                f"data/refresh_status.json: {unit_path}: stale entry has no "
                "reason -- an unmarked/bare stale is not allowed"
            )
    return errors, units


def check_refresh_consistency(pages_by_path, leaves_under, refresh_status, leaf_set):
    """Every committed award-ledger dashboard's own refreshStatus field
    must agree exactly with what data/refresh_status.json + the org
    registry say it should be (Phase 3.2d remediation W17):

    - a configured leaf's refreshStatus is {**entry, "unit": path} when
      the unit is stale, and absent when it is fresh;
    - a rollup node's (directorate/agency/root) refreshStatus is present
      if and only if at least one leaf it aggregates is stale;
    - every child row in a dashboard's own `children` table carries the
      same refreshStatus as that child's own dashboard (or none, if the
      child's dashboard carries none)."""
    errors = []
    for node_path, leaves in leaves_under.items():
        found = pages_by_path.get(node_path)
        if found is None:
            continue  # dashboard not committed for this node yet
        label, page = found
        page_refresh = page.get("refreshStatus")
        if node_path in leaf_set:
            entry = refresh_status.get(node_path) or {}
            if entry.get("status") == "stale":
                expected = {**entry, "unit": node_path}
                if page_refresh != expected:
                    errors.append(
                        f"{label}: refreshStatus {page_refresh!r} does not "
                        f"match data/refresh_status.json entry {expected!r}"
                    )
            elif page_refresh is not None:
                errors.append(
                    f"{label}: refreshStatus is present but this unit is "
                    "not stale in data/refresh_status.json"
                )
        else:
            stale_leaves = [
                leaf for leaf in leaves
                if (refresh_status.get(leaf) or {}).get("status") == "stale"
            ]
            if stale_leaves and page_refresh is None:
                errors.append(
                    f"{label}: {len(stale_leaves)} descendant leaf unit(s) "
                    f"({stale_leaves}) are stale but this rollup carries no "
                    "refreshStatus"
                )
            elif not stale_leaves and page_refresh is not None:
                errors.append(
                    f"{label}: refreshStatus is present but no descendant "
                    "leaf unit is stale"
                )
        for child in page.get("children") or []:
            child_found = pages_by_path.get(child.get("path"))
            if child_found is None:
                continue
            _child_label, child_page = child_found
            child_dashboard_refresh = child_page.get("refreshStatus")
            row_refresh = child.get("refreshStatus")
            if row_refresh != child_dashboard_refresh:
                errors.append(
                    f"{label}: child row {child.get('path')!r} refreshStatus "
                    f"{row_refresh!r} does not match its own dashboard's "
                    f"refreshStatus {child_dashboard_refresh!r}"
                )
    return errors


def validate(repo=REPO):
    repo = Path(repo)
    errors = []
    checked = []
    data_root = repo / "data"
    orgs_path = repo / "config" / "orgs.json"
    orgs_cfg = None
    if orgs_path.exists():
        try:
            orgs_cfg = json.loads(orgs_path.read_text())
        except json.JSONDecodeError as exc:
            errors.append(f"config/orgs.json: invalid JSON: {exc}")

    leaves_under = node_leaf_map(orgs_cfg) if orgs_cfg else {}
    leaf_set = set(leaves_under.get("", []))

    refresh_status_errors, refresh_status = check_refresh_status_file(repo, leaf_set)
    errors.extend(refresh_status_errors)

    pages_by_path = {}
    for path in sorted(data_root.rglob("dashboard.json")) if data_root.exists() else []:
        page = json.loads(path.read_text())
        if not is_award_ledger(page):
            continue
        label = str(path.relative_to(repo))
        checked.append(label)
        errors.extend(check_dashboard(label, page))
        node_path = (page.get("node") or {}).get("path")
        if node_path is not None:
            pages_by_path[node_path] = (label, page)

    if orgs_cfg:
        errors.extend(check_refresh_consistency(
            pages_by_path, leaves_under, refresh_status, leaf_set))

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
