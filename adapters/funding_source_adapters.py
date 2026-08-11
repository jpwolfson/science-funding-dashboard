"""Bounded authoritative-source adapters for Phase 3.2c-2.

Adapters accept raw bytes, validate the source-specific schema and facts, and
return normalized event candidates plus snapshot metadata. They do not write
stores; acceptance and last-good retention belong to funding_sentinel.py.
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser


NSF_COLUMNS = ("Award ID", "Directorate", "Recipient", "Title", "Obligated")


def _sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def _dollars_to_cents(value):
    cleaned = value.strip().replace("$", "").replace(",", "")
    try:
        amount = Decimal(cleaned)
    except InvalidOperation as error:
        raise ValueError(f"invalid dollar amount {value!r}") from error
    cents = amount * 100
    if cents != cents.to_integral_value():
        raise ValueError(f"dollar amount is not exact to cents: {value!r}")
    return int(cents)


def parse_nsf_terminated_awards(raw, source):
    """Parse NSF's official terminated-awards CSV without inferring dates."""
    if not raw or len(raw) > int(source.get("maximumBytes", 5_000_000)):
        raise ValueError("NSF terminated-awards response is empty or oversized")
    encoding = "utf-8-sig"
    try:
        text = raw.decode(encoding)
    except UnicodeDecodeError:
        # The live file currently contains Windows-1252 punctuation despite
        # otherwise ASCII-looking CSV. Preserve those characters losslessly.
        encoding = "cp1252"
        text = raw.decode(encoding)
    reader = csv.reader(io.StringIO(text, newline=""))
    try:
        header = next(reader)
    except StopIteration as error:
        raise ValueError("NSF terminated-awards CSV has no header") from error
    if tuple(cell.strip() for cell in header[:5]) != NSF_COLUMNS:
        raise ValueError(f"NSF terminated-awards schema changed: {header[:5]!r}")
    export_cells = [cell.strip() for cell in header[5:] if cell.strip()]
    if len(export_cells) != 1:
        raise ValueError("NSF terminated-awards CSV needs one export-date marker")
    match = re.fullmatch(r"Date of export:\s*(\d{1,2}/\d{1,2}/\d{4})",
                         export_cells[0])
    if not match:
        raise ValueError("NSF terminated-awards export date is malformed")
    source_as_of = datetime.strptime(match.group(1), "%m/%d/%Y").date().isoformat()
    snapshot_sha = _sha256(raw)
    events = []
    seen = set()
    for line_number, row in enumerate(reader, start=2):
        if not row or not any(cell.strip() for cell in row):
            continue
        if len(row) < 5 or any(cell.strip() for cell in row[5:]):
            raise ValueError(f"NSF CSV row {line_number} has unexpected columns")
        award_id, directorate, recipient, title, obligated = (
            cell.strip() for cell in row[:5]
        )
        if not re.fullmatch(r"\d{7,10}", award_id):
            raise ValueError(f"NSF CSV row {line_number} has invalid award ID")
        if award_id in seen:
            raise ValueError(f"NSF CSV contains duplicate award ID {award_id}")
        if not re.fullmatch(r"[A-Z0-9/-]{2,8}", directorate):
            raise ValueError(f"NSF CSV row {line_number} has invalid directorate")
        if not recipient or not title:
            raise ValueError(f"NSF CSV row {line_number} lacks recipient or title")
        prior_obligations = _dollars_to_cents(obligated)
        if prior_obligations < 0:
            raise ValueError(f"NSF CSV row {line_number} has negative obligations")
        seen.add(award_id)
        events.append({
            "sourceRecordId": award_id,
            "episodeKey": "portfolio|nsf|terminated-awards-2025",
            "eventType": "termination",
            "observedAt": source_as_of,
            "sourceAsOf": source_as_of,
            "sourceUrl": source["url"],
            "sourceSha256": snapshot_sha,
            "sourceTitle": "NSF terminated awards list",
            "statedReason": (
                "NSF's structured list identifies this award as terminated; "
                "the CSV does not state an award-specific reason or termination date."
            ),
            "awardIds": [award_id],
            "awardUrls": [
                f"https://www.nsf.gov/awardsearch/showAward?AWD_ID={award_id}"
            ],
            "directorate": directorate,
            "recipient": recipient,
            "awardTitle": title,
            "priorObligationsCents": prior_obligations,
        })
    if not events:
        raise ValueError("NSF terminated-awards CSV contains no award records")
    return {
        "events": events,
        "snapshotSha256": snapshot_sha,
        "metadata": {
            "sourceAsOf": source_as_of,
            "recordCount": len(events),
            "schema": list(NSF_COLUMNS),
            "encoding": encoding,
        },
    }


