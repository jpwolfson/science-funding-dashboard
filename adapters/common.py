"""Shared store, aggregation, and output logic for all source adapters and
for the rollup builder. The aggregation here is verbatim from the verified
DMS pipeline (reference/pull_nsf_dms.py); the site reads exactly this shape.

Award record shape used everywhere in this repo (the "store" shape):
  {id, date (ISO), month (YYYY-MM), amount (int), type (std|cont|fell|other),
   transType, title, awardee}
"""

import csv
import gzip
import io
import json
import re
from datetime import date, timedelta
from pathlib import Path

SERIES_START = date(2014, 10, 1)  # FY2015 onward

CSV_HEADER = ["id", "date", "estimatedTotalAmt", "transType", "title", "awardeeName"]


def norm_type(t):
    t = (t or "").lower()
    if t.startswith("standard"):
        return "std"
    if t.startswith("continuing"):
        return "cont"
    if t.startswith("fellowship"):
        return "fell"
    return "other"


def fiscal_year(d):
    return d.year + 1 if d.month >= 10 else d.year


def month_floor(d):
    return d.replace(day=1)


def months_back(d, n):
    y, m = d.year, d.month - n
    while m < 1:
        y, m = y - 1, m + 12
    return date(y, m, 1)


def month_windows(first, last):
    cur = first.replace(day=1)
    while cur <= last:
        nxt = (cur.replace(day=28) + timedelta(days=4)).replace(day=1)
        yield cur, min(nxt - timedelta(days=1), last)
        cur = nxt


def median(xs):
    xs = sorted(xs)
    n = len(xs)
    return 0 if n == 0 else (xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) // 2)


def _store_files(store_path):
    """Return committed CSV store files in deterministic merge order.

    Phase 1 leaves use one ``awards.csv``.  High-volume adapters use an
    ``awards/`` directory of deterministic ``FY####.csv.gz`` shards.  A
    caller may pass either the store itself or the containing leaf directory.
    """
    path = Path(store_path)
    if path.is_dir() and (path / "awards.csv").exists():
        return [path / "awards.csv"]
    if path.is_dir() and (path / "awards").is_dir():
        path = path / "awards"
    if path.is_file():
        return [path]
    if path.is_dir():
        return sorted((*path.glob("FY*.csv.gz"), *path.glob("FY*.csv")))
    return []


def store_exists(store_path):
    path = Path(store_path)
    if path.is_dir() and (path / "awards").is_dir():
        path = path / "awards"
    return bool(_store_files(path)) or (path / "manifest.json").exists()


def load_store(store_path):
    """Load a legacy CSV or a directory of fiscal-year gzip CSV shards."""
    store = {}
    for csv_path in _store_files(store_path):
        opener = gzip.open if csv_path.suffix == ".gz" else open
        with opener(csv_path, "rt", newline="") as fh:
            for row in csv.DictReader(fh):
                date.fromisoformat(row["date"])  # validate before trusting the row
                store[row["id"]] = {
                    "id": row["id"],
                    "date": row["date"],
                    "month": row["date"][:7],
                    "amount": int(row["estimatedTotalAmt"]),
                    "type": norm_type(row["transType"]),
                    "transType": row["transType"],
                    "title": row["title"],
                    "awardee": row["awardeeName"],
                }
    return store


def _write_rows(fh, awards):
    w = csv.writer(fh)
    w.writerow(CSV_HEADER)
    for a in sorted(awards, key=lambda a: (a["date"], a["id"])):
        w.writerow([a["id"], a["date"], a["amount"], a["transType"],
                    a["title"], a["awardee"]])


