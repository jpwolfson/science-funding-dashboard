#!/usr/bin/env python3
"""Build the independent obligation dashboard tree from account event stores."""

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from adapters.obligation_common import (
    account_period_status, aggregate, load_store, merge_period_status,
    write_dashboard,
)


def child_summary(path, name, abbrev, events, current_fy, covered_periods,
                  partial_fys, period_status=None, note=None):
    stats = aggregate(events, current_fy, covered_periods, partial_fys,
                      period_status)
    fy = next((row for row in stats["fiscalYears"] if row["fy"] == current_fy), None)
    summary = {"path": path, "name": name, "abbrev": abbrev, "hasData": bool(events),
            "currentFYNetObligations": fy["netObligations"] if fy else 0,
            "fileCToNetRatio": fy["fileCToNetRatio"] if fy else None,
            "distinctLinkedAwards": fy["distinctLinkedAwards"] if fy else 0}
    # interpretationNote (docs/verification-regime.md specialization schema):
    # an optional registry field, forwarded here so the site can render a row
    # note on any listing table for a child that carries one. Purely
    # field-driven -- no name or agency check.
    if note:
        summary["interpretationNote"] = note
    return summary


def agency_interpretation_note(accounts):
    """Uniform interpretationNote across every account in one agency, or None.

    Purely value-driven: if every account under the agency that declares a
    note declares the SAME note, that value propagates to the agency-level
    child summary (what the obligations landing table renders per agency).
    Distinct values across accounts join rather than silently pick one; no
    agency name is ever consulted.
    """
    notes = {a.get("interpretationNote") for a in accounts if a.get("interpretationNote")}
    if not notes:
        return None
    if len(notes) == 1:
        return next(iter(notes))
    return "; ".join(sorted(notes))


def account_availability(repo, account):
    baseline_path = account.get("baseline")
    if not baseline_path:
        raise ValueError(f"{account['path']}: missing baseline path")
    baseline = json.loads((repo / baseline_path).read_text())
    if baseline.get("schemaVersion") != 2:
        raise ValueError(f"{account['path']}: baseline schema must be v2")
    if baseline.get("federalAccount") != account["federalAccount"]:
        raise ValueError(f"{account['path']}: baseline account mismatch")
    return {
        int(fy) for fy, row in baseline["fiscalYears"].items()
        if row["status"] == "partial"
    }


