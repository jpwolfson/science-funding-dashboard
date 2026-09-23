#!/usr/bin/env python3
"""Fail-closed validation for committed NIH award stores.

Offline checks validate shard/manifests, dashboard totals, configured volume
ranges, cross-institute uniqueness, and independent NIH Data Book benchmarks.
``--live`` adds one orthogonal multi-year RePORTER count query per institute;
this is intentionally a different query shape from the per-year paginated pull.
"""

import argparse
import csv
import gzip
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from adapters.award_refresh import (  # noqa: E402
    default_entry, is_marked_stale, load_refresh_status,
)
from adapters.common import SERIES_START, fiscal_year  # noqa: E402
from adapters.nih_reporter import (  # noqa: E402
    CHANGES_HEADER, FUNDING_MECHANISMS, INCLUDE_FIELDS, LIVE_GAP_ABS_MIN,
    LIVE_GAP_REL_FRACTION, METHODOLOGY_NOTE, NihReporterPull, api_post,
    changes_ledger_path, load_exclusion_ledger, parse_trans_type,
    retained_missing_count,
)

DATA = REPO_ROOT / "data"
CONFIG = REPO_ROOT / "config" / "orgs.json"
DATA_BOOK_BASELINE = REPO_ROOT / "reference" / "nih_databook_baseline.json"
DATA_BOOK_EXCLUDED_MECHANISMS = {
    "r and d contracts", "interagency agreements", "intramural",
}


def nih_units(cfg):
    agency = next(a for a in cfg["agencies"] if a["slug"] == "nih")
    defaults = dict(cfg.get("defaults", {}))
    defaults.update(agency.get("checks", {}))
    for directorate in agency["directorates"]:
        for division in directorate["divisions"]:
            checks = dict(defaults)
            checks.update(directorate.get("checks", {}))
            checks.update(division.get("checks", {}))
            yield {
                "path": f"nih/{directorate['slug']}/{division['slug']}",
                "agency": division["params"]["reporter_agency"],
                "checks": checks,
            }


def read_store(leaf_path):
    """Return raw rows plus structural errors without deduplicating first."""
    errors = []
    rows = []
    awards_dir = leaf_path / "awards"
    manifest_path = awards_dir / "manifest.json"
    if not manifest_path.exists():
        return [], [f"{leaf_path}: missing awards/manifest.json"]
    try:
        manifest = json.loads(manifest_path.read_text())
    except (OSError, ValueError) as exc:
        return [], [f"{manifest_path}: invalid manifest: {exc}"]

    shard_years = set()
    nonempty_years = set()
    for shard in sorted(awards_dir.glob("FY*.csv.gz")):
        match = re.fullmatch(r"FY(\d{4})\.csv\.gz", shard.name)
        if not match:
            errors.append(f"{shard}: invalid fiscal-year shard name")
            continue
        shard_fy = int(match.group(1))
        shard_years.add(shard_fy)
        try:
            with gzip.open(shard, "rt", newline="") as fh:
                shard_rows = list(csv.DictReader(fh))
        except (OSError, UnicodeError, csv.Error) as exc:
            errors.append(f"{shard}: unreadable gzip CSV: {exc}")
            continue
        if shard_rows:
            nonempty_years.add(shard_fy)
        for row in shard_rows:
            award_id = row.get("id") or "<missing>"
            if not award_id.startswith("nih:"):
                errors.append(f"{shard}: invalid NIH id {award_id!r}")
            try:
                award_day = date.fromisoformat(row["date"])
            except (KeyError, TypeError, ValueError):
                errors.append(f"{shard}: invalid date for {award_id}")
                continue
            if fiscal_year(award_day) != shard_fy:
                errors.append(
                    f"{shard}: {award_id} date {award_day} belongs to "
                    f"FY{fiscal_year(award_day)}")
            try:
                int(row["estimatedTotalAmt"])
            except (KeyError, TypeError, ValueError):
                errors.append(f"{shard}: invalid amount for {award_id}")
            rows.append(row)

    if manifest.get("format") != "fiscal-year-csv-gzip-v1":
        errors.append(f"{manifest_path}: unexpected format {manifest.get('format')!r}")
    if manifest.get("recordCount") != len(rows):
        errors.append(
            f"{manifest_path}: recordCount={manifest.get('recordCount')} "
            f"but read {len(rows)} rows")
    if manifest.get("fiscalYears") != sorted(nonempty_years):
        errors.append(
            f"{manifest_path}: fiscalYears={manifest.get('fiscalYears')} "
            f"but nonempty shards are {sorted(nonempty_years)}")
    missing_files = set(manifest.get("fiscalYears") or []) - shard_years
    if missing_files:
        errors.append(f"{manifest_path}: missing shard files for {sorted(missing_files)}")
    return rows, errors


