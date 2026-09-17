"""NIH RePORTER v2 adapter.

One leaf represents one administering NIH institute or center (IC).  The
API is queried one fiscal year at a time so no result set approaches the
documented 15,000-record pagination ceiling.  Every year is paged twice in
opposite application-ID orders; both complete ID sets must match the API's
``meta.total`` before anything is published.

RePORTER also contains intramural project records whose award amounts and
award notice dates are generally absent.  This funding dashboard therefore
pulls every documented mechanism except ``IM`` (intramural), while retaining
grants, cooperative agreements, contracts, and interagency agreements.

Source-current semantics (Phase 3.2d remediation, W1). RePORTER re-dates,
retracts, and un-retracts records between weekly pulls -- this is normal
source behavior, not a pipeline defect. A stored award id is never deleted
from the physical store (``adapters.common.write_store``); every pull only
ever adds to or overwrites fields on the store, never removes a row. Two
ledgers, both committed alongside the data they describe, make this legible:

- ``reference/nih_reporter_exclusions.json`` -- a reviewed, human-curated
  list of ids that a full pull's aggregation should currently *skip*
  (``status: "excluded"``) because RePORTER stopped returning them for a
  documented reason. This is a soft delete: the row stays in the store, but
  ``totalAwards`` and every aggregate skip it. If the live source ever
  re-emits an excluded id, the pull flips its ledger status to ``"returned"``
  and re-includes it -- this is expected source behavior, not a failure.
- ``data/nih/<ic>/<ic>/changes.csv.gz`` -- an append-only, per-unit log of
  every tracked field (date, amount, title, type) a pull overwrote on an
  already-stored id, for auditability of the source-current overwrite.

See ``docs/nih-data-validation.md`` and ``docs/verification-regime.md`` for
the full contract and the churn/live-reconciliation constants.
"""

import csv
import gzip
import io
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

from .common import SERIES_START, fiscal_year, load_store, store_exists

API = "https://api.reporter.nih.gov/v2/projects/search"
PAGE_SIZE = 500
MAX_RESULTS = 15000
RECENT_FYS = 2
FUNDING_MECHANISMS = [
    "SB", "RP", "RC", "OR", "TR", "TI", "CO", "IAA", "RDC", "SRDC",
    "OTHER",
]

# ---------------------------------------------------------------------------
# Exclusions ledger (soft-delete): reference/nih_reporter_exclusions.json
# ---------------------------------------------------------------------------

EXCLUSION_LEDGER_SCHEMA_VERSION = 1
EXCLUSION_STATUSES = {"excluded", "returned"}
SOURCE_EXCLUSION_CLASSIFICATIONS = {
    "reporter-record-retraction-or-supersession",
    "confirmed-bilateral-termination",
}
METHODOLOGY_NOTE = "counts as of the pull date; NIH revises award notice dates."

# Invariant constants (docs/verification-regime.md "NIH award-ledger
# invariants" carries the authoritative copy of these numbers).
MOVE_RETURN_ABS_MIN = 20
MOVE_RETURN_REL_FRACTION = 0.001  # 0.1%
LIVE_GAP_ABS_MIN = 3
LIVE_GAP_REL_FRACTION = 0.0001  # 0.01%

TRACKED_FIELDS = ("date", "amount", "title", "type")
CHANGES_HEADER = ["pullDate", "id", "field", "old", "new"]

_RETAINED_MISSING_NOTE_RE = re.compile(
    r"^(?P<n>\d+) stored award record\(s\) were not returned by the "
    r"(?P<date>\d{4}-\d{2}-\d{2}) full pull and are retained; NIH revises "
    r"and withdraws notices\.$"
)
_FY_ANOMALY_NOTE_RE = re.compile(
    r"^(?P<n>\d+) award record\(s\) carry a NIH-reported award notice date "
    r"outside their own declared fiscal year; retained and dated by the "
    r"source's current notice date\.$"
)


def exclusion_ledger_path(repo_root):
    return Path(repo_root) / "reference" / "nih_reporter_exclusions.json"


