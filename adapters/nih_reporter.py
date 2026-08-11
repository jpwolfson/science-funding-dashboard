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
"""

import json
import sys
import time
import urllib.error
import urllib.request
from datetime import date

from .common import SERIES_START, fiscal_year, load_store, store_exists

API = "https://api.reporter.nih.gov/v2/projects/search"
PAGE_SIZE = 500
MAX_RESULTS = 15000
RECENT_FYS = 2
FUNDING_MECHANISMS = [
    "SB", "RP", "RC", "OR", "TR", "TI", "CO", "IAA", "RDC", "SRDC",
    "OTHER",
]
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


class NihReporterPull:
    def __init__(self, agency, checks, store_path):
        self.agency = agency
        self.checks = checks
        self.store_path = store_path
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
        fy = int(row["fiscal_year"])
        fy_start, fy_end = date(fy - 1, 10, 1), date(fy, 9, 30)
        candidates = [_iso_day(row.get("award_notice_date")),
                      _iso_day(row.get("budget_start")),
                      _iso_day(row.get("project_start_date"))]
        award_day = next((day for day in candidates
                          if day is not None and fy_start <= day <= fy_end), None)
        used_fallback = not candidates[0] or candidates[0] != award_day
        if award_day is None:
            award_day = fy_start
        activity = row.get("activity_code") or ""
        award_type = row.get("award_type") or ""
        kind = _award_kind(activity, award_type)
        detail = ", ".join(x for x in [str(award_type), activity] if x)
        organization = row.get("organization") or {}
        return {
            "id": f"nih:{row['appl_id']}",
            "date": award_day.isoformat(),
            "month": award_day.strftime("%Y-%m"),
            "amount": int(round(float(row.get("award_amount") or 0))),
            "type": {"Fellowship": "fell", "Continuing award": "cont",
                     "Standard/new award": "std"}.get(kind, "other"),
            "transType": f"{kind} ({detail})" if detail else kind,
            "title": row.get("project_title") or row.get("project_num") or "",
            "awardee": organization.get("org_name") or "",
        }, used_fallback

    def pull(self, full, today):
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
        for fy in years:
            rows = self.fetch_year(fy)
            for row in rows.values():
                award, used_fallback = self.normalize(row)
                collected[award["id"]] = award
                fallback_dates += int(used_fallback)
            print(f"  FY{fy}: {len(rows)} applications", flush=True)

        if fallback_dates:
            print(f"NOTICE: {fallback_dates} RePORTER records used a "
                  "budget/project start date or fiscal-year start because "
                  "the award notice date was absent or outside its fiscal year")

        merged = dict(stored)
        merged.update(collected)
        if mode == "full":
            missing = sum(1 for award_id in stored if award_id not in collected)
            if missing:
                self.warn(
                    f"{missing} stored awards not returned by this full re-pull; "
                    "retained from the store"
                )

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
        return awards, self.warnings


def pull_unit(unit_cfg, store_path, full, today, repo_root):
    del repo_root  # adapter signature shared with NSF
    agency = unit_cfg["params"]["reporter_agency"]
    puller = NihReporterPull(agency, unit_cfg["checks"], store_path)
    awards, warnings = puller.pull(full=full, today=today)
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
    }
    return awards, warnings, source, metadata
