"""Exact-cents store and aggregation for the obligation ledger.

This module is intentionally separate from ``adapters.common``. Award records
deduplicate by award ID; obligation allocations are signed, additive events.
"""

import csv
import gzip
import hashlib
import io
import json
import re
from calendar import monthrange
from collections import defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import quote, unquote


CSV_HEADER = [
    "id", "source", "submissionPeriod", "fiscalYear", "fiscalPeriod",
    "date", "federalAccount", "programActivityCode", "programActivityName",
    "programActivityReportingKey", "amountCents", "awardId", "linked",
    "title", "recipientUEI", "recipient", "awardUrl", "sourceRowCount",
    "grossPositiveCents", "grossNegativeCents",
]
PERIOD_RE = re.compile(r"^FY(\d{4})(?:P(0[2-9]|1[0-2])|Q([1-4]))$")
LOCAL_AWARD_URL_RE = re.compile(
    r"^(?:https?://)?localhost(?::\d+)?/award/([^/?#]+)/?",
    re.IGNORECASE,
)
PROVENANCE_SUFFIX = ".provenance.json"


def cents(value):
    """Convert a Decimal-like value to exact integer cents."""
    from decimal import Decimal, ROUND_HALF_UP
    return int((Decimal(str(value)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def dollars(value):
    return value / 100


BASELINE_VARIANCE_FIELDS = (
    "fileBObligationsCents",
    "fileAFileBVarianceCents",
    "fileAFileBVarianceReason",
)


def baseline_file_b_cents(pin):
    """Return the exact File B ledger pin for one available baseline row."""
    if "fileBObligationsCents" in pin:
        return pin["fileBObligationsCents"]
    return pin["obligationsCents"]


def baseline_pin_problems(pin):
    """Validate the universal File A/File B baseline specialization schema."""
    status = pin.get("status")
    present = [field in pin for field in BASELINE_VARIANCE_FIELDS]
    if status == "unavailable":
        return (["source-unavailable row cannot declare a File A/File B variance"]
                if any(present) else [])
    problems = []
    if type(pin.get("obligationsCents")) is not int:
        problems.append("available row must declare integer obligationsCents")
    if any(present) and not all(present):
        missing = [field for field, exists in zip(BASELINE_VARIANCE_FIELDS, present)
                   if not exists]
        problems.append("File A/File B variance fields must be declared together; "
                        f"missing {missing}")
        return problems
    if all(present):
        file_a = pin.get("obligationsCents")
        file_b = pin.get("fileBObligationsCents")
        variance = pin.get("fileAFileBVarianceCents")
        reason = pin.get("fileAFileBVarianceReason")
        if type(file_b) is not int or type(variance) is not int:
            problems.append("File B and variance pins must be integer cents")
        elif type(file_a) is int and file_a - file_b != variance:
            problems.append("File A minus File B does not equal the declared variance")
        if variance == 0:
            problems.append("zero File A/File B variance must use the ordinary pin schema")
        if not isinstance(reason, str) or not reason.strip():
            problems.append("File A/File B variance requires a non-empty reason")
    return problems


def classify_file_b_periods(row_counts):
    """Classify one fiscal year's File B period snapshots as accepted.

    ``row_counts`` maps canonical submission-period labels, all within one
    fiscal year, to the raw row count returned by that period's File B
    download. This is the universal, registry-free snapshot-acceptance rule
    (see docs/obligation-ledger.md "Snapshot acceptance and not-reported
    periods"): a period whose own download returned zero rows, or fewer
    than half the previous *reported* period's rows in the same fiscal
    year, is ``notReported``. Its bytes and provenance are still kept
    upstream; this function only returns the classification.

    Returns ``{period: "reported" | "notReported"}``.
    """
    ordered = sorted(row_counts, key=lambda label: period_info(label)[1])
    status = {}
    last_reported_rows = None
    for label in ordered:
        rows = int(row_counts[label])
        if rows == 0 or (
                last_reported_rows is not None and rows < 0.5 * last_reported_rows):
            status[label] = "notReported"
        else:
            status[label] = "reported"
            last_reported_rows = rows
    return status


def check_final_period_reported(period_status, fy_complete):
    """Fail closed when a fiscal year cannot reconcile without its last period.

    ``period_status`` is one fiscal year's ``classify_file_b_periods``
    result. Raises ``ValueError`` when the highest-numbered period recorded
    is ``notReported`` and either it is P12 or the fiscal year's baseline
    pin says the year is complete -- a File B snapshot the GTAS total
    depends on is missing, and pinning through it would be exactly the
    empty-snapshot defect the acceptance rule exists to prevent.
    """
    if not period_status:
        return
    last_label = max(period_status, key=lambda label: period_info(label)[1])
    if period_status[last_label] != "notReported":
        return
    last_period = period_info(last_label)[1]
    if last_period == 12 or fy_complete:
        raise ValueError(
            f"{last_label} is notReported and the fiscal year cannot "
            "reconcile without it"
        )


def covers_and_effective(period_status):
    """Derive reporting-span relationships from a period-status map.

    ``period_status`` may span several fiscal years; periods are ordered by
    (fiscal year, period number) so spans never cross a fiscal-year
    boundary (each fiscal year's own P12/P02 reset is independent).

    Returns ``(covers, effective)``:

    - ``covers[reportedPeriod]`` is the ordered list of periods that
      reported period absorbs (itself last), present only when it follows
      one or more ``notReported`` periods -- i.e. length > 1. The site uses
      this to label a row "P12 (covers P11-P12)".
    - ``effective[period]`` is the reported period whose span covers it
      (itself, for a reported period). A ``notReported`` period with no
      later reported period yet in ``period_status`` -- a dangling tail on
      an in-progress pull -- is omitted: its File C events remain
      unmatched until a future pull supplies the covering reported period.
    """
    ordered = sorted(period_status, key=lambda label: period_info(label)[:2])
    covers, effective = {}, {}
    pending = []
    for label in ordered:
        if period_status[label] == "notReported":
            pending.append(label)
            continue
        span = pending + [label]
        if len(span) > 1:
            covers[label] = span
        for member in span:
            effective[member] = label
        pending = []
    return covers, effective


def file_b_row_counts_from_provenance(provenance):
    """Extract ``{period: rows}`` for File B downloads in one FY's provenance."""
    counts = {}
    fallback_fy = provenance.get("fiscalYear")
    for download in provenance.get("downloads") or []:
        scope = download.get("acceptedRequestScope") or {}
        if "object_class_program_activity" not in (scope.get("download_types") or []):
            continue
        filters = scope.get("filters") or {}
        period = filters.get("period")
        fy = filters.get("fy", fallback_fy)
        if period is None or fy is None:
            continue
        label = canonical_period(f"FY{int(fy)}P{int(period):02}")
        counts[label] = int(download.get("statusRowCount") or 0)
    return counts


def account_period_status(store, events, partial_fys=()):
    """Recompute an account's File B period classification from provenance.

    Reads each event-bearing fiscal year's committed
    ``FY####.provenance.json`` and reapplies ``classify_file_b_periods``, so
    dashboard rebuilds (``scripts/rollup_obligations.py``) and validation
    (``scripts/validate_obligations.py``) derive the identical status from
    the same source of truth without any network pull. This never raises:
    the P12/complete-year hard error
    (``check_final_period_reported``) is a validation-time concern (an
    already-committed historical fiscal year that turns out to end on a
    notReported period must be reported as a validation failure -- and,
    independently, will already fail the exact-cents GTAS gate since its
    File B cumulative total is now frozen short -- not crash the dashboard
    rebuild for every other account in the same process). Callers that want
    the hard error call ``check_final_period_reported`` themselves per
    fiscal year.
    """
    partial_fys = set(partial_fys)
    merged = {}
    for fy in sorted({event["fiscalYear"] for event in events}):
        provenance = load_partition_provenance(store, fy)
        if not provenance:
            continue
        row_counts = file_b_row_counts_from_provenance(provenance)
        if not row_counts:
            continue
        merged.update(classify_file_b_periods(row_counts))
    return merged


def merge_period_status(status_dicts):
    """Combine several accounts' per-period status for an agency/root rollup.

    A period is ``notReported`` at the combined grain only when every
    account that has an opinion on it agrees; a mix (or accounts silent on
    it, e.g. before this feature or with no File B download recorded) is a
    legitimate, if partly incomplete, reported total and must not be
    hidden from the combined chart.
    """
    votes = defaultdict(list)
    for status in status_dicts:
        for period, value in status.items():
            votes[period].append(value)
    return {
        period: ("notReported" if values and all(v == "notReported" for v in values)
                 else "reported")
        for period, values in votes.items()
    }


def period_info(label):
    match = PERIOD_RE.fullmatch(label or "")
    if not match:
        raise ValueError(f"invalid submission period: {label!r}")
    fy = int(match.group(1))
    period = int(match.group(2)) if match.group(2) else int(match.group(3)) * 3
    calendar_month = ((period + 8) % 12) + 1
    calendar_year = fy - 1 if calendar_month >= 10 else fy
    end = date(calendar_year, calendar_month, monthrange(calendar_year, calendar_month)[1])
    return fy, period, end


def canonical_period(label):
    """Canonicalize quarterly labels to their period-ending month."""
    fy, period, _ = period_info(label)
    return f"FY{fy}P{period:02}"


def stable_id(source, account, pa_code, submission_period, award_id=""):
    raw = "\x1f".join(("obligation-v1", source, account, pa_code,
                       submission_period, award_id))
    return hashlib.sha256(raw.encode()).hexdigest()


def normalize_award_url(value):
    """Replace USAspending's internal download permalink with its public URL."""
    value = str(value or "").strip()
    match = LOCAL_AWARD_URL_RE.match(value)
    if match:
        award_id = quote(unquote(match.group(1)), safe="")
        return f"https://www.usaspending.gov/award/{award_id}/"
    return value


def normalize_event(event):
    event = dict(event)
    event["submissionPeriod"] = canonical_period(event["submissionPeriod"])
    fy, period, end = period_info(event["submissionPeriod"])
    event.setdefault("fiscalYear", fy)
    event.setdefault("fiscalPeriod", period)
    event.setdefault("date", end.isoformat())
    event.setdefault("source", "file_c")
    event.setdefault("programActivityCode", "0000")
    event.setdefault("programActivityName", "Unknown / other")
    event.setdefault("programActivityReportingKey", "")
    event.setdefault("awardId", "")
    event.setdefault("linked", bool(event["awardId"]) and event["source"] == "file_c")
    event.setdefault("title", "")
    event.setdefault("recipientUEI", "")
    event.setdefault("recipient", "")
    event["awardUrl"] = normalize_award_url(event.get("awardUrl", ""))
    event.setdefault("sourceRowCount", 1)
    event.setdefault("grossPositiveCents", max(0, int(event["amountCents"])))
    event.setdefault("grossNegativeCents", min(0, int(event["amountCents"])))
    event["amountCents"] = int(event["amountCents"])
    event["grossPositiveCents"] = int(event["grossPositiveCents"])
    event["grossNegativeCents"] = int(event["grossNegativeCents"])
    event["sourceRowCount"] = int(event["sourceRowCount"])
    event["linked"] = bool(event["linked"])
    event.setdefault("id", stable_id(
        event["source"], event["federalAccount"], event["programActivityCode"],
        event["submissionPeriod"], event["awardId"]))
    if event["fiscalYear"] != fy or event["fiscalPeriod"] != period or event["date"] != end.isoformat():
        raise ValueError(f"period fields disagree for {event['id']}")
    return event


def _write_csv(fh, events):
    writer = csv.DictWriter(fh, fieldnames=CSV_HEADER, extrasaction="ignore")
    writer.writeheader()
    for event in sorted(events, key=lambda e: (e["date"], e["id"])):
        row = {key: event.get(key, "") for key in CSV_HEADER}
        row["linked"] = "true" if event.get("linked") else "false"
        writer.writerow(row)


def event_fingerprint(events):
    """Hash normalized event content, not only stable IDs.

    Stable IDs deliberately survive corrections.  A fingerprint used for
    replacement lineage therefore has to include every persisted field so a
    same-ID amount or metadata correction is visible.
    """
    rows = []
    for event in sorted((normalize_event(e) for e in events), key=lambda e: e["id"]):
        rows.append(json.dumps(
            {key: event.get(key, "") for key in CSV_HEADER},
            sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        ))
    return hashlib.sha256("\n".join(rows).encode()).hexdigest()


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def partition_diff(previous, current):
    """Return a compact, committed diff summary for a replaced partition."""
    before = {e["id"]: normalize_event(e) for e in previous}
    after = {e["id"]: normalize_event(e) for e in current}
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    changed = sorted(
        event_id for event_id in set(before) & set(after)
        if any(before[event_id].get(key, "") != after[event_id].get(key, "")
               for key in CSV_HEADER)
    )

    def ids_sha(values):
        return hashlib.sha256("\n".join(values).encode()).hexdigest()

    return {
        "previousRecordCount": len(before),
        "recordCount": len(after),
        "addedCount": len(added),
        "removedCount": len(removed),
        "changedCount": len(changed),
        "netAmountChangeCents": (
            sum(e["amountCents"] for e in after.values())
            - sum(e["amountCents"] for e in before.values())
        ),
        "addedIdsSha256": ids_sha(added),
        "removedIdsSha256": ids_sha(removed),
        "changedIdsSha256": ids_sha(changed),
    }


def provenance_path(store, fiscal_year):
    return Path(store) / f"FY{int(fiscal_year)}{PROVENANCE_SUFFIX}"


def load_partition_provenance(store, fiscal_year):
    path = provenance_path(store, fiscal_year)
    return json.loads(path.read_text()) if path.exists() else None


def write_partition_provenance(store, fiscal_year, value):
    value = dict(value)
    value.setdefault("schemaVersion", 2)
    value.setdefault("fiscalYear", int(fiscal_year))
    path = provenance_path(store, fiscal_year)
    path.write_text(json.dumps(value, indent=1, sort_keys=True) + "\n")
    return path


def rebuild_manifest(path, events=None, metadata=None):
    """Rebuild the schema-v2 manifest from committed shards and provenance."""
    path = Path(path)
    normalized = load_store(path) if events is None else [normalize_event(e) for e in events]
    by_fy = defaultdict(list)
    for event in normalized:
        by_fy[event["fiscalYear"]].append(event)
    partitions = []
    accepted_by_fy = {}
    for fy in sorted(by_fy):
        shard = path / f"FY{fy}.csv.gz"
        provenance = load_partition_provenance(path, fy)
        row = {
            "fiscalYear": fy,
            "file": shard.name,
            "recordCount": len(by_fy[fy]),
            "sha256": file_sha256(shard),
            "eventFingerprint": event_fingerprint(by_fy[fy]),
            "provenance": provenance_path(path, fy).name if provenance else None,
            "collectionStatus": (
                provenance.get("collectionStatus") if provenance else "missing"
            ),
        }
        partitions.append(row)
        if (provenance and provenance.get("collectionStatus") == "accepted"
                and provenance.get("acceptedAt")):
            accepted_by_fy[fy] = provenance["acceptedAt"]
    manifest = {
        "schemaVersion": 2,
        "format": "obligation-events-csv-gzip-v2",
        "recordCount": len(normalized),
        "fiscalYears": sorted(by_fy),
        "eventFingerprint": event_fingerprint(normalized),
        "partitions": partitions,
        "latestAcceptedAt": accepted_by_fy.get(max(by_fy)) if by_fy else None,
        **(metadata or {}),
    }
    (path / "manifest.json").write_text(
        json.dumps(manifest, indent=1, sort_keys=True) + "\n"
    )
    return manifest


def write_store(path, events, metadata=None, partition_metadata=None):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    normalized = [normalize_event(e) for e in events]
    ids = [e["id"] for e in normalized]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate obligation event ID")
    by_fy = defaultdict(list)
    for event in normalized:
        by_fy[event["fiscalYear"]].append(event)
    existing = {int(p.name[2:6]) for p in path.glob("FY????.csv.gz")}
    for fy in sorted(existing | set(by_fy)):
        shard = path / f"FY{fy}.csv.gz"
        with shard.open("wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
                with io.TextIOWrapper(zipped, encoding="utf-8", newline="") as fh:
                    _write_csv(fh, by_fy.get(fy, []))
    for fy, value in (partition_metadata or {}).items():
        write_partition_provenance(path, fy, value)
    return rebuild_manifest(path, normalized, metadata)


def load_store(path):
    events = []
    for shard in sorted(Path(path).glob("FY????.csv.gz")):
        with gzip.open(shard, "rt", newline="") as fh:
            for row in csv.DictReader(fh):
                row["amountCents"] = int(row["amountCents"])
                row["grossPositiveCents"] = int(row["grossPositiveCents"])
                row["grossNegativeCents"] = int(row["grossNegativeCents"])
                row["sourceRowCount"] = int(row["sourceRowCount"])
                row["linked"] = row["linked"].lower() == "true"
                row["fiscalYear"] = int(row["fiscalYear"])
                row["fiscalPeriod"] = int(row["fiscalPeriod"])
                events.append(normalize_event(row))
    ids = [e["id"] for e in events]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate obligation event ID across shards")
    return events


def _metrics(events):
    linked = [e for e in events if e["source"] == "file_c" and e["linked"]]
    file_c = sum(e["amountCents"] for e in events if e["source"] == "file_c")
    residual = sum(e["amountCents"] for e in events if e["source"] == "file_b_residual")
    net = file_c + residual
    return {
        "netObligationsCents": net,
        "netObligations": dollars(net),
        "awardLinkedObligationsCents": file_c,
        "awardLinkedObligations": dollars(file_c),
        "residualObligationsCents": residual,
        "residualObligations": dollars(residual),
        "grossObligationsCents": sum(e["grossPositiveCents"] for e in events),
        "grossObligations": dollars(sum(e["grossPositiveCents"] for e in events)),
        "deobligationsCents": sum(e["grossNegativeCents"] for e in events),
        "deobligations": dollars(sum(e["grossNegativeCents"] for e in events)),
        "distinctLinkedAwards": len({e["awardId"] for e in linked if e["awardId"]}),
        "fileCToNetRatio": (file_c / net) if net else None,
    }


def _top_recipients(events):
    groups = {}
    for event in events:
        if event["source"] != "file_c" or not event["linked"]:
            continue
        key = event["recipientUEI"] or event["recipient"] or "Unknown recipient"
        group = groups.setdefault(key, {"recipientUEI": event["recipientUEI"],
                                        "recipient": event["recipient"] or "Unknown recipient",
                                        "amountCents": 0, "awardIds": set()})
        group["amountCents"] += event["amountCents"]
        if event["awardId"]:
            group["awardIds"].add(event["awardId"])
    rows = sorted(groups.values(), key=lambda r: (-r["amountCents"], r["recipient"]))[:20]
    return [{"recipientUEI": r["recipientUEI"], "recipient": r["recipient"],
             "netObligationsCents": r["amountCents"],
             "netObligations": dollars(r["amountCents"]),
             "distinctLinkedAwards": len(r["awardIds"])} for r in rows]


def _top_flows(events, positive):
    amount_key = "grossPositiveCents" if positive else "grossNegativeCents"
    rows = [
        e for e in events
        if e["source"] == "file_c" and e["linked"] and e[amount_key] != 0
    ]
    rows.sort(key=lambda e: (-abs(e[amount_key]), e["id"]))
    return [{"id": e["id"], "awardId": e["awardId"], "title": e["title"],
             "recipient": e["recipient"], "amountCents": e[amount_key],
             "amount": dollars(e[amount_key]),
             "netAmountCents": e["amountCents"],
             "netAmount": dollars(e["amountCents"]),
             "submissionPeriod": e["submissionPeriod"],
             "awardUrl": e["awardUrl"]} for e in rows[:20]]


def aggregate(events, current_fy=None, covered_periods=None, partial_fys=None,
              period_status=None):
    events = [normalize_event(e) for e in events]
    period_status = dict(period_status or {})
    covered_periods = {
        canonical_period(label) for label in (covered_periods or [])
    } | set(period_status)
    covered_fys = {period_info(label)[0] for label in covered_periods}
    if current_fy is None:
        current_fy = max(
            {e["fiscalYear"] for e in events} | covered_fys,
            default=date.today().year,
        )
    # Callers that do not have an external availability contract retain the
    # historical behavior. Obligation rollups pass baseline-derived statuses
    # so an incomplete historical year cannot masquerade as complete.
    partial_fys = {current_fy} if partial_fys is None else set(partial_fys)
    by_period, by_fy = defaultdict(list), defaultdict(list)
    for event in events:
        by_period[event["submissionPeriod"]].append(event)
        by_fy[event["fiscalYear"]].append(event)
    # A Program Activity with no event in a covered period had zero activity;
    # it did not skip forward in time. Materialize those zero buckets so child
    # charts share the account timeline and current-year zeroes remain visible.
    for label in covered_periods:
        by_period[label]
        by_fy[period_info(label)[0]]

    covers, _ = covers_and_effective(period_status) if period_status else ({}, {})

    periods = []
    for label in sorted(by_period, key=lambda p: (period_info(p)[0], period_info(p)[1])):
        period_events = by_period[label]
        status = period_status.get(label, "reported")
        row = {"submissionPeriod": label,
               "month": period_info(label)[2].isoformat()[:7],
               "status": status}
        if status == "notReported":
            # No derived File B activity or residual exists for a
            # not-reported period (see "Snapshot acceptance and
            # not-reported periods" in docs/obligation-ledger.md); publish
            # no numeric period activity at all rather than the partial,
            # potentially misleading File-C-only total that would otherwise
            # land in this bucket.
            row.update({key: None for key in _metrics(period_events)})
        else:
            row.update(_metrics(period_events))
            if label in covers:
                row["coversPeriods"] = covers[label]
        periods.append(row)

    fiscal_years, cumulative = [], []
    for fy in sorted(by_fy):
        fy_events = by_fy[fy]
        fiscal_years.append({"fy": fy, "partial": fy in partial_fys,
                             **_metrics(fy_events),
                             "topRecipients": _top_recipients(fy_events),
                             "positiveFlows": _top_flows(fy_events, True),
                             "negativeFlows": _top_flows(fy_events, False)})
        fy_rows = [r for r in periods if period_info(r["submissionPeriod"])[0] == fy]
        running, last_reported_point = [], None
        for index, row in enumerate(fy_rows):
            label = row["submissionPeriod"]
            status = period_status.get(label, "reported")
            end = period_info(label)[2]
            day = (end - date(fy - 1, 10, 1)).days
            is_last = index == len(fy_rows) - 1
            if status == "notReported" and last_reported_point is not None and not is_last:
                # Hold the cumulative line at the last reported value
                # instead of dipping to the partial File-C-only total that
                # a not-reported period's own events would otherwise imply.
                # A dangling final period (no later reported point yet to
                # anchor a hold) is shown at its real, if incomplete, value
                # so the cumulative-endpoint invariant still holds exactly.
                point = {**last_reported_point, "d": day,
                         "submissionPeriod": label, "status": "notReported",
                         "held": True}
            else:
                through = [e for e in fy_events if e["fiscalPeriod"] <= period_info(label)[1]]
                point = {"d": day, "submissionPeriod": label, "status": status,
                         **_metrics(through)}
                if status == "reported":
                    last_reported_point = point
            running.append(point)
        cumulative.append({"fy": fy, "partial": fy in partial_fys, "points": running})
    totals = _metrics(events)
    return {**totals,
            "totalNetObligationsCents": totals["netObligationsCents"],
            "totalNetObligations": totals["netObligations"],
            "totalAwardLinkedObligationsCents": totals["awardLinkedObligationsCents"],
            "totalAwardLinkedObligations": totals["awardLinkedObligations"],
            "totalResidualObligationsCents": totals["residualObligationsCents"],
            "totalResidualObligations": totals["residualObligations"],
            "currentFY": current_fy,
            "asOfPeriod": periods[-1]["submissionPeriod"] if periods else None,
            "reportingPeriods": periods, "fiscalYears": fiscal_years,
            "fyCumulative": cumulative[-5:]}


def write_dashboard(data_dir, node, source, events, warnings=None, children=None,
                    current_fy=None, metadata=None, covered_periods=None,
                    partial_fys=None, period_status=None):
    out = {"schemaVersion": 2, "kind": "obligations",
           "generated": date.today().isoformat(),
           "node": node, "source": source, "warnings": list(warnings or []),
           "dataComplete": not warnings,
           **aggregate(events, current_fy, covered_periods, partial_fys,
                      period_status),
           "children": children or []}
    if metadata:
        out.update(metadata)
    path = Path(data_dir)
    path.mkdir(parents=True, exist_ok=True)
    (path / "dashboard.json").write_text(json.dumps(out, indent=1) + "\n")
    return out