def _check_changes_ledger(leaf_path):
    """Validate one unit's move ledger (data/nih/<ic>/<ic>/changes.csv.gz):
    readable, exact columns, and sorted by (pullDate, id, field). Absence is
    fine -- the ledger cannot be produced offline; only a live pull appends
    to it."""
    path = changes_ledger_path(leaf_path / "awards")
    if not path.exists():
        return []
    errors = []
    try:
        with gzip.open(path, "rt", newline="") as fh:
            reader = csv.DictReader(fh)
            if reader.fieldnames != CHANGES_HEADER:
                return [f"{path}: unexpected columns {reader.fieldnames}, "
                        f"expected {CHANGES_HEADER}"]
            rows = list(reader)
    except (OSError, UnicodeError, csv.Error) as exc:
        return [f"{path}: unreadable gzip CSV: {exc}"]
    keys = [(row.get("pullDate"), row.get("id"), row.get("field")) for row in rows]
    if keys != sorted(keys):
        errors.append(f"{path}: rows are not sorted by (pullDate, id, field)")
    return errors


def within_relative(actual, expected, tolerance):
    return abs(actual - expected) <= abs(expected) * tolerance


def live_gap_tolerance(store_count):
    """max(3, 0.01%) per docs/verification-regime.md "NIH award-ledger
    invariants"."""
    return max(LIVE_GAP_ABS_MIN, LIVE_GAP_REL_FRACTION * store_count)


def reconcile_live_total(store_count, excluded_count, retained_missing,
                         source_total):
    """Decompose store vs independent RePORTER meta.total. Equality is not
    required -- only a bounded, explained gap (docs/verification-regime.md)."""
    expected = store_count - excluded_count - retained_missing
    gap = abs(source_total - expected)
    tolerance = live_gap_tolerance(store_count)
    return {
        "storeCount": store_count,
        "excludedCount": excluded_count,
        "retainedMissingCount": retained_missing,
        "expected": expected,
        "sourceTotal": source_total,
        "gap": gap,
        "tolerance": tolerance,
        "withinTolerance": gap <= tolerance,
    }


def in_data_book_scope(row):
    """Match NIH Data Book reports 400/401 without narrowing the product."""
    detail = parse_trans_type(row.get("transType"))
    if detail is None:
        raise ValueError(
            "missing structured NIH funding-mechanism detail; full re-pull required")
    mechanism = detail["mechanism"].strip().lower()
    activity = detail["activity"].strip().upper()
    amount = int(row["estimatedTotalAmt"])
    return (
        amount != 0
        and mechanism not in DATA_BOOK_EXCLUDED_MECHANISMS
        and not activity.startswith("L")
    )


def live_reporter_total(agency, first_fy, last_fy):
    puller = NihReporterPull(agency, {}, Path("unused"))
    payload = {
        "criteria": {
            "fiscal_years": list(range(first_fy, last_fy + 1)),
            "agencies": [agency],
            "is_agency_admin": True,
            "exclude_subprojects": True,
            "funding_mechanism": FUNDING_MECHANISMS,
        },
        "include_fields": [INCLUDE_FIELDS[0]],
        "offset": 0,
        "limit": 1,
    }
    # Build criteria through the same adapter object as a contract check, but
    # use one multi-year meta query rather than paginating each fiscal year.
    expected_one_year = puller.criteria(first_fy)
    if expected_one_year["agencies"] != [agency]:
        raise RuntimeError(f"criteria construction failed for {agency}")
    body = api_post(payload)
    return int((body.get("meta") or {}).get("total") or 0)


