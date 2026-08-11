"""USAspending prime-award adapter.

USAspending's transaction rows are modifications layered on a base award.
This adapter deliberately uses the award search index instead: one row per
``generated_internal_id``, dated by ``Base Obligation Date`` and valued at
the award's current ``Award Amount`` (the award index's total obligation).

Completeness is checked per fiscal year and award-type group.  Every slice
is counted independently, paged in both ascending and descending award-ID
order, and accepted only when both unique-ID sets equal the count endpoint.
The API permits only one award-type group per request, so contracts, grants,
and the two other-assistance groups are queried separately and unioned.
"""

import json
import sys
import time
import urllib.error
import urllib.request
from datetime import date

from .common import SERIES_START, fiscal_year, load_store, store_exists

SEARCH_API = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
COUNT_API = "https://api.usaspending.gov/api/v2/search/spending_by_award_count/"
PAGE_SIZE = 100
RECENT_FYS = 2

# USAspending rejects a request that mixes these groups.  Include both the
# legacy and FABS 2.0 codes so a source migration cannot silently erase data.
AWARD_GROUPS = {
    "contracts": ["A", "B", "C", "D"],
    "grants": ["02", "03", "04", "05", "F001", "F002"],
    "direct_payments": ["06", "10", "F006", "F007"],
    "other_financial_assistance": [
        "09", "11", "-1", "F005", "F008", "F009", "F010",
    ],
}
COUNT_KEYS = {
    "contracts": "contracts",
    "grants": "grants",
    "direct_payments": "direct_payments",
    "other_financial_assistance": "other",
}
FIELDS = [
    "Award ID", "Recipient Name", "Base Obligation Date", "Award Amount",
    "Description", "Award Type", "Contract Award Type", "Awarding Agency",
    "Awarding Agency Code", "Awarding Sub Agency", "Awarding Sub Agency Code",
    "generated_internal_id",
]


def api_post(url, payload, retries=5):
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "science-funding-dashboard/3.1",
        },
        method="POST",
    )
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return json.load(response)
        except (OSError, ValueError, urllib.error.HTTPError) as exc:
            if attempt == retries - 1:
                raise RuntimeError(
                    f"USAspending request failed after {retries} tries: {url}"
                ) from exc
            time.sleep(2 ** attempt)


def _fy_dates(fy):
    return f"{fy - 1}-10-01", f"{fy}-09-30"


def _kind(group, description):
    label = description or "Unspecified"
    if group == "contracts":
        return "cont", f"Contract ({label})"
    if group == "grants":
        return "std", f"Grant or cooperative agreement ({label})"
    return "fell", f"Other financial assistance ({label})"


