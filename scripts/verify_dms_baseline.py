#!/usr/bin/env python3
"""Phase-1 acceptance gate: DMS must reproduce the verified baseline EXACTLY.

Compares data/nsf/mps/dms/awards.csv monthly counts and intended-dollar sums
against reference/verified_baseline.json (hand-verified 2026-08-07):
  - months before 2026-07: count and dollars must match exactly;
  - 2026-07 onward: count may only meet or exceed the baseline (NSF
    backfills trailing months).

Exit 1 with a diff table on any mismatch. Note: dollar amounts drift over
time as NSF amends awards upward, so this exact gate is meaningful near the
baseline's verification date; the ongoing tolerance-based drift check lives
in the adapter (checks.baseline).
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from adapters.common import load_store  # noqa: E402

CUTOVER = "2026-07"  # baseline trailing months still growing at verification


def main():
    store = load_store(REPO_ROOT / "data" / "nsf" / "mps" / "dms" / "awards.csv")
    if not store:
        sys.exit("FATAL: no DMS store at data/nsf/mps/dms/awards.csv")
    baseline = json.loads(
        (REPO_ROOT / "reference" / "verified_baseline.json").read_text())["months"]

    counts, dollars = {}, {}
    for a in store.values():
        counts[a["month"]] = counts.get(a["month"], 0) + 1
        dollars[a["month"]] = dollars.get(a["month"], 0) + a["amount"]

    failures = []
    for month in sorted(baseline):
        base_n, base_d = baseline[month]
        got_n, got_d = counts.get(month, 0), dollars.get(month, 0)
        if month < CUTOVER:
            if got_n != base_n:
                failures.append(f"{month}: count {got_n} != baseline {base_n}")
            if got_d != base_d:
                failures.append(f"{month}: dollars {got_d} != baseline {base_d}")
        elif got_n < base_n:
            failures.append(f"{month}: count {got_n} < baseline {base_n} "
                            "(trailing months may only grow)")
    extra = sorted(set(counts) - set(baseline))
    for month in extra:
        if month < CUTOVER:
            failures.append(f"{month}: {counts[month]} awards in a month "
                            "absent from the baseline")

    checked = sum(1 for m in baseline if m < CUTOVER)
    if failures:
        print(f"DMS BASELINE VERIFICATION FAILED ({len(failures)} mismatches, "
              f"{checked} strict months checked):")
        for f in failures:
            print(f"  {f}")
        sys.exit(1)
    print(f"DMS baseline verification PASSED: {checked} months exact, "
          f"{len(baseline) - checked} trailing months >= baseline, "
          f"{len(store)} awards in store.")


if __name__ == "__main__":
    main()
