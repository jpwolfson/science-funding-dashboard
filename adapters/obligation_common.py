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


def cents(value):
    """Convert a Decimal-like value to exact integer cents."""
    from decimal import Decimal, ROUND_HALF_UP
    return int((Decimal(str(value)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def dollars(value):
    return value / 100


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


def write_store(path, events, metadata=None):
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
    manifest = {
        "format": "obligation-events-csv-gzip-v1",
        "recordCount": len(normalized),
        "fiscalYears": sorted(by_fy),
        "sha256": hashlib.sha256("\n".join(sorted(ids)).encode()).hexdigest(),
        **(metadata or {}),
    }
    (path / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    return manifest


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
        "fileCCoverage": (file_c / net) if net else None,
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


def aggregate(events, current_fy=None, covered_periods=None, partial_fys=None):
    events = [normalize_event(e) for e in events]
    covered_periods = {
        canonical_period(label) for label in (covered_periods or [])
    }
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

    periods = []
    for label in sorted(by_period, key=lambda p: (period_info(p)[0], period_info(p)[1])):
        period_events = by_period[label]
        periods.append({"submissionPeriod": label,
                        "month": period_info(label)[2].isoformat()[:7],
                        **_metrics(period_events)})

    fiscal_years, cumulative = [], []
    for fy in sorted(by_fy):
        fy_events = by_fy[fy]
        fiscal_years.append({"fy": fy, "partial": fy in partial_fys,
                             **_metrics(fy_events),
                             "topRecipients": _top_recipients(fy_events),
                             "positiveFlows": _top_flows(fy_events, True),
                             "negativeFlows": _top_flows(fy_events, False)})
        running = []
        for row in [r for r in periods if period_info(r["submissionPeriod"])[0] == fy]:
            through = [e for e in fy_events if e["fiscalPeriod"] <= period_info(row["submissionPeriod"])[1]]
            end = period_info(row["submissionPeriod"])[2]
            day = (end - date(fy - 1, 10, 1)).days
            running.append({"d": day, "submissionPeriod": row["submissionPeriod"], **_metrics(through)})
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
                    partial_fys=None):
    out = {"kind": "obligations", "generated": date.today().isoformat(),
           "node": node, "source": source, "warnings": list(warnings or []),
           "dataComplete": not warnings,
           **aggregate(events, current_fy, covered_periods, partial_fys),
           "children": children or []}
    if metadata:
        out.update(metadata)
    path = Path(data_dir)
    path.mkdir(parents=True, exist_ok=True)
    (path / "dashboard.json").write_text(json.dumps(out, indent=1) + "\n")
    return out