def _validate_exclusion_ledger(ledger, path):
    if ledger.get("schemaVersion") != EXCLUSION_LEDGER_SCHEMA_VERSION:
        raise RuntimeError(f"unexpected schemaVersion in {path}: {ledger.get('schemaVersion')!r}")
    records = ledger.get("records")
    if not isinstance(records, list):
        raise RuntimeError(f"{path}: 'records' must be a list")
    ids = [record.get("id") for record in records]
    if len(set(ids)) != len(ids):
        raise RuntimeError(f"duplicate NIH exclusion ledger ID in {path}")
    for record in records:
        if not isinstance(record.get("id"), str) or not record["id"].startswith("nih:"):
            raise RuntimeError(f"invalid NIH exclusion ledger id in {path}: {record.get('id')!r}")
        if not record.get("unit"):
            raise RuntimeError(f"{path}: {record.get('id')} missing 'unit'")
        if record.get("classification") not in SOURCE_EXCLUSION_CLASSIFICATIONS:
            raise RuntimeError(
                f"{path}: {record.get('id')} has invalid classification "
                f"{record.get('classification')!r}"
            )
        if not record.get("reason"):
            raise RuntimeError(f"{path}: {record.get('id')} missing 'reason'")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(record.get("decidedOn") or "")):
            raise RuntimeError(f"{path}: {record.get('id')} has invalid 'decidedOn'")
        if record.get("status") not in EXCLUSION_STATUSES:
            raise RuntimeError(
                f"{path}: {record.get('id')} has invalid status {record.get('status')!r}"
            )


def load_exclusion_ledger(repo_root):
    """Load, validate, and return the exclusions ledger dict.

    A missing file is treated as an empty ledger -- this file cannot be
    produced offline (it is only ever mutated by a live pull), so every
    offline consumer (validator, rollup, reaggregate) must tolerate its
    absence.
    """
    path = exclusion_ledger_path(repo_root)
    if not path.exists():
        return {"schemaVersion": EXCLUSION_LEDGER_SCHEMA_VERSION, "records": []}
    ledger = json.loads(path.read_text())
    _validate_exclusion_ledger(ledger, path)
    return ledger


def save_exclusion_ledger(repo_root, ledger):
    path = exclusion_ledger_path(repo_root)
    records = sorted(ledger.get("records") or [], key=lambda r: r["id"])
    out = {"schemaVersion": ledger.get("schemaVersion", EXCLUSION_LEDGER_SCHEMA_VERSION),
           "records": records}
    _validate_exclusion_ledger(out, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=1) + "\n")


def excluded_ids(repo_root):
    """Ids whose ledger status is currently 'excluded' -- skip from every
    aggregation (adapter pull, rollup.py, reaggregate.py). The physical
    store retains these rows if present; this is a soft delete."""
    return {record["id"] for record in load_exclusion_ledger(repo_root)["records"]
            if record["status"] == "excluded"}


def retained_missing_count(notes):
    """Sum the counts embedded in any missing-uncovered dataQualityNotes."""
    total = 0
    for note in notes or []:
        match = _RETAINED_MISSING_NOTE_RE.fullmatch(note)
        if match:
            total += int(match.group("n"))
    return total


# ---------------------------------------------------------------------------
# Move ledger (append-only, per unit): data/nih/<ic>/<ic>/changes.csv.gz
# ---------------------------------------------------------------------------


def changes_ledger_path(store_path):
    return Path(store_path).parent / "changes.csv.gz"


def load_changes_ledger(store_path):
    """Return the committed change rows, or [] if the ledger does not exist
    yet (it cannot be produced offline -- only a live pull appends to it)."""
    path = changes_ledger_path(store_path)
    if not path.exists():
        return []
    with gzip.open(path, "rt", newline="") as fh:
        reader = csv.DictReader(fh)
        return list(reader)