def live_mechanism_partition(agencies, fy):
    """Return unfiltered, supported extramural, and intramural totals.

    This tripwire detects new RePORTER funding-mechanism values before the
    adapter's explicit extramural whitelist can silently omit them.
    """
    if isinstance(agencies, str):
        agencies = [agencies]
    base = {
        "fiscal_years": [fy],
        "agencies": list(agencies),
        "is_agency_admin": True,
        "exclude_subprojects": True,
    }

    def total(extra=None):
        criteria = dict(base)
        if extra:
            criteria.update(extra)
        body = api_post({
            "criteria": criteria,
            "include_fields": [INCLUDE_FIELDS[0]],
            "offset": 0,
            "limit": 1,
        })
        return int((body.get("meta") or {}).get("total") or 0)

    return {
        "unfiltered": total(),
        "extramural": total({"funding_mechanism": FUNDING_MECHANISMS}),
        "intramural": total({"funding_mechanism": ["IM"]}),
    }


def validate(repo_root=REPO_ROOT, live=False, allow_warnings=False):
    global DATA, CONFIG, DATA_BOOK_BASELINE
    repo_root = Path(repo_root)
    DATA = repo_root / "data"
    CONFIG = repo_root / "config" / "orgs.json"
    DATA_BOOK_BASELINE = repo_root / "reference" / "nih_databook_baseline.json"

    cfg = json.loads(CONFIG.read_text())
    baseline = json.loads(DATA_BOOK_BASELINE.read_text())
    errors, notes = [], []
    # Separate from `warnings`, a per-unit local reused below for a
    # dashboard's own published data-quality warnings -- this is the
    # module-level live-gap-tolerance warning list (Phase 3.2d remediation
    # W17): a unit disclosed as stale in data/refresh_status.json (its pull
    # job did not complete this run) is expected to lag the live RePORTER
    # source, so the live-gap check below downgrades from error to warning
    # for exactly this unit instead of failing the whole rollup on a
    # known, already-disclosed gap. All non-live checks stay exactly as
    # strict as for any other unit. See docs/nih-data-validation.md,
    # "Award refresh, freshness, and publication (W17)".
    live_warnings = []
    stale_units = []
    refresh_status = load_refresh_status(repo_root)
    global_ids = {}
    aggregated_global_ids = set()
    fy_counts, fy_dollars = Counter(), Counter()
    databook_fy_counts, databook_fy_dollars = Counter(), Counter()
    first_fy = fiscal_year(SERIES_START)
    last_fy = fiscal_year(date.today())

    try:
        exclusion_ledger = load_exclusion_ledger(repo_root)
    except (RuntimeError, OSError, ValueError) as exc:
        errors.append(f"reference/nih_reporter_exclusions.json: {exc}")
        exclusion_ledger = {"schemaVersion": 1, "records": []}
    excluded = {r["id"] for r in exclusion_ledger["records"] if r["status"] == "excluded"}
    returned_in_ledger = {r["id"] for r in exclusion_ledger["records"] if r["status"] == "returned"}

    units = list(nih_units(cfg))
    for unit in units:
        unit_refresh = default_entry(refresh_status.get(unit["path"]))
        unit_stale = is_marked_stale(unit_refresh)
        leaf = DATA / unit["path"]
        rows, row_errors = read_store(leaf)
        errors.extend(row_errors)
        ids = [row.get("id") for row in rows]
        duplicates = sorted(aid for aid, n in Counter(ids).items() if n > 1)
        if duplicates:
            errors.append(
                f"{unit['path']}: {len(duplicates)} duplicate IDs within shards")
        aggregated_rows = []
        for row in rows:
            aid = row.get("id")
            if aid in global_ids and global_ids[aid] != unit["path"]:
                errors.append(
                    f"{aid} appears in both {global_ids[aid]} and {unit['path']}")
            global_ids[aid] = unit["path"]
            if aid in excluded:
                continue  # soft-deleted: retained in the store, skipped here
            aggregated_global_ids.add(aid)
            aggregated_rows.append(row)
            try:
                fy = fiscal_year(date.fromisoformat(row["date"]))
                amount = int(row["estimatedTotalAmt"])
            except (KeyError, TypeError, ValueError):
                continue  # already reported by read_store
            fy_counts[fy] += 1
            fy_dollars[fy] += amount
            try:
                benchmark_row = in_data_book_scope(row)
            except ValueError as exc:
                errors.append(f"{unit['path']}: {aid}: {exc}")
                continue
            if benchmark_row:
                databook_fy_counts[fy] += 1
                databook_fy_dollars[fy] += amount

        checks = unit["checks"]
        if not checks["min_total"] <= len(aggregated_rows) <= checks["max_total"]:
            errors.append(
                f"{unit['path']}: {len(aggregated_rows)} rows outside configured "
                f"range {checks['min_total']}..{checks['max_total']}")
        monthly = Counter(row.get("date", "")[:7] for row in aggregated_rows)
        too_large = [(month, n) for month, n in monthly.items()
                     if n > checks["max_monthly"]]
        if too_large:
            month, count = sorted(too_large)[0]
            errors.append(
                f"{unit['path']}: {month} has {count} rows, above "
                f"{checks['max_monthly']}")

        dashboard_path = leaf / "dashboard.json"
        dashboard = {}
        if not dashboard_path.exists():
            errors.append(f"{unit['path']}: missing dashboard.json")
        else:
            dashboard = json.loads(dashboard_path.read_text())
            if dashboard.get("totalAwards") != len(aggregated_rows):
                errors.append(
                    f"{unit['path']}: dashboard totalAwards="
                    f"{dashboard.get('totalAwards')} but aggregated store has "
                    f"{len(aggregated_rows)} (of {len(rows)} stored, "
                    f"{len(rows) - len(aggregated_rows)} excluded)")
            if dashboard.get("methodologyNote") != METHODOLOGY_NOTE:
                errors.append(
                    f"{unit['path']}: methodologyNote is "
                    f"{dashboard.get('methodologyNote')!r}, expected the "
                    "approved verbatim text")
            warnings = dashboard.get("warnings") or []
            if warnings and not allow_warnings:
                errors.append(
                    f"{unit['path']}: dashboard has {len(warnings)} warning(s)")

        errors.extend(_check_changes_ledger(leaf))

        if live and not row_errors:
            source_total = live_reporter_total(unit["agency"], first_fy, last_fy)
            retained_missing = retained_missing_count(dashboard.get("dataQualityNotes"))
            unit_excluded = len(rows) - len(aggregated_rows)
            result = reconcile_live_total(
                len(rows), unit_excluded, retained_missing, source_total)
            notes.append(
                f"{unit['path']}: live decomposition store={result['storeCount']} "
                f"excluded={result['excludedCount']} "
                f"retainedMissing={result['retainedMissingCount']} "
                f"expected={result['expected']} sourceTotal={result['sourceTotal']} "
                f"gap={result['gap']} tolerance={result['tolerance']:.2f}")
            if not result["withinTolerance"]:
                if unit_stale:
                    # Published staleness (Phase 3.2d remediation W17): an
                    # out-of-tolerance live gap for a disclosed-stale unit is
                    # not an error -- the store simply has not caught up to
                    # the live source since the pull job that would have
                    # refreshed it did not complete. The gap is disclosed,
                    # not silent.
                    stale_units.append(unit["path"])
                    live_warnings.append(
                        f"WARNING: {unit['path']}: stale since "
                        f"{unit_refresh.get('staleSince')} (pull did not "
                        f"complete); live gap {result['gap']} vs tolerance "
                        f"{result['tolerance']:.2f} not enforced")
                else:
                    errors.append(
                        f"{unit['path']}: live RePORTER total {source_total} vs "
                        f"expected {result['expected']} (store {len(rows)} - "
                        f"excluded {unit_excluded} - retainedMissing "
                        f"{retained_missing}) differs by {result['gap']}, above "
                        f"tolerance {result['tolerance']:.2f}")
            elif unit_stale:
                # A stale unit within tolerance still gets its normal
                # decomposition note above, plus this stale notice -- the
                # staleness is disclosed regardless of whether the gap
                # happens to be small this week.
                stale_units.append(unit["path"])
                notes.append(
                    f"{unit['path']}: stale since "
                    f"{unit_refresh.get('staleSince')} (pull did not "
                    "complete); live gap within tolerance")

    # Exclusions-ledger cross-checks: an "excluded" id must never contribute
    # to an aggregated total, and a "returned" id present in the store must
    # always be counted (soft delete never silently drops a returned id).
    for eid in excluded:
        if eid in aggregated_global_ids:
            errors.append(
                f"exclusion ledger: {eid} is marked excluded but is present "
                "in an aggregated total")
    for rid in returned_in_ledger:
        if rid in global_ids and rid not in aggregated_global_ids:
            errors.append(
                f"exclusion ledger: {rid} is marked returned and present in "
                "the store, but is excluded from aggregated totals")

    # Funding-mechanism values are global, so one union query over all current
    # administrative ICs detects drift without multiplying requests by 28.
    if live:
        agencies = [unit["agency"] for unit in units]
        for fy in range(first_fy, last_fy + 1):
            partition = live_mechanism_partition(agencies, fy)
            classified = partition["extramural"] + partition["intramural"]
            if classified != partition["unfiltered"]:
                errors.append(
                    f"NIH FY{fy}: RePORTER has {partition['unfiltered']} "
                    f"unfiltered records but the extramural whitelist + IM "
                    f"classify {classified}; a funding-mechanism value may be "
                    "unrecognized")

    nih_dashboard_path = DATA / "nih" / "dashboard.json"
    if not nih_dashboard_path.exists():
        errors.append("nih: missing agency dashboard.json")
    else:
        nih_dashboard = json.loads(nih_dashboard_path.read_text())
        if nih_dashboard.get("totalAwards") != len(aggregated_global_ids):
            errors.append(
                f"nih dashboard totalAwards={nih_dashboard.get('totalAwards')} "
                f"but leaf union has {len(aggregated_global_ids)}")
        if nih_dashboard.get("dataComplete") is not True:
            errors.append("nih dashboard dataComplete is not true")
        if nih_dashboard.get("methodologyNote") != METHODOLOGY_NOTE:
            errors.append(
                "nih dashboard methodologyNote is "
                f"{nih_dashboard.get('methodologyNote')!r}, expected the "
                "approved verbatim text")

    root_dashboard_path = DATA / "dashboard.json"
    if root_dashboard_path.exists():
        root_dashboard = json.loads(root_dashboard_path.read_text())
        if root_dashboard.get("methodologyNote") != METHODOLOGY_NOTE:
            errors.append(
                "award-root dashboard methodologyNote is "
                f"{root_dashboard.get('methodologyNote')!r}, expected the "
                "approved verbatim text")

    comparison = baseline["comparison"]
    for fy_text, expected in baseline["fiscalYears"].items():
        fy = int(fy_text)
        actual_count = databook_fy_counts[fy]
        actual_dollars = databook_fy_dollars[fy]
        if not within_relative(
                actual_count, expected["awards"],
                comparison["countRelativeTolerance"]):
            errors.append(
                f"FY{fy}: {actual_count} Data Book-scope awards differs from "
                f"NIH Data Book "
                f"{expected['awards']} by more than "
                f"{comparison['countRelativeTolerance']:.0%}")
        if not within_relative(
                actual_dollars, expected["dollars"],
                comparison["dollarRelativeTolerance"]):
            errors.append(
                f"FY{fy}: ${actual_dollars:,} in Data Book scope differs from "
                f"NIH Data Book "
                f"${expected['dollars']:,} by more than "
                f"{comparison['dollarRelativeTolerance']:.0%}")

    summary = {
        "validatedAt": date.today().isoformat(),
        "liveReporter": live,
        "units": len(units),
        "uniqueAwards": len(global_ids),
        "aggregatedAwards": len(aggregated_global_ids),
        "excludedAwards": len(excluded),
        "fiscalYears": {
            str(fy): {"awards": fy_counts[fy], "dollars": fy_dollars[fy]}
            for fy in sorted(fy_counts)
        },
        "dataBookScopeFiscalYears": {
            str(fy): {
                "awards": databook_fy_counts[fy],
                "dollars": databook_fy_dollars[fy],
            }
            for fy in sorted(databook_fy_counts)
        },
        "errors": errors,
        "notes": notes,
        "warnings": live_warnings,
        "staleUnits": sorted(set(stale_units)),
    }
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--live", action="store_true",
        help="also reconcile each store to a multi-year RePORTER meta.total")
    parser.add_argument(
        "--allow-warnings", action="store_true",
        help="do not fail solely because a dashboard contains warnings")
    parser.add_argument(
        "--report", type=Path,
        help="write the machine-readable validation summary to this path")
    args = parser.parse_args()

    summary = validate(live=args.live, allow_warnings=args.allow_warnings)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(summary, indent=1) + "\n")
    for note in summary["notes"]:
        print(f"OK: {note}")
    for warning in summary.get("warnings", []):
        print(warning)
    for error in summary["errors"]:
        print(f"ERROR: {error}", file=sys.stderr)
    if summary["errors"]:
        raise SystemExit(
            f"NIH validation failed with {len(summary['errors'])} error(s)")
    print(
        f"NIH validation passed: {summary['units']} units, "
        f"{summary['uniqueAwards']} unique awards")


if __name__ == "__main__":
    main()
