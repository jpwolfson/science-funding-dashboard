#!/usr/bin/env python3
"""Pull one org unit (division-tier leaf) and write its data subtree.

Usage: python scripts/pull_unit.py --unit nsf/mps/dms [--full]

Reads config/orgs.json, dispatches to the agency's adapter, and writes
data/<unit>/awards.csv + data/<unit>/dashboard.json. Exits nonzero (writing
nothing) on any plausibility failure inside the adapter.
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from adapters import nsf  # noqa: E402
from adapters.common import write_dashboard, write_store  # noqa: E402

ADAPTERS = {"nsf": nsf}


def load_config():
    return json.loads((REPO_ROOT / "config" / "orgs.json").read_text())


def find_unit(cfg, unit_path):
    """Returns (agency, directorate, division) dicts for 'ag/dir/div'."""
    parts = unit_path.strip("/").split("/")
    if len(parts) != 3:
        sys.exit(f"unit must be agency/directorate/division, got: {unit_path}")
    for ag in cfg["agencies"]:
        if ag["slug"] != parts[0]:
            continue
        for dr in ag["directorates"]:
            if dr["slug"] != parts[1]:
                continue
            for dv in dr["divisions"]:
                if dv["slug"] == parts[2]:
                    return ag, dr, dv
    sys.exit(f"unit not found in config/orgs.json: {unit_path}")


def resolved_checks(cfg, division):
    checks = dict(cfg.get("defaults", {}))
    checks.setdefault("max_monthly", 1500)
    checks.setdefault("min_total", 0)
    checks.setdefault("max_total", 200000)
    checks.update(division.get("checks", {}))
    return checks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--unit", required=True, help="e.g. nsf/mps/dms")
    ap.add_argument("--full", action="store_true",
                    help="re-pull the full history (reconciles amendments)")
    args = ap.parse_args()

    cfg = load_config()
    agency, directorate, division = find_unit(cfg, args.unit)
    unit_path = args.unit.strip("/")
    data_dir = REPO_ROOT / "data" / unit_path
    adapter = ADAPTERS.get(agency["adapter"])
    if adapter is None:
        sys.exit(f"unknown adapter: {agency['adapter']}")

    unit_cfg = dict(division)
    unit_cfg["checks"] = resolved_checks(cfg, division)
    today = date.today()

    awards, warnings, source = adapter.pull_unit(
        unit_cfg, data_dir / "awards.csv", full=args.full, today=today,
        repo_root=REPO_ROOT)

    node = {"name": division["name"], "abbrev": division["abbrev"],
            "path": unit_path, "level": "division"}
    write_store(data_dir / "awards.csv", awards)
    all_warnings = write_dashboard(data_dir, node, source, awards, warnings, today)
    print(f"Wrote {data_dir}/dashboard.json and awards.csv "
          f"({len(awards)} awards, {len(all_warnings)} warnings)")


if __name__ == "__main__":
    main()
