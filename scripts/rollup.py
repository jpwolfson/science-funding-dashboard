#!/usr/bin/env python3
"""Build rollup dashboards (directorate, agency, root) and the nav index.

Usage: python scripts/rollup.py

Reads config/orgs.json plus every leaf's committed CSV store (a legacy
awards.csv or compressed fiscal-year shards), unions awards, and writes
dashboard.json at each directorate, agency, and the root, plus data/index.json
for site navigation. Leaves with no data yet are skipped from aggregation but
still listed for nav.
"""

import json
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from adapters.common import load_store, store_exists, write_dashboard  # noqa: E402
from adapters.nih_reporter import reviewed_retraction_months_by_unit  # noqa: E402

DATA = REPO_ROOT / "data"


def leaf_paths(directorate_path, directorate):
    return [f"{directorate_path}/{dv['slug']}" for dv in directorate["divisions"]]


def union_awards(paths, warnings):
    """Union leaf stores by award id. Returns list of award dicts."""
    by_id = {}
    dup_ids = set()
    for p in sorted(paths):
        for aid, a in load_store(DATA / p).items():
            if aid in by_id:
                dup_ids.add(aid)
            else:
                by_id[aid] = a
    if dup_ids:
        warnings.append(f"{len(dup_ids)} awards appear in more than one "
                        "division; counted once in this rollup")
    return list(by_id.values())


def child_summary(child_cfg, child_path):
    """Summary row for the parent's children table, from the child's own
    dashboard.json (written by pull jobs for leaves, by this script for
    rollups — traversal is post-order so rollup children exist by then)."""
    entry = {"slug": child_cfg["slug"], "abbrev": child_cfg["abbrev"],
             "name": child_cfg["name"], "path": child_path,
             "active": child_cfg.get("active", True)}
    dash_path = DATA / child_path / "dashboard.json"
    if not dash_path.exists():
        return {**entry, "hasData": False, "totalAwards": 0, "currentFY": None,
                "octJulAwards": 0, "octJulDollars": 0,
                "avgOctJulAwards": None, "avgOctJulDollars": None}
    d = json.loads(dash_path.read_text())
    if not d.get("dataComplete", True):
        return {**entry, "hasData": False, "totalAwards": 0,
                "currentFY": d.get("currentFY"), "octJulAwards": 0,
                "octJulDollars": 0, "avgOctJulAwards": None,
                "avgOctJulDollars": None}
    cur = next((f for f in d["fiscalYears"] if f["fy"] == d["currentFY"]), None)
    base = [f for f in d["fiscalYears"] if 2015 <= f["fy"] <= 2024]
    # Label on the site is "FY15-24 avg": only claim it with near-full history.
    if len(base) >= 8:
        avg_awards = sum(f["octJul"]["awards"] for f in base) / len(base)
        avg_dollars = sum(f["octJul"]["dollars"] for f in base) / len(base)
    else:
        avg_awards = avg_dollars = None
    return {**entry, "hasData": True, "totalAwards": d["totalAwards"],
            "currentFY": d["currentFY"],
            "octJulAwards": cur["octJul"]["awards"] if cur else 0,
            "octJulDollars": cur["octJul"]["dollars"] if cur else 0,
            "avgOctJulAwards": avg_awards, "avgOctJulDollars": avg_dollars}


def child_warnings(child_cfg, child_path):
    dash_path = DATA / child_path / "dashboard.json"
    if not dash_path.exists():
        return []
    d = json.loads(dash_path.read_text())
    return [f"{child_cfg['abbrev']}: {w}" for w in d.get("warnings", [])]


