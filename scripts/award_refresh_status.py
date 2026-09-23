#!/usr/bin/env python3
"""Build data/refresh_status.json from this run's pull-ok markers.

Phase 3.2d remediation W17 (the award-ledger analogue of W12's
scripts/reconcile_obligation_artifacts.py). Run in update-data.yml's
rollup job, BEFORE scripts/rollup.py: every unit the plan job's nsf_matrix
+ nih_matrix planned this run either uploaded a `_pull_ok/<slug>.json`
marker (its pull job reached the commit/push step successfully) or did
not (the pull job was refused, timed out, or lost the push -- any earlier
failure). A planned unit with no marker is published as a disclosed
``stale`` unit instead of vetoing the whole rollup; see
docs/nih-data-validation.md, "Award refresh, freshness, and publication
(W17)".

Usage (as invoked by .github/workflows/update-data.yml):
    NSF_MATRIX=... NIH_MATRIX=... python scripts/award_refresh_status.py \
        --markers-dir _pull_ok
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from adapters.award_refresh import (  # noqa: E402
    build_refresh_status, check_all_missing, write_refresh_status,
)


def _load_matrix(env_var):
    """Unit paths from a plan-job matrix output (the same
    {"include": [{"unit": ...}, ...]} shape update-data.yml's `plan` job
    writes to nsf_matrix/nih_matrix), or [] if the env var is unset/empty
    (a run that planned no units of that adapter)."""
    raw = os.environ.get(env_var)
    if not raw:
        return []
    data = json.loads(raw)
    return [entry["unit"] for entry in data.get("include", [])]


def load_markers(markers_dir):
    """{unit path: marker dict} from every `<slug>.json` file in
    ``markers_dir`` (the merged download of every `pull-ok-<slug>` upload-
    artifact this run produced). Missing or empty is fine -- it just means
    no pull job reached its success-marker step."""
    markers = {}
    directory = Path(markers_dir)
    if not directory.is_dir():
        return markers
    for marker_path in sorted(directory.glob("*.json")):
        try:
            entry = json.loads(marker_path.read_text())
        except json.JSONDecodeError:
            continue
        unit = entry.get("unit")
        if unit:
            markers[unit] = entry
    return markers


def _write_job_summary(stale_entries):
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    with open(summary_path, "a", encoding="utf-8") as handle:
        handle.write("## Award refresh: tolerated pull failures\n\n")
        if not stale_entries:
            handle.write("Every planned unit produced a pull-ok marker.\n\n")
            return
        handle.write(
            "The committed store for each unit below is retained unchanged; "
            "the next scheduled pull will retry it.\n\n"
        )
        handle.write("| Unit | Stale since |\n|---|---|\n")
        for path in sorted(stale_entries):
            handle.write(f"| {path} | {stale_entries[path]['staleSince']} |\n")
        handle.write("\n")


def run(repo=REPO, markers_dir="_pull_ok", generated_at=None):
    repo = Path(repo)
    orgs_cfg = json.loads((repo / "config" / "orgs.json").read_text())
    planned = _load_matrix("NSF_MATRIX") + _load_matrix("NIH_MATRIX")
    markers = load_markers(markers_dir)

    check_all_missing(planned, markers)

    if generated_at is None:
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entries = build_refresh_status(repo, orgs_cfg, planned, markers, generated_at)
    write_refresh_status(repo, entries, generated_at)

    stale = {path: entry for path, entry in entries.items()
             if entry.get("status") == "stale"}
    for path in sorted(stale):
        entry = stale[path]
        print(f"STALE (pull failed): {path} since {entry['staleSince']}, "
              "committed store retained")
    _write_job_summary(stale)
    print(f"{len(stale)} of {len(planned)} planned unit(s) stale this run; "
          f"{len(entries)} unit(s) total in data/refresh_status.json")
    return entries


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--markers-dir", default="_pull_ok",
                        help="directory of downloaded pull-ok-* markers")
    parser.add_argument("--repo", default=str(REPO))
    args = parser.parse_args()
    try:
        run(repo=args.repo, markers_dir=args.markers_dir)
    except ValueError as exc:
        raise SystemExit(str(exc))


if __name__ == "__main__":
    main()