class _VisibleHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth_ignored = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            self.depth_ignored += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"} and self.depth_ignored:
            self.depth_ignored -= 1

    def handle_data(self, data):
        if not self.depth_ignored:
            self.parts.append(data)


def _visible_text(raw):
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("DOE announcement is not UTF-8 HTML") from error
    parser = _VisibleHTML()
    parser.feed(text)
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()


def parse_doe_portfolio_announcement(raw, source):
    """Parse only the exact bounded facts in DOE's October 2025 page."""
    if not raw or len(raw) > int(source.get("maximumBytes", 5_000_000)):
        raise ValueError("DOE announcement response is empty or oversized")
    text = _visible_text(raw)
    facts = re.search(
        r"announced the termination of\s+([\d,]+)\s+financial awards "
        r"supporting\s+([\d,]+)\s+projects, resulting in a savings of\s+"
        r"(approximately|about|up to|over|nearly)\s+\$([\d.]+)\s+billion",
        text,
        flags=re.IGNORECASE,
    )
    if not facts:
        raise ValueError("DOE announcement facts could not be extracted")
    award_count = int(facts.group(1).replace(",", ""))
    project_count = int(facts.group(2).replace(",", ""))
    qualifier = facts.group(3).lower()
    amount_decimal = Decimal(facts.group(4))
    amount_cents = int(amount_decimal * Decimal(1_000_000_000) * 100)
    expected = source["expectedFacts"]
    actual = {
        "awardCount": award_count,
        "projectCount": project_count,
        "amountCents": amount_cents,
        "amountQualifier": qualifier,
    }
    for key, value in actual.items():
        if expected.get(key) != value:
            raise ValueError(
                f"DOE announcement {key} drifted: expected {expected.get(key)!r}, "
                f"found {value!r}"
            )
    if expected["displayDate"] not in text:
        raise ValueError("DOE announcement display date is missing")
    offices = source["expectedOffices"]
    for office in offices:
        marker = f"{office['name']} ({office['abbrev']})"
        markers = [marker]
        if office["name"].startswith("Office of "):
            markers.append(
                f"Offices of {office['name'].removeprefix('Office of ')} "
                f"({office['abbrev']})"
            )
        if not any(value in text for value in markers):
            raise ValueError(f"DOE announcement office is missing: {marker}")
    snapshot_sha = _sha256(raw)
    display_amount = f"{qualifier} ${facts.group(4)} billion"
    event = {
        "sourceRecordId": "2025-10-01-portfolio-termination-announcement",
        "episodeKey": "portfolio|doe|2025-10-01-termination-announcement",
        "eventType": "announcement",
        "announcedAction": "termination",
        "effectiveDate": expected["effectiveDate"],
        "sourceAsOf": expected["effectiveDate"],
        "sourceUrl": source["url"],
        "sourceSha256": snapshot_sha,
        "sourceTitle": source["sourceTitle"],
        "statedReason": (
            "DOE attributed the decision to its financial review. This record "
            "represents the October 1, 2025 announcement only; later appeals, "
            "closeout, litigation, deobligations, and restorations require "
            "their own dated authoritative events."
        ),
        "awardIds": [],
        "announcedAffectedValueCents": amount_cents,
        "announcedAffectedValueQualifier": qualifier,
        "announcedAffectedValueDisplay": display_amount,
        "announcedAwardCount": award_count,
        "announcedProjectCount": project_count,
        "namedOffices": offices,
        "awardMapping": "not-published-by-source",
    }
    return {
        "events": [event],
        "snapshotSha256": snapshot_sha,
        "metadata": {
            "sourceAsOf": expected["effectiveDate"],
            "recordCount": 1,
            "schema": [
                "termination announcement", "announced affected value",
                "award count", "project count", "named offices",
            ],
        },
    }


ADAPTERS = {
    "nsf_terminated_awards_csv": parse_nsf_terminated_awards,
    "doe_portfolio_announcement": parse_doe_portfolio_announcement,
}


def parse_source(raw, source):
    try:
        adapter = ADAPTERS[source["adapter"]]
    except KeyError as error:
        raise ValueError(f"unsupported funding source adapter: {source.get('adapter')}") from error
    return adapter(raw, source)