def write_store(store_path, awards):
    """Write a legacy CSV file or deterministic fiscal-year gzip shards.

    A path ending in ``.csv`` selects the Phase 1 format.  Any other path is
    a shard directory.  Existing shard years are rewritten even when empty,
    which prevents a record whose corrected date crosses a fiscal-year
    boundary from surviving in both files, while never deleting a stored ID.
    """
    path = Path(store_path)
    if path.suffix == ".csv":
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="") as fh:
            _write_rows(fh, awards)
        return

    path.mkdir(parents=True, exist_ok=True)
    by_fy = {}
    for award in awards:
        fy = fiscal_year(date.fromisoformat(award["date"]))
        by_fy.setdefault(fy, []).append(award)
    existing_years = set()
    for old in _store_files(path):
        match = re.fullmatch(r"FY(\d{4})\.csv(?:\.gz)?", old.name)
        if match:
            existing_years.add(int(match.group(1)))
    for fy in sorted(existing_years | set(by_fy)):
        shard = path / f"FY{fy}.csv.gz"
        with open(shard, "wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
                with io.TextIOWrapper(zipped, encoding="utf-8", newline="") as fh:
                    _write_rows(fh, by_fy.get(fy, []))
    manifest = {
        "format": "fiscal-year-csv-gzip-v1",
        "recordCount": len(awards),
        "fiscalYears": sorted(by_fy),
    }
    (path / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")


def aggregate(awards, today, series_start=SERIES_START):
    """Monthly and fiscal-year series in the exact shape the site consumes."""
    months = {}
    for a in awards:
        m = months.setdefault(a["month"], {"awards": 0, "dollars": 0,
                                           "std": 0, "cont": 0, "fell": 0, "other": 0})
        m["awards"] += 1
        m["dollars"] += a["amount"]
        m[a["type"]] += 1
    # Explicit zero rows so gaps read as 0, not missing data.
    for mstart, _ in month_windows(series_start, today):
        months.setdefault(mstart.strftime("%Y-%m"),
                          {"awards": 0, "dollars": 0, "std": 0, "cont": 0, "fell": 0, "other": 0})
    monthly = [{"month": k, **v} for k, v in sorted(months.items())]

    fys = {}
    for a in awards:
        d = date.fromisoformat(a["date"])
        fy = fys.setdefault(fiscal_year(d), {
            "awards": 0, "dollars": 0, "amounts": [],
            "oj": {"awards": 0, "dollars": 0, "std": 0, "cont": 0, "fell": 0, "other": 0},
        })
        fy["awards"] += 1
        fy["dollars"] += a["amount"]
        fy["amounts"].append(a["amount"])
        if d.month not in (8, 9):  # Oct-Jul basis for partial-year comparison
            fy["oj"]["awards"] += 1
            fy["oj"]["dollars"] += a["amount"]
            fy["oj"][a["type"]] += 1

    current_fy = fiscal_year(today)
    fy_rows = []
    for fy in sorted(fys):
        f = fys[fy]
        top3 = sorted((a for a in awards if fiscal_year(date.fromisoformat(a["date"])) == fy),
                      key=lambda a: -a["amount"])[:3]
        fy_rows.append({
            "fy": fy,
            "partial": fy == current_fy,
            "awards": f["awards"],
            "dollars": f["dollars"],
            "median": median(f["amounts"]),
            "exTop3Dollars": f["dollars"] - sum(a["amount"] for a in top3),
            "octJul": f["oj"],
            "top3": [{"id": a["id"], "title": a["title"], "awardee": a["awardee"],
                      "amount": a["amount"]} for a in top3],
        })

    # Cumulative FY-to-date overlays, last five fiscal years: weekly running
    # totals aligned by day-of-fiscal-year (day 0 = Oct 1), so leap years and
    # weekday drift never misalign the lines. Complete years end on Sep 30;
    # the current year ends at today. Endpoints therefore equal the
    # fiscal-year totals above exactly.
    fy_cum = []
    for fy in [f for f in sorted(fys) if current_fy - 5 < f <= current_fy]:
        fy_start = date(fy - 1, 10, 1)
        last_day = (min(date(fy, 9, 30), today) - fy_start).days
        daily = [[0, 0] for _ in range(last_day + 1)]
        for a in awards:
            d = (date.fromisoformat(a["date"]) - fy_start).days
            if 0 <= d <= last_day:
                daily[d][0] += 1
                daily[d][1] += a["amount"]
        pts, ca, cd = [], 0, 0
        for d in range(last_day + 1):
            ca += daily[d][0]
            cd += daily[d][1]
            if d % 7 == 6 or d == last_day:
                pts.append({"d": d, "awards": ca, "dollars": cd})
        fy_cum.append({"fy": fy, "partial": fy == current_fy, "points": pts})

    return {
        "totalAwards": len(awards),
        "currentFY": current_fy,
        "monthly": monthly,
        "fiscalYears": fy_rows,
        "fyCumulative": fy_cum,
    }


def write_dashboard(data_dir, node, source, awards, warnings, today,
                    children=None, series_start=SERIES_START, metadata=None):
    """Aggregate and write dashboard.json for one node (leaf or rollup).

    Invariant check: per-unit monthly counts may only grow. The store is
    never pruned, so a shrinking month means a code or merge bug — warn
    loudly (into the published warnings, so it surfaces on the site) rather
    than publish silently.
    """
    data_dir = Path(data_dir)
    warnings = list(warnings)
    agg = aggregate(awards, today, series_start)

    prev_path = data_dir / "dashboard.json"
    if prev_path.exists():
        prev = json.loads(prev_path.read_text())
        prev_counts = {m["month"]: m["awards"] for m in prev.get("monthly", [])}
        new_counts = {m["month"]: m["awards"] for m in agg["monthly"]}
        for month, n in sorted(prev_counts.items()):
            if new_counts.get(month, 0) < n:
                warnings.append(
                    f"invariant violated: {month} shrank from {n} to "
                    f"{new_counts.get(month, 0)} awards")

    out = {
        "generated": today.isoformat(),
        "node": node,
        "source": source,
        "warnings": warnings,
        **agg,
        "children": children if children is not None else [],
    }
    if metadata:
        out.update(metadata)
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "dashboard.json").write_text(json.dumps(out, indent=1))
    return warnings