def append_changes_ledger(store_path, new_rows):
    """Append field-change rows, never rewriting or removing an existing
    row. Rewrites the whole gzip file (mtime=0) with the full row set,
    sorted deterministically by (pullDate, id, field), so the output bytes
    are reproducible and the file stays small and append-only in content.

    An empty ``new_rows`` is a no-op if the ledger already exists (nothing
    to add, nothing to rewrite). If the ledger does not exist yet, an empty
    list still creates the header-only file -- this is the marker a caller
    uses (``changes_ledger_path(store_path).exists()``) to tell an
    already-initialized unit from one whose first source-current pull is
    still in progress."""
    path = changes_ledger_path(store_path)
    if not new_rows and path.exists():
        return
    combined = load_changes_ledger(store_path) + [
        {"pullDate": row["pullDate"], "id": row["id"], "field": row["field"],
         "old": row["old"], "new": row["new"]}
        for row in new_rows
    ]
    combined.sort(key=lambda row: (row["pullDate"], row["id"], row["field"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
            with io.TextIOWrapper(zipped, encoding="utf-8", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=CHANGES_HEADER)
                writer.writeheader()
                for row in combined:
                    writer.writerow(row)


MOVE_SAMPLE_LIMIT = 10


def _move_field_breakdown(moves):
    """Per-tracked-field move counts, e.g. {'date': 5, 'amount': 2}."""
    counts = {}
    for move in moves:
        counts[move["field"]] = counts.get(move["field"], 0) + 1
    return counts


def _move_breakdown_str(counts):
    if not counts:
        return "none"
    return ", ".join(f"{field}: {n}" for field, n in sorted(counts.items()))


def _move_sample_lines(moves, limit=MOVE_SAMPLE_LIMIT):
    """Up to `limit` sample moves as 'id field: old -> new', for diagnosing
    a threshold trip (or an initializing pull) from the CI log."""
    return [f"  {move['id']} {move['field']}: {move['old']} -> {move['new']}"
            for move in moves[:limit]]


INCLUDE_FIELDS = [
    "ApplId", "FiscalYear", "ProjectNum", "AwardNoticeDate", "BudgetStart",
    "ProjectStartDate", "AwardAmount", "AwardType", "ActivityCode",
    "ProjectTitle", "Organization", "AgencyIcAdmin", "FundingMechanism",
    "SubprojectId",
]
MIN_REQUEST_INTERVAL = 1.05  # NIH recommends no more than one request/second.
_last_request_at = 0.0


def api_post(payload, retries=5):
    global _last_request_at
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        API,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "science-funding-dashboard/2.0",
        },
        method="POST",
    )
    for attempt in range(retries):
        try:
            wait = MIN_REQUEST_INTERVAL - (time.monotonic() - _last_request_at)
            if wait > 0:
                time.sleep(wait)
            _last_request_at = time.monotonic()
            with urllib.request.urlopen(request, timeout=90) as response:
                return json.load(response)
        except (OSError, ValueError, urllib.error.HTTPError) as exc:
            if attempt == retries - 1:
                raise RuntimeError(
                    f"NIH RePORTER request failed after {retries} tries: {API}"
                ) from exc
            time.sleep(2 ** attempt)


def _iso_day(value):
    if not value:
        return None
    return date.fromisoformat(str(value)[:10])


def _award_kind(activity_code, award_type):
    """Map NIH activity/application codes onto the dashboard's four bins."""
    activity = (activity_code or "").upper()
    award_type = str(award_type or "").upper()
    if activity.startswith("F"):
        return "Fellowship"
    if award_type in {"5", "6", "7", "8", "9", "4N"}:
        return "Continuing award"
    if award_type in {"1", "2", "3", "4", "4C"}:
        return "Standard/new award"
    return "Other award"


_TRANS_TYPE_RE = re.compile(
    r"^(?P<kind>.+?) \(award type=(?P<award_type>[^;]*); "
    r"activity=(?P<activity>[^;]*); funding mechanism=(?P<mechanism>.*)\)$"
)


def encode_trans_type(kind, award_type, activity, mechanism):
    """Persist NIH benchmark dimensions in the existing detail field."""
    return (
        f"{kind} (award type={award_type}; activity={activity}; "
        f"funding mechanism={mechanism})"
    )


def parse_trans_type(value):
    """Return persisted NIH dimensions, or ``None`` for a legacy row."""
    match = _TRANS_TYPE_RE.fullmatch(str(value or ""))
    return match.groupdict() if match else None


class NihReporterPull:
    def __init__(self, agency, checks, store_path):
        self.agency = agency
        self.checks = checks
        self.store_path = Path(store_path)
        self.warnings = []

    def warn(self, message):
        self.warnings.append(message)
        print(f"WARNING: {message}", file=sys.stderr)

    def criteria(self, fiscal_year_value):
        return {
            "fiscal_years": [fiscal_year_value],
            "agencies": [self.agency],
            "is_agency_admin": True,
            "exclude_subprojects": True,
            "funding_mechanism": FUNDING_MECHANISMS,
        }

    def fetch_pass(self, fiscal_year_value, sort_order):
        """Fetch and exactly validate one ordered pagination pass."""
        offset = 0
        total = None
        by_id = {}
        while total is None or offset < total:
            payload = {
                "criteria": self.criteria(fiscal_year_value),
                "include_fields": INCLUDE_FIELDS,
                "offset": offset,
                "limit": PAGE_SIZE,
                "sort_field": "appl_id",
                "sort_order": sort_order,
            }
            body = api_post(payload)
            meta = body.get("meta") or {}
            page = body.get("results") or []
            reported = int(meta.get("total") or 0)
            if total is None:
                total = reported
                if total > MAX_RESULTS:
                    raise RuntimeError(
                        f"FY{fiscal_year_value} {self.agency} reports {total} records, "
                        f"above RePORTER's {MAX_RESULTS}-record pagination ceiling"
                    )
            elif reported != total:
                raise RuntimeError(
                    f"FY{fiscal_year_value} {self.agency} total changed during "
                    f"pagination ({total} -> {reported})"
                )
            if not page and offset < total:
                raise RuntimeError(
                    f"FY{fiscal_year_value} {self.agency} returned an empty page "
                    f"at offset {offset} of {total}"
                )
            for row in page:
                appl_id = row.get("appl_id")
                if appl_id is None:
                    raise RuntimeError("RePORTER row is missing appl_id")
                try:
                    row_fy = int(row.get("fiscal_year"))
                except (TypeError, ValueError) as exc:
                    raise RuntimeError(
                        f"application {appl_id} has invalid fiscal_year "
                        f"{row.get('fiscal_year')!r}"
                    ) from exc
                if row_fy != fiscal_year_value:
                    raise RuntimeError(
                        f"fiscal-year filter mismatch: requested FY"
                        f"{fiscal_year_value}, got FY{row_fy} for application "
                        f"{appl_id}"
                    )
                admin = row.get("agency_ic_admin") or {}
                if admin.get("abbreviation") != self.agency:
                    raise RuntimeError(
                        f"agency filter mismatch: requested {self.agency}, got "
                        f"{admin.get('abbreviation')!r} for application {appl_id}"
                    )
                if row.get("subproject_id") is not None:
                    raise RuntimeError(
                        f"subproject filter mismatch: application {appl_id} "
                        f"has subproject_id={row.get('subproject_id')!r}"
                    )
                mechanism = str(row.get("funding_mechanism") or "").strip()
                if not mechanism:
                    raise RuntimeError(
                        f"application {appl_id} is missing funding_mechanism"
                    )
                if "intramural" in mechanism.lower():
                    raise RuntimeError(
                        f"funding-mechanism filter mismatch: application "
                        f"{appl_id} is {mechanism!r}"
                    )
                by_id[int(appl_id)] = row
            offset += len(page)
        if len(by_id) != total:
            raise RuntimeError(
                f"FY{fiscal_year_value} {self.agency} pagination returned "
                f"{len(by_id)} unique applications vs meta.total={total}"
            )
        return by_id, total

    def fetch_year(self, fiscal_year_value, attempts=3):
        """Require matching ascending and descending complete snapshots."""
        last_error = None
        for attempt in range(attempts):
            try:
                ascending, total_a = self.fetch_pass(fiscal_year_value, "asc")
                descending, total_d = self.fetch_pass(fiscal_year_value, "desc")
                if total_a != total_d or set(ascending) != set(descending):
                    raise RuntimeError(
                        f"FY{fiscal_year_value} {self.agency} ordered passes disagree "
                        f"(asc {len(ascending)}/{total_a}, desc "
                        f"{len(descending)}/{total_d})"
                    )
                ascending.update(descending)
                return ascending
            except RuntimeError as exc:
                last_error = exc
                if attempt + 1 < attempts:
                    print(f"retrying FY{fiscal_year_value} snapshot: {exc}",
                          file=sys.stderr)
                    time.sleep(2 ** attempt)
        raise last_error

    def normalize(self, row):
        """Return (award dict, used_fallback, fy_anomaly).

        Source-current: when RePORTER reports an award notice date, that
        date is used as-is, even when it falls outside the record's own
        declared ``fiscal_year`` -- this is a source anomaly to retain and
        report (invariant D3), not to silently paper over by substituting a
        different candidate date. ``used_fallback`` is only set when the
        award notice date is absent entirely and a budget/project start
        date (or the fiscal-year start) had to stand in for it.
        """
        fy = int(row["fiscal_year"])
        fy_start, fy_end = date(fy - 1, 10, 1), date(fy, 9, 30)
        notice_day = _iso_day(row.get("award_notice_date"))
        fy_anomaly = False
        if notice_day is not None:
            award_day = notice_day
            used_fallback = False
            if not (fy_start <= award_day <= fy_end):
                fy_anomaly = True
        else:
            candidates = [_iso_day(row.get("budget_start")),
                          _iso_day(row.get("project_start_date"))]
            award_day = next((day for day in candidates
                              if day is not None and fy_start <= day <= fy_end), None)
            used_fallback = True
            if award_day is None:
                award_day = fy_start
        activity = row.get("activity_code") or ""
        award_type = row.get("award_type") or ""
        mechanism = str(row.get("funding_mechanism") or "").strip()
        if not mechanism:
            raise RuntimeError(
                f"application {row.get('appl_id')} is missing funding_mechanism")
        kind = _award_kind(activity, award_type)
        organization = row.get("organization") or {}
        award = {
            "id": f"nih:{row['appl_id']}",
            "date": award_day.isoformat(),
            "month": award_day.strftime("%Y-%m"),
            "amount": int(round(float(row.get("award_amount") or 0))),
            "type": {"Fellowship": "fell", "Continuing award": "cont",
                     "Standard/new award": "std"}.get(kind, "other"),
            "transType": encode_trans_type(
                kind, str(award_type), activity, mechanism),
            "title": row.get("project_title") or row.get("project_num") or "",
            "awardee": organization.get("org_name") or "",
        }
        return award, used_fallback, fy_anomaly

    def pull(self, full, today, repo_root=None):
        stored = load_store(self.store_path)
        has_prior_store = store_exists(self.store_path)
        current_fy = fiscal_year(today)
        first_fy = fiscal_year(SERIES_START)
        if full or not has_prior_store:
            years = list(range(first_fy, current_fy + 1))
            mode = "full"
        else:
            years = list(range(max(first_fy, current_fy - RECENT_FYS + 1),
                               current_fy + 1))
            mode = "incremental"
        print(f"{mode} NIH RePORTER pull [{self.agency}]: FY{years[0]}.."
              f"FY{years[-1]} ({len(stored)} awards in store)")

        collected = {}
        fallback_dates = 0
        fy_anomaly_ids = []
        for fy in years:
            rows = self.fetch_year(fy)
            for row in rows.values():
                award, used_fallback, fy_anomaly = self.normalize(row)
                collected[award["id"]] = award
                fallback_dates += int(used_fallback)
                if fy_anomaly:
                    fy_anomaly_ids.append(award["id"])
            print(f"  FY{fy}: {len(rows)} applications", flush=True)

        if fallback_dates:
            print(f"NOTICE: {fallback_dates} RePORTER records used a "
                  "budget/project start date or fiscal-year start because "
                  "the award notice date was absent")

        # Load the reviewed exclusions ledger (soft-delete). A live pull that
        # re-emits an id currently marked "excluded" flips it to "returned"
        # and re-includes it -- expected source behavior, never a failure.
        ledger = load_exclusion_ledger(repo_root) if repo_root is not None \
            else {"schemaVersion": EXCLUSION_LEDGER_SCHEMA_VERSION, "records": []}
        records_by_id = {record["id"]: record for record in ledger["records"]}
        currently_excluded = {aid for aid, record in records_by_id.items()
                              if record["status"] == "excluded"}

        returned_ids = sorted(set(collected) & currently_excluded)
        for award_id in returned_ids:
            records_by_id[award_id]["status"] = "returned"
        if returned_ids:
            if repo_root is not None:
                save_exclusion_ledger(repo_root, {
                    "schemaVersion": ledger.get("schemaVersion",
                                                EXCLUSION_LEDGER_SCHEMA_VERSION),
                    "records": list(records_by_id.values()),
                })
            print(f"NOTICE: {len(returned_ids)} previously excluded RePORTER "
                  f"record(s) returned to the live source for {self.agency} "
                  "and re-included: " + ", ".join(returned_ids))

        # Carry forward the missing-uncovered note across incremental pulls
        # (only a full pull can determine full-coverage; an incremental
        # pull's window is too narrow to speak to older fiscal years).
        data_quality_notes = []
        if mode != "full":
            prior_dashboard_path = self.store_path.parent / "dashboard.json"
            if prior_dashboard_path.exists():
                try:
                    prior = json.loads(prior_dashboard_path.read_text())
                except (OSError, ValueError):
                    prior = {}
                data_quality_notes = [
                    note for note in (prior.get("dataQualityNotes") or [])
                    if _RETAINED_MISSING_NOTE_RE.fullmatch(note)
                ]

        if mode == "full":
            missing_ids = set(stored) - set(collected)
            unexplained_missing = sorted(missing_ids - currently_excluded)
            if unexplained_missing:
                data_quality_notes.append(
                    f"{len(unexplained_missing)} stored award record(s) were "
                    f"not returned by the {today.isoformat()} full pull and "
                    "are retained; NIH revises and withdraws notices."
                )

        # Source-current field overwrite: every id present in both the store
        # and this pull's fetch is diffed on the tracked fields and any
        # change is appended to the per-unit move ledger.
        moves = []
        for award_id, new_award in collected.items():
            old_award = stored.get(award_id)
            if old_award is None:
                continue
            for field in TRACKED_FIELDS:
                if old_award.get(field) != new_award.get(field):
                    moves.append({
                        "pullDate": today.isoformat(),
                        "id": award_id,
                        "field": field,
                        "old": str(old_award.get(field)),
                        "new": str(new_award.get(field)),
                    })

        # The committed ledger file is the marker of whether this unit has
        # ever completed a source-current pull. It must be read BEFORE this
        # pull appends to it, and before the threshold decision below, so
        # the exemption below can only ever see a unit's true first pull.
        ledger_initialized = changes_ledger_path(self.store_path).exists()

        move_return_count = len(moves) + len(returned_ids)
        limit = max(MOVE_RETURN_ABS_MIN, MOVE_RETURN_REL_FRACTION * len(stored))
        field_counts = _move_field_breakdown(moves)
        field_breakdown = _move_breakdown_str(field_counts)
        sample_lines = _move_sample_lines(moves)

        if ledger_initialized:
            if move_return_count > limit:
                diagnostics = f"  field breakdown: {field_breakdown}"
                if sample_lines:
                    diagnostics += "\n  sample moves (up to " \
                        f"{MOVE_SAMPLE_LIMIT}):\n" + "\n".join(sample_lines)
                raise SystemExit(
                    f"FATAL: {self.agency} pull has {len(moves)} field "
                    f"move(s) + {len(returned_ids)} return(s) = "
                    f"{move_return_count}, above the max(20, 0.1% of "
                    f"store) = {limit:.1f} threshold for a {len(stored)}-"
                    "award store; this is the pagination/duplicate-"
                    "displacement bug signature (CLAUDE.md data integrity "
                    "rule 4) -- refusing to publish\n" + diagnostics
                )
        else:
            # First source-current pull for this unit: the old adapter
            # never overwrote fields, so this pull is measuring the drift
            # accumulated since the store was built, not one pull's worth
            # of churn. The threshold would misfire on that backlog every
            # time, so it is not enforced here -- every move is appended,
            # initializing the ledger. This is deliberately NOT a general
            # bypass: the ledger file this pull creates is itself the
            # marker `ledger_initialized` checks, so no unit can hit this
            # branch more than once, ever. From the next pull for this
            # unit onward the threshold applies exactly as it does today.
            print(
                f"NOTICE: first source-current pull for {self.agency}: "
                f"initialized the change ledger with {len(moves)} field "
                f"move(s) ({field_breakdown}); the churn threshold applies "
                "from the next pull"
            )
            if sample_lines:
                print(f"  sample moves (up to {MOVE_SAMPLE_LIMIT}):\n"
                      + "\n".join(sample_lines))

        append_changes_ledger(self.store_path, moves)

        if fy_anomaly_ids:
            print(f"NOTICE: {len(fy_anomaly_ids)} RePORTER record(s) carry an "
                  "award notice date outside their own declared fiscal year; "
                  "retained and dated by the source's current notice date")
            data_quality_notes.append(
                f"{len(fy_anomaly_ids)} award record(s) carry a NIH-reported "
                "award notice date outside their own declared fiscal year; "
                "retained and dated by the source's current notice date."
            )

        # Never pop: the store retains every id ever seen. Aggregation-level
        # exclusion (the "excluded" ledger status) is applied downstream by
        # the caller (scripts/pull_unit.py), not here, so the physical store
        # this method's caller writes always contains the full history.
        merged = dict(stored)
        merged.update(collected)

        awards = list(merged.values())
        total = len(awards)
        if not self.checks["min_total"] <= total <= self.checks["max_total"]:
            raise SystemExit(
                f"FATAL: implausible total {total} for {self.agency} "
                f"(allowed {self.checks['min_total']}.."
                f"{self.checks['max_total']}); refusing to publish"
            )
        monthly = {}
        for award in awards:
            monthly[award["month"]] = monthly.get(award["month"], 0) + 1
        too_large = [(month, count) for month, count in sorted(monthly.items())
                     if count > self.checks["max_monthly"]]
        if too_large:
            month, count = too_large[0]
            raise SystemExit(
                f"FATAL: {month} has {count} {self.agency} awards, above the "
                f"{self.checks['max_monthly']}/month plausibility cap"
            )
        print(f"Total unique awards [{self.agency}]: {total}")
        return awards, self.warnings, data_quality_notes


def pull_unit(unit_cfg, store_path, full, today, repo_root):
    agency = unit_cfg["params"]["reporter_agency"]
    puller = NihReporterPull(agency, unit_cfg["checks"], store_path)
    awards, warnings, data_quality_notes = puller.pull(
        full=full, today=today, repo_root=repo_root)
    source = (
        f"{API} (NIH RePORTER v2), administering IC {agency}; "
        "one application record per fiscal year; intramural projects excluded; "
        "dated by award notice, then budget/project start when unavailable"
    )
    metadata = {
        "provider": "nih",
        "dataComplete": True,
        "storeFormat": "fiscal-year-gzip",
        "amountNote": "Dollar figures are RePORTER award amounts, not outlays.",
        "mechanismLabels": {
            "std": "New/competing awards",
            "cont": "Noncompeting continuations",
            "fell": "Fellowships",
            "other": "Other awards",
        },
        "methodologyNote": METHODOLOGY_NOTE,
        "dataQualityNotes": data_quality_notes,
    }
    return awards, warnings, source, metadata
