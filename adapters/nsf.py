"""NSF Award Search API adapter, generalized from the verified DMS pipeline
(reference/pull_nsf_dms.py, exact against a hand-tallied baseline).

Empirically confirmed API defects this adapter works around — do not
"simplify" any of these away:

- `offset` is 0-based despite documentation suggesting 1-based. Paginating
  from offset=1 silently skips each query's first record, so after normal
  pagination the offset=0 page is unioned back in.
- Cross-page duplicate displacement: queries spanning many pages return
  duplicates, each silently displacing a record that is never returned.
  Result sets are kept <= SAFE_WINDOW by recursive date bisection; heavy
  single days partition by transType, then awardeeStateCode.
- Date-filter off-by-one: unpadded windows each came back exactly one award
  short. Windows are padded +/-1 day and records attributed by their own
  `date` field. The filter may not even operate on the returned `date`
  field, so the pull queries a wider horizon than the series.
- Undocumented params are silently ignored: partition only by documented
  params, and union results at every level so an ineffective partition can
  waste requests but never lose records.
"""

import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, timedelta

from .common import SERIES_START, load_store, norm_type

API = "https://api.nsf.gov/services/v1/awards.json"
RPP = 25          # API maximum results per page
SAFE_WINDOW = 60  # bisect windows larger than this (~2.5 pages) to dodge the pagination fault
RECENT_MONTHS = 4  # incremental runs re-pull this trailing window (NSF backfill period)
PRINT_FIELDS = "id,date,estimatedTotalAmt,transType,title,awardeeName"
# The API's date filter may not operate on exactly the "date" field it
# returns, so query a wider horizon than the series and attribute records
# by their own date.
QUERY_BACK = date(2013, 10, 1)
QUERY_AHEAD = timedelta(days=550)

TRANS_TYPES = [
    "Standard Grant", "Continuing Grant", "Continuing grant", "Fellowship",
    "Cooperative Agreement", "Interagency Agreement", "Contract",
    "Fixed Price Award", "BOA/Task Order", "GAA",
]
STATE_CODES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA", "HI",
    "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN",
    "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH",
    "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA",
    "WV", "WI", "WY", "PR", "VI", "GU", "AS", "MP",
]


def api_get(params, retries=5):
    url = API + "?" + urllib.parse.urlencode(params)
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=60) as resp:
                body = json.load(resp)
            return body.get("response", {}).get("award", []) or []
        except Exception as e:
            if attempt == retries - 1:
                raise RuntimeError(f"API request failed after {retries} tries: {url}") from e
            time.sleep(2 ** attempt)


