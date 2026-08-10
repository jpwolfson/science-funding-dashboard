#!/usr/bin/env python3
"""Offline re-aggregation: rewrite every leaf's dashboard.json (and then all
rollups) from the already-committed awards.csv stores, with no API calls.

Usage: python scripts/reaggregate.py

For every division-tier leaf in config/orgs.json that has a
data/<unit>/awards.csv, reloads the store and rewrites dashboard.json via the
same write_dashboard() path scripts/pull_unit.py uses -- so any change to
aggregate() (e.g. a new output key) reaches every leaf without a live pull.
Each leaf's node/source metadata is preserved by reading it back from that
leaf's *current* dashboard.json rather than recomputing it (this script has
no adapter context to rebuild it from). Existing published warnings are
carried forward too; this is a re-aggregation, not a re-pull, so there is no
new information to warn about. Finishes by running scripts/rollup.py's build
so directorate/agency/root dashboards and data/index.json stay consistent
with the rewritten leaves.

This script never reads or writes any awards.csv content other than loading
it read-only via adapters.common.load_store -- the store itself is untouched.

`today` for offline re-aggregation is the date of this run (there is no pull
date to inherit). The current partial fiscal year's series therefore reflect
"as of today"; the next weekly CI pull refreshes them naturally.

write_dashboard() enforces a monotonic monthly-award-count invariant against
each leaf's existing dashboard.json. Re-aggregating an unchanged store must
never trip it -- if it does, something about this script or aggregate() is
wrong, so we abort loudly rather than publish a leaf with unexplained new
warnings.
"""

import json
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from adapters.common import load_store, write_dashboard  # noqa: E402
import rollup  # scripts/rollup.py, run after every leaf is rewritten  # noqa: E402

DATA = REPO_ROOT / "data"


def leaf_units(cfg):
    """Yields (unit_path, division_cfg) for every division-tier leaf."""
    for ag in cfg["agencies"]:
        for dr in ag["directorates"]:
            for dv in dr["divisions"]:
                yield f"{ag['slug']}/{dr['slug']}/{dv['slug']}", dv


def main():
    cfg = json.loads((REPO_ROOT / "config" / "orgs.json").read_text())
    today = date.today()

    reaggregated = 0
    for unit_path, _division in leaf_units(cfg):
        data_dir = DATA / unit_path
        csv_path = data_dir / "awards.csv"
        dash_path = data_dir / "dashboard.json"
        if not csv_path.exists():
            continue  # leaf never pulled; nothing to re-aggregate offline
        if not dash_path.exists():
            sys.exit(f"FATAL: {csv_path} exists but {dash_path} does not; "
                      "cannot recover node/source metadata offline")
        prev = json.loads(dash_path.read_text())
        awards = list(load_store(csv_path).values())
        warnings = write_dashboard(data_dir, prev["node"], prev["source"],
                                    awards, prev.get("warnings", []), today)
        new_invariant_warnings = [w for w in warnings if w.startswith("invariant violated")]
        if new_invariant_warnings:
            sys.exit(
                f"FATAL: re-aggregating an unchanged store at {unit_path} produced "
                f"new invariant warnings -- stop and investigate: {new_invariant_warnings}")
        reaggregated += 1
    print(f"Re-aggregated {reaggregated} leaf dashboard(s) from committed stores, "
          f"0 new invariant warnings")

    rollup.main()


if __name__ == "__main__":
    main()