class USAspendingPull:
    def __init__(self, params, checks, store_path):
        self.params = params
        self.checks = checks
        self.store_path = store_path
        self.warnings = []

    def warn(self, message):
        self.warnings.append(message)
        print(f"WARNING: {message}", file=sys.stderr)

    def filters(self, fy, group):
        start, end = _fy_dates(fy)
        filters = {
            "time_period": [{"start_date": start, "end_date": end,
                             "date_type": "new_awards_only"}],
            "award_type_codes": AWARD_GROUPS[group],
        }
        agency = self.params.get("awarding_agency")
        if agency:
            filters["agencies"] = [{
                "type": "awarding",
                "tier": agency.get("tier", "toptier"),
                "name": agency["name"],
                **({"toptier_name": agency["toptier_name"]}
                   if agency.get("toptier_name") else {}),
            }]
        account = self.params.get("federal_account")
        if account:
            aid, main = account.split("-", 1)
            filters["treasury_account_components"] = [{"aid": aid, "main": main}]
        if self.params.get("program_activities"):
            filters["program_activities"] = self.params["program_activities"]
        if self.params.get("program_numbers"):
            filters["program_numbers"] = self.params["program_numbers"]
        return filters

    def fetch_count(self, fy, group):
        body = api_post(COUNT_API, {"filters": self.filters(fy, group)})
        results = body.get("results") or {}
        key = COUNT_KEYS[group]
        if key not in results:
            raise RuntimeError(f"USAspending count response is missing {key!r}")
        return int(results[key] or 0)

    def fetch_pass(self, fy, group, order, expected):
        by_id = {}
        page = 1
        cursor = {}
        while True:
            payload = {
                "filters": self.filters(fy, group),
                "fields": FIELDS,
                "subawards": False,
                "limit": PAGE_SIZE,
                "page": page,
                "sort": "generated_internal_id",
                "order": order,
                "spending_level": "awards",
                **cursor,
            }
            body = api_post(SEARCH_API, payload)
            if body.get("spending_level") != "awards":
                raise RuntimeError("USAspending returned the wrong spending level")
            if any("not used" in str(message).lower()
                   for message in body.get("messages") or []):
                raise RuntimeError(
                    f"USAspending ignored a configured filter: {body['messages']}")
            rows = body.get("results") or []
            metadata = body.get("page_metadata") or {}
            if not rows and len(by_id) < expected:
                raise RuntimeError(
                    f"FY{fy} {group} {order} returned an empty page after "
                    f"{len(by_id)} of {expected} awards")
            for row in rows:
                award_id = row.get("generated_internal_id")
                internal_id = row.get("internal_id")
                if not award_id or internal_id is None:
                    raise RuntimeError("USAspending row is missing a stable award ID")
                day_text = row.get("Base Obligation Date")
                try:
                    day = date.fromisoformat(str(day_text)[:10])
                except (TypeError, ValueError) as exc:
                    raise RuntimeError(
                        f"USAspending award {award_id} has invalid base obligation "
                        f"date {day_text!r}") from exc
                if fiscal_year(day) != fy:
                    raise RuntimeError(
                        f"USAspending fiscal-year filter mismatch: requested FY{fy}, "
                        f"got {day} for {award_id}")
                by_id[str(award_id)] = row
            if not metadata.get("hasNext"):
                break
            last_id = metadata.get("last_record_unique_id")
            last_sort = metadata.get("last_record_sort_value")
            if last_id is None or last_sort is None:
                raise RuntimeError("USAspending pagination cursor is missing")
            cursor = {
                "last_record_unique_id": last_id,
                "last_record_sort_value": last_sort,
            }
            page += 1
        if len(by_id) != expected:
            raise RuntimeError(
                f"FY{fy} {group} {order} returned {len(by_id)} unique awards "
                f"vs count endpoint {expected}")
        return by_id

    def fetch_slice(self, fy, group, attempts=3):
        last_error = None
        for attempt in range(attempts):
            try:
                before = self.fetch_count(fy, group)
                asc = self.fetch_pass(fy, group, "asc", before)
                desc = self.fetch_pass(fy, group, "desc", before)
                after = self.fetch_count(fy, group)
                signatures_a = {
                    aid: (row.get("Award Amount"), row.get("Base Obligation Date"))
                    for aid, row in asc.items()
                }
                signatures_d = {
                    aid: (row.get("Award Amount"), row.get("Base Obligation Date"))
                    for aid, row in desc.items()
                }
                if before != after or signatures_a != signatures_d:
                    raise RuntimeError(
                        f"FY{fy} {group} snapshots disagree (count "
                        f"{before}->{after}, asc={len(asc)}, desc={len(desc)})")
                asc.update(desc)
                return asc
            except RuntimeError as exc:
                last_error = exc
                if attempt + 1 < attempts:
                    print(f"retrying FY{fy} {group} snapshot: {exc}", file=sys.stderr)
                    time.sleep(2 ** attempt)
        raise last_error

    def normalize(self, row, group):
        stable_id = str(row["generated_internal_id"])
        day = date.fromisoformat(str(row["Base Obligation Date"])[:10])
        description = row.get("Contract Award Type") or row.get("Award Type")
        kind, transaction_type = _kind(group, description)
        return {
            "id": f"usaspending:{stable_id}",
            "date": day.isoformat(),
            "month": day.strftime("%Y-%m"),
            "amount": int(round(float(row.get("Award Amount") or 0))),
            "type": kind,
            "transType": transaction_type,
            "title": row.get("Description") or row.get("Award ID") or stable_id,
            "awardee": row.get("Recipient Name") or "",
        }

    def pull(self, full, today):
        stored = load_store(self.store_path)
        has_prior_store = store_exists(self.store_path)
        first_fy, current_fy = fiscal_year(SERIES_START), fiscal_year(today)
        if full or not has_prior_store:
            years = list(range(first_fy, current_fy + 1))
            mode = "full"
        else:
            years = list(range(max(first_fy, current_fy - RECENT_FYS + 1),
                               current_fy + 1))
            mode = "incremental"
        print(f"{mode} USAspending pull: FY{years[0]}..FY{years[-1]} "
              f"({len(stored)} awards in store)")

        collected = {}
        for fy in years:
            fy_count = 0
            for group in AWARD_GROUPS:
                rows = self.fetch_slice(fy, group)
                for row in rows.values():
                    award = self.normalize(row, group)
                    collected[award["id"]] = award
                fy_count += len(rows)
            print(f"  FY{fy}: {fy_count} prime awards", flush=True)

        merged = dict(stored)
        merged.update(collected)
        if mode == "full":
            missing = sum(1 for award_id in stored if award_id not in collected)
            if missing:
                self.warn(f"{missing} stored awards not returned by this full "
                          "re-pull; retained from the store")

        awards = list(merged.values())
        total = len(awards)
        if not self.checks["min_total"] <= total <= self.checks["max_total"]:
            raise SystemExit(
                f"FATAL: implausible USAspending total {total} (allowed "
                f"{self.checks['min_total']}..{self.checks['max_total']})")
        monthly = {}
        for award in awards:
            monthly[award["month"]] = monthly.get(award["month"], 0) + 1
        too_large = [(month, count) for month, count in sorted(monthly.items())
                     if count > self.checks["max_monthly"]]
        if too_large:
            month, count = too_large[0]
            raise SystemExit(
                f"FATAL: {month} has {count} USAspending awards, above the "
                f"{self.checks['max_monthly']}/month plausibility cap")
        return awards, self.warnings


def pull_unit(unit_cfg, store_path, full, today, repo_root):
    del repo_root
    puller = USAspendingPull(unit_cfg["params"], unit_cfg["checks"], store_path)
    awards, warnings = puller.pull(full=full, today=today)
    account = unit_cfg["params"].get("federal_account", "configured scope")
    source = (
        f"{SEARCH_API} (USAspending award search), federal account {account}; "
        "one prime record per base award, dated by base obligation and valued "
        "at current total obligations"
    )
    metadata = {
        "provider": "usaspending",
        "dataComplete": True,
        "storeFormat": "fiscal-year-gzip",
        "amountNote": ("Dollar figures are each prime award's current total "
                       "obligations, not annual obligations or outlays."),
        "mechanismLabels": {
            "std": "Grants & cooperative agreements",
            "cont": "Contracts",
            "fell": "Other assistance",
            "other": "Other awards",
        },
    }
    return awards, warnings, source, metadata
