#!/usr/bin/env python3
"""Build rollup dashboards (directorate, agency, root) and the nav index.

Usage: python scripts/rollup.py

Reads config/orgs.json plus every leaf's committed data/<path>/awards.csv,
unions awards (deduped by award id — an award that moved between divisions
is counted once), and writes dashboard.json at each directorate, agency,
and the root, plus data/index.json for site navigation. Leaves with no data
yet are skipped from aggregation but still listed for nav.
"""

import json
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from adapters.common import load_store, write_dashboard  # noqa: E402

DATA = REPO_ROOT / "data"


def leaf_paths(directorate_path, directorate):
    return [f"{directorate_path}/{dv['slug']}" for dv in directorate["divisions"]]


def union_awards(paths, warnings):
    """Union leaf stores by award id. Returns list of award dicts."""
    by_id = {}
    dup_ids = set()
    for p in sorted(paths):
        for aid, a in load_store(DATA / p / "awards.csv").items():
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


def rollup_node(node_cfg, path, level, leaf_list, children_cfg, today):
    warnings = []
    for c in children_cfg:
        warnings.extend(child_warnings(c, f"{path}/{c['slug']}" if path else c["slug"]))
    awards = union_awards(leaf_list, warnings)
    children = [child_summary(c, f"{path}/{c['slug']}" if path else c["slug"])
                for c in children_cfg]
    pulled = sum(1 for p in leaf_list if (DATA / p / "awards.csv").exists())
    node = {"name": node_cfg["name"], "abbrev": node_cfg.get("abbrev", ""),
            "path": path, "level": level}
    source = (f"Aggregated from {pulled} division-level dataset(s) "
              f"({len(leaf_list)} configured); each division page documents "
              "its own API provenance.")
    write_dashboard(DATA / path if path else DATA, node, source, awards,
                    warnings, today, children=children)
    print(f"rollup {path or '(root)'}: {len(awards)} awards, "
          f"{pulled}/{len(leaf_list)} leaves with data, {len(warnings)} warnings")


def nav_node(cfg_node, path, children):
    return {"slug": cfg_node.get("slug", ""), "abbrev": cfg_node.get("abbrev", ""),
            "name": cfg_node["name"], "path": path,
            "active": cfg_node.get("active", True), "children": children}


def main():
    cfg = json.loads((REPO_ROOT / "config" / "orgs.json").read_text())
    today = date.today()

    nav_agencies = []
    all_leaves = []
    for ag in cfg["agencies"]:
        ag_leaves = []
        nav_dirs = []
        for dr in ag["directorates"]:
            dr_path = f"{ag['slug']}/{dr['slug']}"
            leaves = leaf_paths(dr_path, dr)
            ag_leaves.extend(leaves)
            rollup_node(dr, dr_path, "directorate", leaves, dr["divisions"], today)
            nav_dirs.append(nav_node(dr, dr_path, [
                nav_node(dv, f"{dr_path}/{dv['slug']}", [])
                for dv in dr["divisions"]]))
        rollup_node(ag, ag["slug"], "agency", ag_leaves, ag["directorates"], today)
        nav_agencies.append(nav_node(ag, ag["slug"], nav_dirs))
        all_leaves.extend(ag_leaves)

    root_cfg = {"name": "Federal science funding", "abbrev": ""}
    rollup_node(root_cfg, "", "root", all_leaves, cfg["agencies"], today)

    index = {"generated": today.isoformat(),
             "root": {**nav_node(root_cfg, "", nav_agencies)}}
    (DATA / "index.json").write_text(json.dumps(index, indent=1))
    print(f"Wrote data/index.json ({len(all_leaves)} leaves)")


if __name__ == "__main__":
    main()