def rollup_node(node_cfg, path, level, leaf_list, children_cfg, today,
                retraction_months):
    warnings = []
    for c in children_cfg:
        warnings.extend(child_warnings(c, f"{path}/{c['slug']}" if path else c["slug"]))
    awards = union_awards(leaf_list, warnings)
    children = [child_summary(c, f"{path}/{c['slug']}" if path else c["slug"])
                for c in children_cfg]
    pulled = sum(1 for p in leaf_list if store_exists(DATA / p))
    node = {"name": node_cfg["name"], "abbrev": node_cfg.get("abbrev", ""),
            "path": path, "level": level}
    source = (f"Aggregated from {pulled} leaf dataset(s) "
              f"({len(leaf_list)} configured); each source page documents "
              "its own API provenance.")
    providers = {p.split("/", 1)[0] for p in leaf_list}
    if providers == {"nih"}:
        metadata = {
            "provider": "nih",
            "amountNote": "Dollar figures are RePORTER award amounts, not outlays.",
            "mechanismLabels": {
                "std": "New/competing awards", "cont": "Noncompeting continuations",
                "fell": "Fellowships", "other": "Other awards",
            },
        }
        if len(leaf_list) == 1:
            metadata.update({"storeFormat": "fiscal-year-gzip",
                             "storePath": leaf_list[0]})
    elif providers == {"nsf"}:
        metadata = {
            "provider": "nsf",
            "amountNote": ("Dollar figures are intended totals "
                           "(estimatedTotalAmt), not outlays."),
            "mechanismLabels": {
                "std": "Standard grants", "cont": "Continuing grants",
                "fell": "Fellowships", "other": "Other awards",
            },
        }
    else:
        metadata = {
            "provider": "mixed",
            "amountNote": ("Dollar figures use each source's reported award "
                           "amount or intended total; they are not outlays."),
            "mechanismLabels": {
                "std": "New/standard awards", "cont": "Continuing awards",
                "fell": "Fellowships", "other": "Other awards",
            },
        }
    metadata["dataComplete"] = pulled == len(leaf_list)
    allowed_monthly_shrink = {}
    for leaf_path in leaf_list:
        for month, count in retraction_months.get(leaf_path, {}).items():
            allowed_monthly_shrink[month] = (
                allowed_monthly_shrink.get(month, 0) + count
            )
    if allowed_monthly_shrink:
        metadata["_allowedMonthlyShrink"] = allowed_monthly_shrink
    write_dashboard(DATA / path if path else DATA, node, source, awards,
                    warnings, today, children=children, metadata=metadata)
    print(f"rollup {path or '(root)'}: {len(awards)} awards, "
          f"{pulled}/{len(leaf_list)} leaves with data, {len(warnings)} warnings")


def nav_node(cfg_node, path, children):
    return {"slug": cfg_node.get("slug", ""), "abbrev": cfg_node.get("abbrev", ""),
            "name": cfg_node["name"], "path": path,
            "active": cfg_node.get("active", True), "children": children}


def main():
    cfg = json.loads((REPO_ROOT / "config" / "orgs.json").read_text())
    today = date.today()
    retraction_months = reviewed_retraction_months_by_unit(REPO_ROOT)

    nav_agencies = []
    all_leaves = []
    for ag in cfg["agencies"]:
        ag_leaves = []
        nav_dirs = []
        for dr in ag["directorates"]:
            dr_path = f"{ag['slug']}/{dr['slug']}"
            leaves = leaf_paths(dr_path, dr)
            passthrough = (ag["slug"] == "nih" and len(dr["divisions"]) == 1
                           and dr["divisions"][0]["slug"] == dr["slug"])
            visible_divisions = [] if passthrough else dr["divisions"]
            ag_leaves.extend(leaves)
            rollup_node(dr, dr_path, "directorate", leaves, visible_divisions,
                        today, retraction_months)
            nav_dirs.append(nav_node(dr, dr_path, [
                nav_node(dv, f"{dr_path}/{dv['slug']}", [])
                for dv in visible_divisions]))
        rollup_node(ag, ag["slug"], "agency", ag_leaves, ag["directorates"],
                    today, retraction_months)
        nav_agencies.append(nav_node(ag, ag["slug"], nav_dirs))
        all_leaves.extend(ag_leaves)

    root_cfg = {"name": "Federal science funding", "abbrev": ""}
    rollup_node(root_cfg, "", "root", all_leaves, cfg["agencies"], today,
                retraction_months)

    index = {"generated": today.isoformat(),
             "root": {**nav_node(root_cfg, "", nav_agencies)}}
    (DATA / "index.json").write_text(json.dumps(index, indent=1))
    print(f"Wrote data/index.json ({len(all_leaves)} leaves)")


if __name__ == "__main__":
    main()
