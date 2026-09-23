#!/usr/bin/env python3
"""Offline re-aggregation: rewrite every leaf's dashboard.json (and then all
rollups) from the already-committed award stores, with no API calls.

Usage: python scripts/reaggregate.py

For every division-tier leaf in config/orgs.json that has a
data/<unit> award store, reloads it and rewrites dashboard.json via the
same write_dashboard() path scripts/pull_unit.py uses -- so any change to
aggregate() (e.g. a new output key) reaches every leaf without a live pull.
Each leaf's node/source metadata is preserved by reading it back from that
leaf's *current* dashboard.json rather than recomputing it (this script has
no adapter context to rebuild it from). For a NIH leaf, awards whose id is
currently marked "excluded" in reference/nih_reporter_exclusions.json are
skipped from aggregation (the physical store keeps every row; this is a
soft delete) and previously published warnings are dropped and
recomputed fresh, since the retired month-shrink regime's warnings no
longer apply under the id-count invariant (adapters.common.write_dashboard).
Finishes by running scripts/rollup.py's build so directorate/agency/root
dashboards and data/index.json stay consistent with the rewritten leaves.
Each leaf's write_dashboard() call above does not carry forward a
previously stamped `refreshStatus` (Phase 3.2d remediation W17) -- but
rollup.main()'s own leaf-stamping pass (driven by the untouched
data/refresh_status.json, which this script never reads or writes) restamps
every configured leaf unconditionally before building any rollup, so an
offline rebuild never erases a published staleness disclosure.

This script only loads award stores read-only -- the stores are untouched.

`today` for offline re-aggregation is the date of this run (there is no pull
date to inherit). The current partial fiscal year's series therefore reflect
"as of today"; the next weekly CI pull refreshes them naturally.

write_dashboard() enforces a monotonic store-id-count invariant against each
leaf's existing dashboard.json: the physical store may only grow. This
script passes the *raw* (pre-exclusion) store size as store_id_count, so a
NIH leaf's newly-applied exclusion never trips it -- only a genuine drop in
the physical store would. Re-aggregating an unchanged store must never trip
it -- if it does, something about this script or aggregate() is wrong, so we
abort loudly rather than publish a leaf with unexplained new warnings.
"""

import json
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from adapters.common import load_store, store_exists, write_dashboard  # noqa: E402
from adapters.nih_reporter import METHODOLOGY_NOTE, excluded_ids  # noqa: E402
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
    nih_excluded = excluded_ids(REPO_ROOT)

    reaggregated = 0
    for unit_path, _division in leaf_units(cfg):
        data_dir = DATA / unit_path
        dash_path = data_dir / "dashboard.json"
        if not store_exists(data_dir):
            continue  # leaf never pulled; nothing to re-aggregate offline
        if not dash_path.exists():
            sys.exit(f"FATAL: award store at {data_dir} exists but "
                      f"{dash_path} does not; "
                      "cannot recover node/source metadata offline")
        prev = json.loads(dash_path.read_text())
        is_nih = unit_path.startswith("nih/")
        raw_awards = list(load_store(data_dir).values())
        awards = ([a for a in raw_awards if a["id"] not in nih_excluded]
                  if is_nih else raw_awards)
        metadata = {key: prev[key] for key in
                    ("provider", "dataComplete", "storeFormat", "amountNote",
                     "mechanismLabels")
                    if key in prev}
        if is_nih:
            # The retired month-shrink regime's warnings no longer apply
            # under the id-count invariant; start clean and let
            # write_dashboard recompute against the true store size.
            base_warnings = []
            metadata["methodologyNote"] = METHODOLOGY_NOTE
            metadata["dataQualityNotes"] = prev.get("dataQualityNotes", [])
        else:
            base_warnings = prev.get("warnings", [])
        warnings = write_dashboard(data_dir, prev["node"], prev["source"],
                                    awards, base_warnings, today,
                                    metadata=metadata,
                                    store_id_count=len(raw_awards))
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
