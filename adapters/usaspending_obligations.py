"""USAspending File B + File C adapter for appropriation obligations."""

import csv
import hashlib
import http.client
import io
import json
import time
import urllib.request
import urllib.error
import zipfile
from collections import defaultdict
from decimal import Decimal

from adapters.obligation_common import canonical_period, cents, normalize_event, stable_id


API = "https://api.usaspending.gov/api/v2"
_LAST_DOWNLOAD_REQUEST = 0.0


def _json(url, payload=None, attempts=10):
    body = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(url, data=body,
                                     headers={"Content-Type": "application/json",
                                              "User-Agent": "science-funding-dashboard/1"})
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return json.load(response)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError,
                http.client.RemoteDisconnected) as error:
            code = getattr(error, "code", None)
            if attempt + 1 == attempts or (code is not None and code not in (429, 500, 502, 503, 504)):
                raise
            time.sleep(min(30, 2 ** attempt))


def _bytes(url, attempts=6):
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "science-funding-dashboard/1"})
            with urllib.request.urlopen(request, timeout=300) as response:
                return response.read()
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError,
                http.client.RemoteDisconnected) as error:
            code = getattr(error, "code", None)
            if attempt + 1 == attempts or (code is not None and code not in (429, 500, 502, 503, 504)):
                raise
            time.sleep(min(30, 2 ** attempt))


def resolve_account(account, fiscal_year):
    row = _json(f"{API}/federal_accounts/{account}/?fiscal_year={fiscal_year}")
    resolved = row.get("federal_account_code") or row.get("account_number")
    if resolved != account:
        raise ValueError(f"resolved account mismatch: {resolved}")
    return str(row["id"]), row


def request_download(account_id, fiscal_year, period, submission_type, columns):
    global _LAST_DOWNLOAD_REQUEST
    # Custom-account generation is resource-intensive and the public service
    # drops bursty connections instead of always returning 429. Keep POSTs
    # serialized and spaced even after the previous archive finishes.
    elapsed = time.monotonic() - _LAST_DOWNLOAD_REQUEST
    if elapsed < 5:
        time.sleep(5 - elapsed)
    payload = {"account_level": "federal_account", "file_format": "csv",
               "filters": {"fy": fiscal_year, "period": period,
                           "submission_types": [submission_type],
                           "federal_account": str(account_id)},
               "columns": columns}
    result = _json(f"{API}/download/accounts/", payload)
    _LAST_DOWNLOAD_REQUEST = time.monotonic()
    echoed = result.get("download_request") or {}
    filters = echoed.get("filters", {})
    if echoed and (filters.get("federal_account") != str(account_id)
                   or int(filters.get("fy", -1)) != fiscal_year
                   or int(filters.get("period", -1)) != period
                   or echoed.get("download_types") != [submission_type]):
        raise ValueError(f"USAspending echoed a different request scope: {echoed}")
    return result, payload


def finish_download(result, timeout=1800, poll_seconds=15):
    status_url = result["status_url"]
    if status_url.startswith("/"):
        status_url = "https://api.usaspending.gov" + status_url
    deadline = time.monotonic() + timeout
    while True:
        status = _json(status_url)
        state = str(status.get("status", "")).lower()
        if state == "finished":
            break
        if state == "failed" or state not in {
                "ready", "queued", "running", "resumed", "created", "uploading"}:
            raise RuntimeError(f"custom-account download ended in {state!r}")
        if time.monotonic() >= deadline:
            raise TimeoutError("custom-account download did not finish")
        time.sleep(poll_seconds)
    file_url = status.get("file_url") or result.get("file_url")
    if not str(file_url).startswith("https://files.usaspending.gov/"):
        raise ValueError(f"unexpected download host: {file_url}")
    payload = _bytes(file_url)
    return payload, status


def archive_rows(payload):
    """Return {member name: CSV rows}; validates CRC and counts real records."""
    members = {}
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        if archive.testzip() is not None:
            raise ValueError("download ZIP failed CRC")
        for name in archive.namelist():
            if name.lower().endswith(".csv"):
                with archive.open(name) as raw:
                    text = io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")
                    members[name] = list(csv.DictReader(text))
    if not members:
        raise ValueError("download ZIP contains no CSV files")
    return members


def _first(row, *names):
    for name in names:
        if name in row and row[name] not in (None, ""):
            return row[name]
    return ""


def _pa(row, aliases):
    park = _first(row, "program_activity_reporting_key")
    code = _first(row, "program_activity_code").zfill(4) or "0000"
    name = _first(row, "program_activity_name") or "Unknown / other"
    identity = aliases.get(park) or aliases.get(code) or aliases.get(f"{code}:{name.lower()}")
    if not identity:
        identity = aliases.get("0000", {"code": "0000", "name": "Unknown / other", "park": ""})
    return identity["code"], identity["name"], identity.get("park", "") or park


def _award_identity(row):
    generated = _first(row, "award_unique_key", "generated_unique_award_id")
    if generated:
        return generated, True
    piid = _first(row, "award_id_piid")
    if piid:
        return f"PIID:{piid}:PARENT:{_first(row, 'parent_award_id_piid')}", False
    fain = _first(row, "award_id_fain")
    if fain:
        return f"FAIN:{fain}", False
    uri = _first(row, "award_id_uri")
    if uri:
        return f"URI:{uri}", False
    raw = json.dumps(sorted(row.items()), separators=(",", ":"))
    return "UNLINKED:" + hashlib.sha256(raw.encode()).hexdigest()[:24], False