class NsfPull:
    """One pull of one org unit (a division-tier org_code_div)."""

    def __init__(self, org_code_div, checks, store_path):
        self.code = org_code_div
        self.checks = checks  # {min_total, max_total, max_monthly, baseline?}
        self.store_path = store_path
        self.warnings = []
        self.use_zero_offset = False

    def warn(self, msg):
        self.warnings.append(msg)
        print(f"WARNING: {msg}", file=sys.stderr)

    # ---- fetch machinery (verbatim behavior from the verified pipeline) ----

    def fetch_pages(self, extra_params):
        """Paginate one query to exhaustion. Returns (awards_by_id, saw_duplicates)."""
        by_id, dups = {}, False
        offset = 1
        while True:
            page = api_get({
                "org_code_div": self.code,
                "printFields": PRINT_FIELDS,
                "rpp": RPP,
                "offset": offset,
                **extra_params,
            })
            for a in page:
                if a["id"] in by_id:
                    dups = True
                by_id[a["id"]] = a
            if len(page) < RPP:
                break
            offset += RPP
        if self.use_zero_offset:
            # The API's offset is 0-based, so offset=1 pagination skips each
            # query's first record. Union in the offset=0 page.
            for a in api_get({
                "org_code_div": self.code,
                "printFields": PRINT_FIELDS,
                "rpp": RPP,
                "offset": 0,
                **extra_params,
            }):
                by_id.setdefault(a["id"], a)
        return by_id, dups

    @staticmethod
    def date_params(start, end):
        # Pad one day each side: the API's date-range boundaries are
        # off-by-one. Awards are keyed by id and attributed to months by
        # their own date field, so overlap between windows is harmless.
        return {"dateStart": (start - timedelta(days=1)).strftime("%m/%d/%Y"),
                "dateEnd": (end + timedelta(days=1)).strftime("%m/%d/%Y")}

    # The pagination fault displaces records at random, so no single query
    # is trusted to be complete. Every level below UNIONS its own results
    # with its sub-queries' results - a record survives if ANY query returns
    # it, and an ineffective partition can never lose data.

    def fetch_day_partitions(self, day):
        out = {}
        dp = self.date_params(day, day)
        for t in TRANS_TYPES:
            sub, dups = self.fetch_pages({**dp, "transType": t})
            out.update(sub)
            if len(sub) > SAFE_WINDOW or dups:
                for s in STATE_CODES:
                    sub2, _ = self.fetch_pages({**dp, "transType": t, "awardeeStateCode": s})
                    out.update(sub2)
        return out

    def fetch_window(self, start, end):
        by_id, dups = self.fetch_pages(self.date_params(start, end))
        if len(by_id) <= SAFE_WINDOW and not dups:
            return by_id
        if start == end:
            return {**by_id, **self.fetch_day_partitions(start)}
        mid = start + (end - start) // 2
        return {**by_id,
                **self.fetch_window(start, mid),
                **self.fetch_window(mid + timedelta(days=1), end)}

    # ---- pre-pull probes ----

    def probe_org_filter(self, today):
        """Abort rather than publish if org_code_div is being ignored — an
        ignored division filter would silently pull all of NSF into one
        unit. Strategy: a syntactically valid but nonexistent code must
        return nothing; if the API instead ignores unknown codes, fall back
        to comparing filtered vs unfiltered counts over a busy window."""
        wide = {"printFields": "id", "rpp": RPP,
                "dateStart": "01/01/2015", "dateEnd": "12/31/2015"}
        try:
            bogus = api_get({"org_code_div": "99999999", "offset": 0, **wide},
                            retries=2)
        except RuntimeError:
            bogus = []
        if not bogus:
            bogus = api_get({"org_code_div": "99999999", "offset": 1, **wide})
        if not bogus:
            print("org-filter probe: unknown codes return empty; filter is validating")
            return
        # Unknown codes return data — cannot distinguish "unknown code
        # ignored" from "filter ignored". Compare against unfiltered volume
        # on one busy week; a real division is a small fraction of all-NSF.
        week = {"printFields": "id", "rpp": RPP,
                "dateStart": "09/10/2015", "dateEnd": "09/17/2015"}
        ours, _ = self.count_capped({"org_code_div": self.code, **week}, cap=200)
        theirs, _ = self.count_capped(dict(week), cap=200)
        print(f"org-filter probe: unknown codes NOT rejected; "
              f"filtered={ours} vs unfiltered={theirs} on probe week")
        if ours >= theirs and theirs >= 200:
            sys.exit(f"FATAL: org_code_div={self.code} appears to be ignored "
                     f"(filtered count matches unfiltered agency-wide volume). "
                     "Refusing to pull.")
        self.warn("org filter accepts unknown codes; typo'd org codes cannot "
                  "be detected by probe (plausibility caps still apply)")

    @staticmethod
    def count_capped(params, cap):
        """Count distinct ids for a query, paging up to cap. Existence-grade
        only (the pagination fault makes big counts approximate)."""
        seen = set()
        offset = 0
        while len(seen) < cap:
            page = api_get({**params, "offset": offset})
            seen.update(a["id"] for a in page)
            if len(page) < RPP:
                break
            offset += RPP
        return len(seen), len(seen) >= cap

    def probe_zero_offset(self, today):
        try:
            probe = api_get({"org_code_div": self.code, "printFields": "id",
                             "rpp": RPP, "offset": 0,
                             "dateStart": QUERY_BACK.strftime("%m/%d/%Y"),
                             "dateEnd": today.strftime("%m/%d/%Y")},
                            retries=2)
            self.use_zero_offset = len(probe) > 0
        except RuntimeError:
            self.use_zero_offset = False
        print(f"offset=0 supported: {self.use_zero_offset}")

    # ---- main entry ----

    def pull(self, full, today, repo_root):
        """Returns (awards list, warnings list). SystemExits on any
        plausibility failure — publish nothing rather than publish garbage."""
        from .common import month_windows, month_floor, months_back

        self.probe_org_filter(today)
        self.probe_zero_offset(today)

        stored = load_store(self.store_path)
        # Recent months are re-pulled every run: NSF backfills awards for
        # weeks after their award date.
        window_start = months_back(today, RECENT_MONTHS - 1)
        if stored:
            last_stored = max(date.fromisoformat(a["date"]) for a in stored.values())
            window_start = min(window_start, month_floor(last_stored))
        if full or not stored:
            pull_start, mode = QUERY_BACK, "full"
        else:
            pull_start, mode = window_start, "incremental"
        query_end = today + QUERY_AHEAD
        print(f"{mode} pull [{self.code}]: {pull_start} .. {query_end} "
              f"({len(stored)} awards in store)")

        max_monthly = self.checks["max_monthly"]
        collected = {}
        for mstart, mend in month_windows(pull_start, query_end):
            month_key = mstart.strftime("%Y-%m")
            for a in self.fetch_window(mstart, mend).values():
                d = time.strptime(a["date"], "%m/%d/%Y")
                award_date = date(d.tm_year, d.tm_mon, d.tm_mday)
                if not SERIES_START <= award_date <= today:
                    continue  # padding can catch a day outside the series
                collected[a["id"]] = {
                    "id": a["id"],
                    "date": award_date.isoformat(),
                    "month": f"{d.tm_year:04d}-{d.tm_mon:02d}",
                    "amount": int(float(a.get("estimatedTotalAmt") or 0)),
                    "type": norm_type(a.get("transType")),
                    "transType": a.get("transType") or "",
                    "title": a.get("title") or "",
                    "awardee": a.get("awardeeName") or "",
                }
            n = sum(1 for a in collected.values() if a["month"] == month_key)
            print(f"  {month_key}: {n} awards", flush=True)
            if n > max_monthly:
                sys.exit(f"FATAL: {month_key} returned {n} awards - above the "
                         f"{max_monthly}/month plausibility cap for this unit. "
                         "The division filter was probably ignored; aborting.")

        # Merge pull into the store: update or add only, never delete. A
        # stored award missing from this pull is RETAINED and flagged - API
        # downtime, filter quirks, or lost history can never erase our copy.
        merged = dict(stored)
        merged.update(collected)
        missing = sum(1 for aid in stored if aid not in collected)
        if mode == "full" and missing > 0:
            self.warn(f"{missing} stored awards not returned by this full "
                      "re-pull; retained from the store")

        awards = list(merged.values())
        total = len(awards)
        print(f"Total unique awards [{self.code}]: {total}")
        if not self.checks["min_total"] <= total <= self.checks["max_total"]:
            sys.exit(f"FATAL: implausible total {total} for this unit "
                     f"(allowed {self.checks['min_total']}..{self.checks['max_total']}). "
                     "Refusing to publish.")

        baseline_path = self.checks.get("baseline")
        if baseline_path:
            self.check_baseline(awards, repo_root / baseline_path)
        return awards, self.warnings

    def check_baseline(self, awards, baseline_path):
        """Drift check against an independently verified monthly baseline."""
        baseline = json.loads(baseline_path.read_text())["months"]
        monthly_counts = {}
        for a in awards:
            monthly_counts[a["month"]] = monthly_counts.get(a["month"], 0) + 1
        for month, (base_n, _) in baseline.items():
            if month >= "2026-07":
                continue  # trailing months legitimately grow as NSF backfills
            got = monthly_counts.get(month, 0)
            if abs(got - base_n) > max(3, base_n * 0.05):
                self.warn(f"{month}: pulled {got} awards vs verified baseline {base_n}")


def pull_unit(unit_cfg, store_path, full, today, repo_root):
    """Adapter entry point used by scripts/pull_unit.py.

    unit_cfg: the leaf dict from config/orgs.json (params + resolved checks).
    Returns (awards, warnings, source_description).
    """
    code = unit_cfg["params"]["org_code_div"]
    p = NsfPull(code, unit_cfg["checks"], store_path)
    awards, warnings = p.pull(full=full, today=today, repo_root=repo_root)
    source = (f"{API}?org_code_div={code} (NSF Award Search API), "
              "month-by-month on Original Award Date")
    metadata = {
        "provider": "nsf",
        "dataComplete": True,
        "storeFormat": "csv",
        "amountNote": ("Dollar figures are intended totals "
                       "(estimatedTotalAmt), not outlays."),
        "mechanismLabels": {
            "std": "Standard grants",
            "cont": "Continuing grants",
            "fell": "Fellowships",
            "other": "Other awards",
        },
    }
    return awards, warnings, source, metadata