def build(repo=REPO):
    repo = Path(repo)
    config = json.loads((repo / "config" / "obligation_accounts.json").read_text())
    data_root = repo / "data" / "obligations"
    freshness_max_days = int(config.get("refreshDefaults", {}).get(
        "freshnessMaxDays", 10
    ))
    account_rows = []
    account_freshness = {}
    agency_events = {}
    for account in config["accounts"]:
        base = data_root / account["path"]
        events = load_store(base / "events")
        if not events:
            continue
        current_fy = max(e["fiscalYear"] for e in events)
        covered_periods = {e["submissionPeriod"] for e in events}
        partial_fys = account_availability(repo, account)
        manifest = json.loads((base / "events" / "manifest.json").read_text())
        freshness = {
            "latestAcceptedAt": manifest.get("latestAcceptedAt"),
            "maxAgeDays": int(account.get("freshnessMaxDays", freshness_max_days)),
        }
        account_freshness[account["path"]] = freshness
        # Snapshot acceptance rule (docs/obligation-ledger.md "Snapshot
        # acceptance and not-reported periods"): recomputed once per
        # account, straight from committed provenance, and reused for the
        # account itself, every Program Activity child, and the agency/root
        # rollups below -- notReported is a File B/account-wide property,
        # not a per-Program-Activity one.
        period_status = account_period_status(base / "events", events, partial_fys)
        interpretation_note = account.get("interpretationNote")
        pa_children = []
        for pa in account["programActivities"]:
            pa_events = [e for e in events if (
                e["programActivityCode"], e["programActivityName"]
            ) == (pa["code"], pa["name"])]
            path = f"obligations/{account['path']}/{pa['slug']}"
            pa_metadata = {"federalAccount": account["federalAccount"],
                          "programActivityCode": pa["code"],
                          "freshness": freshness}
            if interpretation_note:
                pa_metadata["interpretationNote"] = interpretation_note
            write_dashboard(data_root / account["path"] / pa["slug"],
                {"level": "programActivity", "path": path, "name": pa["name"],
                 "abbrev": pa.get("abbrev", "")}, "USAspending File B and File C",
                pa_events, current_fy=current_fy,
                metadata=pa_metadata,
                covered_periods=covered_periods, partial_fys=partial_fys,
                period_status=period_status)
            # No `note` here: this child_summary feeds the account page's own
            # "Program activities" table, and the account page already shows
            # the note once, near the top -- repeating it as a per-PA-row
            # footnote (one for each of a dozen-plus activities) would be
            # exact-text repetition, not a useful row note. Each PA's own
            # dashboard.json still carries the field (pa_metadata above), so
            # visiting that PA's own page still shows the note.
            pa_children.append(child_summary(path, pa["name"], pa.get("abbrev", ""),
                                             pa_events, current_fy,
                                             covered_periods, partial_fys,
                                             period_status=period_status))
        known = {(pa["code"], pa["name"])
                 for pa in account["programActivities"]}
        unknown = sorted({(e["programActivityCode"], e["programActivityName"])
                          for e in events} - known)
        if unknown:
            raise ValueError(f"unregistered Program Activity codes: {unknown}")
        account_path = f"obligations/{account['path']}"
        account_metadata = {"federalAccount": account["federalAccount"],
                            "freshness": freshness}
        if interpretation_note:
            account_metadata["interpretationNote"] = interpretation_note
        write_dashboard(base, {"level": "account", "path": account_path,
            "name": account["name"], "abbrev": account["abbrev"]},
            "USAspending File B and File C", events, children=pa_children,
            current_fy=current_fy,
            metadata=account_metadata,
            covered_periods=covered_periods, partial_fys=partial_fys,
            period_status=period_status)
        agency_slug = account["path"].split("/")[0]
        agency_events.setdefault(agency_slug, []).extend(events)
        account_rows.append((account, events, current_fy, covered_periods,
                             partial_fys, period_status))

    agency_children = []
    for agency_slug, events in agency_events.items():
        accounts = [(a, ev, fy, periods, partial, status) for
                    a, ev, fy, periods, partial, status in account_rows
                    if a["path"].split("/")[0] == agency_slug]
        ids = [e["id"] for e in events]
        if len(ids) != len(set(ids)):
            raise ValueError(f"duplicate event IDs across {agency_slug} account stores")
        current_fy = max(e["fiscalYear"] for e in events)
        covered_periods = set().union(*(periods for _, _, _, periods, _, _ in accounts))
        partial_fys = set().union(*(partial for _, _, _, _, partial, _ in accounts))
        period_status = merge_period_status(status for _, _, _, _, _, status in accounts)
        children = [child_summary(f"obligations/{a['path']}", a["name"], a["abbrev"],
                                  ev, fy, periods, partial, period_status=status,
                                  note=a.get("interpretationNote"))
                    for a, ev, fy, periods, partial, status in accounts]
        agency_name = accounts[0][0]["agency"]
        accepted = [account_freshness[a["path"]].get("latestAcceptedAt")
                    for a, _, _, _, _, _ in accounts
                    if account_freshness[a["path"]].get("latestAcceptedAt")]
        agency_note = agency_interpretation_note([a for a, _, _, _, _, _ in accounts])
        agency_metadata = {"freshness": {"latestAcceptedAt": min(accepted) if accepted else None,
                                         "maxAgeDays": freshness_max_days}}
        if agency_note:
            agency_metadata["interpretationNote"] = agency_note
        write_dashboard(data_root / agency_slug,
            {"level": "agency", "path": f"obligations/{agency_slug}",
            "name": agency_name, "abbrev": agency_slug.upper()},
            "USAspending File B and File C", events, children=children,
            current_fy=current_fy, covered_periods=covered_periods,
            partial_fys=partial_fys, period_status=period_status,
            metadata=agency_metadata)
        agency_children.append(child_summary(f"obligations/{agency_slug}", agency_name,
                                             agency_slug.upper(), events, current_fy,
                                             covered_periods, partial_fys,
                                             period_status=period_status,
                                             note=agency_note))

    all_events = [e for events in agency_events.values() for e in events]
    if all_events:
        ids = [e["id"] for e in all_events]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate event IDs across obligation accounts")
        current_fy = max(e["fiscalYear"] for e in all_events)
        covered_periods = {e["submissionPeriod"] for e in all_events}
        partial_fys = set().union(*(partial for _, _, _, _, partial, _ in account_rows))
        period_status = merge_period_status(
            status for _, _, _, _, _, status in account_rows
        )
        accepted = [row.get("latestAcceptedAt")
                    for row in account_freshness.values()
                    if row.get("latestAcceptedAt")]
        # accountCount (Phase 3.2d remediation decision 4): the registered
        # account total, so the award root's coverage line and the
        # obligations landing/root-tile subtitle can derive their number
        # from data the site already loads instead of a hardcoded literal.
        write_dashboard(data_root, {"level": "root", "path": "obligations",
            "name": "Appropriations obligations"}, "USAspending File B and File C",
            all_events, children=agency_children, current_fy=current_fy,
            covered_periods=covered_periods, partial_fys=partial_fys,
            period_status=period_status,
            metadata={"freshness": {"latestAcceptedAt": min(accepted) if accepted else None,
                                     "maxAgeDays": freshness_max_days},
                      "accountCount": len(account_rows)})

    index_children = []
    for agency_slug, events in agency_events.items():
        account_nodes = []
        for account, _, _, _, _, _ in account_rows:
            if account["path"].split("/")[0] != agency_slug:
                continue
            account_nodes.append({"slug": account["path"].split("/")[-1],
                "name": account["name"], "abbrev": account["abbrev"],
                "path": account["path"], "children": [
                    {"slug": pa["slug"], "name": pa["name"],
                     "abbrev": pa.get("abbrev", ""),
                     "path": f"{account['path']}/{pa['slug']}", "children": []}
                    for pa in account["programActivities"]]})
        agency_name = next(a["agency"] for a, _, _, _, _, _ in account_rows
                           if a["path"].split("/")[0] == agency_slug)
        index_children.append({"slug": agency_slug, "name": agency_name,
                               "abbrev": agency_slug.upper(), "path": agency_slug,
                               "children": account_nodes})
    index = {"schemaVersion": 2,
             "generated": __import__("datetime").date.today().isoformat(),
             "root": {"slug": "", "abbrev": "", "name": "Appropriations obligations",
                      "path": "", "children": index_children}}
    data_root.mkdir(parents=True, exist_ok=True)
    (data_root / "index.json").write_text(json.dumps(index, indent=1) + "\n")
    return len(all_events)


if __name__ == "__main__":
    print(f"Built obligation dashboards from {build():,} events")
