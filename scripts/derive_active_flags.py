#!/usr/bin/env python3
"""Derive each unit's active flag and note from its own pulled award data.

Discovery cannot reliably classify activity (its recent-window probes were
flaky), so the store of record decides: a unit is active iff it has an
award dated within the trailing window (default 24 months). Inactive units
get a note stating the last award date. Run after a full backfill; commit
the config change and re-run scripts/rollup.py so the nav picks it up.

Usage: python scripts/derive_active_flags.py [--months 24]
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from adapters.common import load_store, months_back  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--months", type=int, default=24)
    args = ap.parse_args()
    cutoff = months_back(date.today(), args.months).isoformat()

    cfg_path = REPO_ROOT / "config" / "orgs.json"
    cfg = json.loads(cfg_path.read_text())
    changed = 0
    for ag in cfg["agencies"]:
        for dr in ag["directorates"]:
            for dv in dr["divisions"]:
                path = REPO_ROOT / "data" / ag["slug"] / dr["slug"] / dv["slug"]
                store = load_store(path / "awards.csv")
                if not store:
                    print(f"  {dv['abbrev']:6s} no data yet; leaving "
                          f"active={dv.get('active', True)}")
                    continue
                last = max(a["date"] for a in store.values())
                active = last >= cutoff
                note = None if active else (
                    f"No awards since {last}; unit appears dormant or "
                    "reorganized (kept for its historical awards).")
                if dv.get("active") != active or dv.get("note") != note:
                    changed += 1
                dv["active"] = active
                if note:
                    dv["note"] = note
                else:
                    dv.pop("note", None)
                print(f"  {dv['abbrev']:6s} last award {last}  active={active}")
    cfg_path.write_text(json.dumps(cfg, indent=1))
    print(f"Updated config/orgs.json ({changed} entries changed, "
          f"cutoff {cutoff})")


if __name__ == "__main__":
    main()