def parse_file_c(members, account, aliases):
    names = " ".join(members).lower()
    for expected in ("assistance", "contract", "unlinked"):
        if expected not in names:
            raise ValueError(f"File C archive is missing {expected} CSV")
    grouped = {}
    raw_total = 0
    for rows in members.values():
        for row in rows:
            raw = _first(row, "transaction_obligated_amount")
            if raw == "":
                continue
            amount = cents(raw)
            if amount == 0:
                continue
            period = canonical_period(_first(row, "submission_period"))
            row_account = _first(row, "federal_account_symbol")
            if row_account and row_account != account:
                raise ValueError(f"File C account mismatch: {row_account}")
            code, name, park = _pa(row, aliases)
            award_id, linked = _award_identity(row)
            key = (award_id, account, code, period)
            if key not in grouped:
                grouped[key] = {"source": "file_c", "submissionPeriod": period,
                    "federalAccount": account, "programActivityCode": code,
                    "programActivityName": name, "programActivityReportingKey": park,
                    "amountCents": 0, "awardId": award_id, "linked": linked,
                    "title": _first(row, "prime_award_base_transaction_description"),
                    "recipientUEI": _first(row, "recipient_uei"),
                    "recipient": _first(row, "recipient_name"),
                    "awardUrl": _first(row, "usaspending_permalink"),
                    "sourceRowCount": 0, "grossPositiveCents": 0,
                    "grossNegativeCents": 0}
            event = grouped[key]
            event["amountCents"] += amount
            event["sourceRowCount"] += 1
            event["grossPositiveCents"] += max(amount, 0)
            event["grossNegativeCents"] += min(amount, 0)
            raw_total += amount
    events = []
    for event in grouped.values():
        event["id"] = stable_id("file_c", account, event["programActivityCode"],
                                event["submissionPeriod"], event["awardId"])
        events.append(normalize_event(event))
    if sum(e["amountCents"] for e in events) != raw_total:
        raise AssertionError("File C normalization changed the exact total")
    return events


def parse_file_b_snapshot(rows, account, aliases):
    """Return exact cumulative cents by the complete File B reconciliation grain."""
    values = defaultdict(int)
    for row in rows:
        row_account = _first(row, "federal_account_symbol")
        if row_account and row_account != account:
            raise ValueError(f"File B account mismatch: {row_account}")
        code, name, park = _pa(row, aliases)
        raw = _first(row, "obligations_incurred", "obligations_incurred_by_program_activity_object_class_cpe")
        if raw == "":
            continue
        key = (code, name, park,
               _first(row, "object_class_code"),
               _first(row, "direct_or_reimbursable_funding_source"),
               _first(row, "disaster_emergency_fund_code"),
               _first(row, "prior_year_adjustment"))
        values[key] += cents(raw)
    return values


def file_b_period_events(snapshots, account):
    """Delta cumulative File B snapshots without losing disappearing dimensions."""
    prior = {}
    output = []
    for submission_period, current in sorted(snapshots.items()):
        pa_deltas = defaultdict(int)
        for key in set(prior) | set(current):
            pa_deltas[key[:3]] += current.get(key, 0) - prior.get(key, 0)
        for (code, name, park), amount in sorted(pa_deltas.items()):
            output.append({"submissionPeriod": submission_period,
                           "federalAccount": account, "programActivityCode": code,
                           "programActivityName": name,
                           "programActivityReportingKey": park,
                           "amountCents": amount})
        prior = current
    return output


def combine_file_b_file_c(file_b_events, file_c_events, account):
    c_by_bucket = defaultdict(int)
    for event in file_c_events:
        c_by_bucket[(event["submissionPeriod"], event["programActivityCode"])] += event["amountCents"]
    residuals = []
    seen = set()
    for flow in file_b_events:
        key = (flow["submissionPeriod"], flow["programActivityCode"])
        if key in seen:
            raise ValueError(f"duplicate File B PA-period bucket: {key}")
        seen.add(key)
        amount = flow["amountCents"] - c_by_bucket.pop(key, 0)
        event = {**flow, "source": "file_b_residual", "amountCents": amount,
                 "awardId": "", "linked": False, "sourceRowCount": 1,
                 "grossPositiveCents": max(0, amount),
                 "grossNegativeCents": min(0, amount)}
        event["id"] = stable_id("file_b_residual", account,
                                event["programActivityCode"], event["submissionPeriod"])
        residuals.append(normalize_event(event))
    if c_by_bucket:
        raise ValueError(f"File C contains PA-period buckets absent from File B: {sorted(c_by_bucket)[:3]}")
    combined = list(file_c_events) + residuals
    if sum(e["amountCents"] for e in combined) != sum(e["amountCents"] for e in file_b_events):
        raise AssertionError("File B/File C residual identity failed")
    return combined


def alias_map(account_config):
    aliases = {}
    for row in account_config["programActivities"]:
        aliases[row["code"]] = row
        if row.get("park"):
            aliases[row["park"]] = row
        aliases[f"{row['code']}:{row['name'].lower()}"] = row
    return aliases
