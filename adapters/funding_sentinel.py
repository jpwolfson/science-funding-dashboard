"""Generic stores and correlation for the funding-action sentinel.

The sentinel is deliberately downstream of the award and obligation ledgers.
It can surface mechanical financial signals, but it never changes or gates
either source ledger and never treats a negative amount as a cancellation.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from adapters.obligation_common import load_store


SCHEMA_VERSION = 1
STORE_FILES = {
    "observations": "financial-observations.json",
    "events": "sourced-events.json",
    "reviews": "review-findings.json",
    "sources": "source-status.json",
    "episodes": "episodes.json",
}
VALID_EVENT_TYPES = {
    "termination", "suspension", "appeal", "litigation", "supersession",
    "restoration", "other",
}
VALID_REVIEW_FINDINGS = {
    "confirmed-status-event",
    "routine-or-administrative-adjustment",
    "portfolio-action-awards-not-fully-mapped",
    "duplicate-of-episode",
    "insufficient-evidence",
    "superseded-or-restored",
}
PUBLIC_STATES = {
    "unreviewed-signal", "source-confirmed-event", "reviewed-finding",
    "superseded", "restored",
}
SEPARATE_AMOUNT_FIELDS = (
    "announcedAffectedValueCents",
    "observedDeobligationCents",
    "eliminatedFutureValueCents",
    "restoredValueCents",
)

LIMITATIONS = [
    {
        "title": "Incomplete discovery",
        "text": "There is no complete federal feed of terminations, suspensions, appeals, settlements, and reinstatements. This page covers registered sources and financial rules only.",
    },
    {
        "title": "No motive inference",
        "text": "Transaction amounts and agency prose do not establish why an action occurred beyond a reason explicitly attributed to a source.",
    },
    {
        "title": "No legal judgment",
        "text": "The sentinel cannot determine whether an action is lawful, final, or likely to survive appeal.",
    },
    {
        "title": "Amounts are not interchangeable",
        "text": "Announced affected value, prior obligations, posted deobligations, eliminated future funding, and later restorations are separate measures and may not reconcile.",
    },
    {
        "title": "Award mapping can be partial",
        "text": "A portfolio announcement without award identifiers cannot be completely joined to award-level records without another authoritative source.",
    },
    {
        "title": "Routine versus extraordinary remains unresolved",
        "text": "Thresholds can prioritize unusual activity but cannot distinguish ordinary amendments, closeout, corrections, partial reductions, and terminations.",
    },
    {
        "title": "No comprehensive real-time docket monitoring",
        "text": "Registered public pages can be monitored, but immediate or complete litigation coverage may require a paid or access-controlled service.",
    },
    {
        "title": "Sources are attributed, not independently proven",
        "text": "Archiving an authoritative source and reporting what it says does not independently verify every factual claim in that source.",
    },
    {
        "title": "Review is optional judgment",
        "text": "Software can assemble evidence and propose a bounded finding; no human or agent is assigned a queue or deadline.",
    },
]

MAINTENANCE_ESTIMATES = [
    {
        "activity": "Generic store, detector, validation, workflow, and site",
        "initial": "3–6 engineering days",
        "recurring": "Ordinarily none outside failures",
    },
    {
        "activity": "Each structured agency source",
        "initial": "0.5–2 engineering days",
        "recurring": "1–4 engineering hours when URL or schema changes",
    },
    {
        "activity": "Weekly fetch, diff, and signal build at pilot scale",
        "initial": "Included above",
        "recurring": "About 10–60 GitHub-hosted runner minutes/month",
    },
    {
        "activity": "Committed normalized records and source snapshots",
        "initial": "Included above",
        "recurring": "Roughly 1–20 MB/year at pilot scale",
    },
    {
        "activity": "Optional review",
        "initial": "None required",
        "recurring": "About 10–30 minutes straightforward; 30–120 minutes ambiguous",
    },
]


def _canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def content_sha256(value):
    return hashlib.sha256(_canonical_json(value).encode()).hexdigest()


def stable_id(prefix, *parts):
    raw = "\x1f".join((f"funding-sentinel-{SCHEMA_VERSION}", prefix,
                       *(str(part) for part in parts)))
    return f"{prefix}-{hashlib.sha256(raw.encode()).hexdigest()[:24]}"


def episode_id(episode_key):
    return stable_id("episode", episode_key)


def _read_store(path, kind, field):
    path = Path(path)
    if not path.exists():
        return {"schemaVersion": SCHEMA_VERSION, "kind": kind, field: []}
    value = json.loads(path.read_text())
    if value.get("schemaVersion") != SCHEMA_VERSION or value.get("kind") != kind:
        raise ValueError(f"{path}: unsupported {kind} store schema")
    if not isinstance(value.get(field), list):
        raise ValueError(f"{path}: {field} must be a list")
    return value


def _write_store(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=1, sort_keys=True,
                               ensure_ascii=False) + "\n")


def load_sentinel_stores(repo):
    root = Path(repo) / "data" / "sentinel"
    return {
        "observations": _read_store(
            root / STORE_FILES["observations"], "financial-observations",
            "observations"),
        "events": _read_store(
            root / STORE_FILES["events"], "sourced-events", "events"),
        "reviews": _read_store(
            root / STORE_FILES["reviews"], "review-findings", "findings"),
        "sources": _read_store(
            root / STORE_FILES["sources"], "source-status", "sources"),
        "episodes": _read_store(
            root / STORE_FILES["episodes"], "episodes", "episodes"),
    }


def load_ledger_events(repo):
    repo = Path(repo)
    registry = json.loads(
        (repo / "config" / "obligation_accounts.json").read_text()
    )
    rows = []
    accounts = {}
    for account in registry["accounts"]:
        accounts[account["federalAccount"]] = account
        store = repo / "data" / "obligations" / account["path"] / "events"
        if store.exists():
            rows.extend(load_store(store))
    return rows, accounts


def _observation_payload(rows, rules, observation_id, episode_key,
                         account_path, detected_at):
    rows = sorted(rows, key=lambda row: row["id"])
    periods = {row["submissionPeriod"] for row in rows}
    accounts = {row["federalAccount"] for row in rows}
    programs = {row["programActivityCode"] for row in rows}
    if len(periods) != 1 or len(accounts) != 1 or len(programs) != 1:
        raise ValueError("one financial observation must have one account/program/period")
    first = rows[0]
    semantic = {
        "id": observation_id,
        "recordType": "financial-observation",
        "episodeKey": episode_key,
        "ruleIds": sorted(rule["id"] for rule in rules),
        "rules": sorted(rules, key=lambda rule: rule["id"]),
        "observedDate": max(row["date"] for row in rows),
        "submissionPeriod": first["submissionPeriod"],
        "fiscalYear": first["fiscalYear"],
        "fiscalPeriod": first["fiscalPeriod"],
        "accountPath": account_path,
        "federalAccount": first["federalAccount"],
        "programActivityCode": first["programActivityCode"],
        "programActivityName": first["programActivityName"],
        "grossNegativeCents": sum(row["grossNegativeCents"] for row in rows),
        "grossPositiveCents": sum(row["grossPositiveCents"] for row in rows),
        "netActivityCents": sum(row["amountCents"] for row in rows),
        "ledgerEventIds": [row["id"] for row in rows],
        "awardIds": sorted({row["awardId"] for row in rows if row["awardId"]}),
        "recipients": sorted({row["recipient"] for row in rows
                              if row.get("recipient")}),
        "awardUrls": sorted({row["awardUrl"] for row in rows
                             if row.get("awardUrl")}),
        "classification": "unclassified-financial-signal",
        "classificationNote": (
            "Gross negative File C activity triggered a mechanical rule. "
            "The sign and amount do not establish a cancellation."
        ),
    }
    return {
        **semantic,
        "contentSha256": content_sha256(semantic),
        "firstDetectedAt": detected_at,
        "active": True,
    }


def detect_financial_observations(events, detector, detected_at,
                                  previous=()):
    """Detect material/clustered gross-negative File C activity.

    File B residuals are excluded before grouping. If a reporting-period
    bucket satisfies the cluster rule it becomes one portfolio observation;
    otherwise each material event becomes an award-correlated observation.
    """
    material = int(detector["materialGrossNegativeCents"])
    cluster_amount = int(detector["clusterGrossNegativeCents"])
    cluster_awards = int(detector["clusterMinimumDistinctAwards"])
    if min(material, cluster_amount, cluster_awards) <= 0:
        raise ValueError("sentinel detector thresholds must be positive")

    eligible = [
        row for row in events
        if row.get("source") == "file_c" and row.get("grossNegativeCents", 0) < 0
    ]
    buckets = defaultdict(list)
    for row in eligible:
        buckets[(row["federalAccount"], row["programActivityCode"],
                 row["submissionPeriod"])].append(row)

    current = []
    for (account, program, period), rows in sorted(buckets.items()):
        gross_negative = sum(row["grossNegativeCents"] for row in rows)
        distinct_awards = len({row["awardId"] for row in rows if row["awardId"]})
        material_rows = [
            row for row in rows if -row["grossNegativeCents"] >= material
        ]
        if -gross_negative >= cluster_amount and distinct_awards >= cluster_awards:
            rules = [{
                "id": "portfolio-cluster",
                "thresholdGrossNegativeCents": cluster_amount,
                "minimumDistinctAwards": cluster_awards,
                "actualDistinctAwards": distinct_awards,
            }]
            if material_rows:
                rules.append({
                    "id": "material-gross-negative",
                    "thresholdGrossNegativeCents": material,
                    "matchedLedgerEventIds": sorted(row["id"] for row in material_rows),
                })
            # Same-program clusters recur within a fiscal-year episode.  A
            # later fiscal year is not silently assumed to be the same action;
            # an accepted sourced event can still join them explicitly.
            key = f"portfolio|{account}|{program}|FY{rows[0]['fiscalYear']}"
            current.append(_observation_payload(
                rows, rules, stable_id("observation", "cluster", account,
                                       program, period), key,
                rows[0].get("accountPath", ""), detected_at,
            ))
        else:
            for row in sorted(material_rows, key=lambda value: value["id"]):
                key = (f"award|{account}|{row.get('awardId') or row['id']}"
                       f"|FY{row['fiscalYear']}")
                current.append(_observation_payload(
                    [row], [{
                        "id": "material-gross-negative",
                        "thresholdGrossNegativeCents": material,
                        "matchedLedgerEventIds": [row["id"]],
                    }],
                    stable_id("observation", "material", row["id"]), key,
                    row.get("accountPath", ""), detected_at,
                ))

    previous_by_id = {row["id"]: row for row in previous}
    merged = []
    current_ids = set()
    for row in current:
        old = previous_by_id.get(row["id"])
        current_ids.add(row["id"])
        if old:
            row["firstDetectedAt"] = old.get("firstDetectedAt", detected_at)
            if old.get("contentSha256") != row["contentSha256"]:
                history = list(old.get("supersededVersions", []))
                history.append({
                    "contentSha256": old.get("contentSha256"),
                    "supersededAt": detected_at,
                })
                row["supersededVersions"] = history
        merged.append(row)
    for old in previous:
        if old["id"] in current_ids:
            continue
        retained = dict(old)
        retained["active"] = False
        retained.setdefault("supersededAt", detected_at)
        retained.setdefault(
            "supersessionReason",
            "No longer present in the current ledger-derived detector output.",
        )
        merged.append(retained)
    return sorted(merged, key=lambda row: row["id"])


def normalize_sourced_event(event, source_id):
    value = dict(event)
    value["sourceId"] = source_id
    if value.get("eventType") not in VALID_EVENT_TYPES:
        raise ValueError(f"unsupported sourced event type: {value.get('eventType')!r}")
    if not value.get("episodeKey"):
        raise ValueError("sourced event is missing episodeKey")
    source_url = str(value.get("sourceUrl", ""))
    parsed = urlparse(source_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("sourced event requires a public HTTPS sourceUrl")
    source_hash = str(value.get("sourceSha256", ""))
    if len(source_hash) != 64 or any(ch not in "0123456789abcdef" for ch in source_hash):
        raise ValueError("sourced event requires a lowercase SHA-256 source hash")
    record_id = value.get("sourceRecordId") or value.get("id")
    if not record_id:
        raise ValueError("sourced event requires sourceRecordId")
    value["sourceRecordId"] = str(record_id)
    value["id"] = stable_id("source-event", source_id, value["sourceRecordId"])
    value["recordType"] = "sourced-status-event"
    value.setdefault("active", True)
    value.setdefault("awardIds", [])
    value.setdefault("sourceTitle", "")
    value.setdefault("statedReason", "")
    for field in SEPARATE_AMOUNT_FIELDS:
        if value.get(field) is not None:
            value[field] = int(value[field])
    return value


def accept_source_snapshot(existing_events, source_statuses, source_id,
                           extracted_events, snapshot_sha256, accepted_at):
    """Accept one validated source snapshot without erasing prior history."""
    if len(snapshot_sha256) != 64 or any(
            ch not in "0123456789abcdef" for ch in snapshot_sha256):
        raise ValueError("accepted source snapshot requires a lowercase SHA-256")
    normalized = [normalize_sourced_event(event, source_id)
                  for event in extracted_events]
    ids = [event["id"] for event in normalized]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate sourced event ID in accepted snapshot")

    by_id = {event["id"]: dict(event) for event in existing_events}
    accepted_ids = set(ids)
    for event_id, event in list(by_id.items()):
        if event.get("sourceId") == source_id and event_id not in accepted_ids:
            event["active"] = False
            event.setdefault("supersededAt", accepted_at)
    for event in normalized:
        old = by_id.get(event["id"])
        if old:
            event.setdefault("firstAcceptedAt", old.get("firstAcceptedAt", accepted_at))
        else:
            event.setdefault("firstAcceptedAt", accepted_at)
        event["active"] = True
        by_id[event["id"]] = event

    statuses = {row["id"]: dict(row) for row in source_statuses}
    old_status = statuses.get(source_id, {})
    statuses[source_id] = {
        **old_status,
        "id": source_id,
        "status": "current",
        "lastAttemptAt": accepted_at,
        "lastAcceptedAt": accepted_at,
        "lastAcceptedSha256": snapshot_sha256,
        "acceptedEventIds": sorted(ids),
        "error": None,
    }
    return (sorted(by_id.values(), key=lambda row: row["id"]),
            sorted(statuses.values(), key=lambda row: row["id"]))


def record_source_failure(source_statuses, source_id, attempted_at, error):
    """Record an adapter failure while retaining the last accepted snapshot."""
    statuses = {row["id"]: dict(row) for row in source_statuses}
    old = statuses.get(source_id, {})
    statuses[source_id] = {
        **old,
        "id": source_id,
        "status": "error",
        "lastAttemptAt": attempted_at,
        "error": str(error),
    }
    return sorted(statuses.values(), key=lambda row: row["id"])


def apply_source_freshness(source_statuses, registered_sources, as_of):
    """Mark accepted snapshots stale by registry SLA without removing data."""
    as_of_date = date.fromisoformat(as_of)
    registry = {row["id"]: row for row in registered_sources}
    output = []
    for source in source_statuses:
        value = dict(source)
        contract = registry.get(value.get("id"))
        if not contract:
            output.append(value)
            continue
        value.setdefault("name", contract.get("name", value["id"]))
        accepted_at = value.get("lastAcceptedAt")
        if accepted_at:
            accepted_date = date.fromisoformat(str(accepted_at)[:10])
            age = (as_of_date - accepted_date).days
            value["ageDays"] = age
            value["freshnessMaxDays"] = int(contract["freshnessMaxDays"])
            if value.get("status") == "current" and age > value["freshnessMaxDays"]:
                value["status"] = "stale"
        output.append(value)
    return sorted(output, key=lambda row: row["id"])


def _episode_state(observations, events, reviews):
    latest_event = max(
        events,
        key=lambda row: (row.get("effectiveDate") or row.get("observedAt") or "",
                         row["id"]),
        default=None,
    )
    latest_review = max(
        reviews,
        key=lambda row: (row.get("reviewedAt") or "", row["id"]),
        default=None,
    )
    if latest_review and latest_review.get("finding") == "superseded-or-restored":
        return "restored" if latest_review.get("disposition") == "restored" else "superseded"
    if latest_event and latest_event.get("eventType") == "restoration":
        return "restored"
    if latest_event and latest_event.get("eventType") == "supersession":
        return "superseded"
    if latest_review:
        return "reviewed-finding"
    if events:
        return "source-confirmed-event"
    if observations and not any(row.get("active", True) for row in observations):
        return "superseded"
    return "unreviewed-signal"


def build_episodes(observations, sourced_events, findings, as_of):
    groups = defaultdict(lambda: {"observations": [], "events": []})
    for observation in observations:
        groups[observation["episodeKey"]]["observations"].append(observation)
    for event in sourced_events:
        groups[event["episodeKey"]]["events"].append(event)

    episodes = []
    for key, values in sorted(groups.items()):
        observations_for_episode = values["observations"]
        events_for_episode = values["events"]
        identifier = episode_id(key)
        reviews = [row for row in findings if row.get("episodeId") == identifier]
        state = _episode_state(observations_for_episode, events_for_episode, reviews)
        dates = [row.get("observedDate") for row in observations_for_episode]
        dates += [row.get("effectiveDate") or row.get("observedAt")
                  for row in events_for_episode]
        dates = sorted(value for value in dates if value)
        active_observations = [row for row in observations_for_episode
                               if row.get("active", True)]
        program_names = sorted({row.get("programActivityName", "")
                                for row in observations_for_episode
                                if row.get("programActivityName")})
        source_titles = sorted({row.get("sourceTitle", "")
                                for row in events_for_episode
                                if row.get("sourceTitle")})
        title = (program_names[0] if program_names else
                 source_titles[0] if source_titles else "Funding-action episode")
        episode = {
            "id": identifier,
            "recordType": "episode",
            "episodeKey": key,
            "title": title,
            "state": state,
            "firstObserved": dates[0] if dates else None,
            "lastObserved": dates[-1] if dates else None,
            "financialObservationIds": sorted(row["id"] for row in observations_for_episode),
            "sourcedEventIds": sorted(row["id"] for row in events_for_episode),
            "reviewFindingIds": sorted(row["id"] for row in reviews),
            "federalAccounts": sorted({row.get("federalAccount")
                                        for row in observations_for_episode + events_for_episode
                                        if row.get("federalAccount")}),
            "programActivityCodes": sorted({row.get("programActivityCode")
                                             for row in observations_for_episode + events_for_episode
                                             if row.get("programActivityCode")}),
            "awardIds": sorted({award_id
                                for row in observations_for_episode + events_for_episode
                                for award_id in row.get("awardIds", [])}),
            "grossNegativeCents": sum(row["grossNegativeCents"]
                                      for row in active_observations),
            "grossPositiveCents": sum(row["grossPositiveCents"]
                                      for row in active_observations),
            "netActivityCents": sum(row["netActivityCents"]
                                    for row in active_observations),
            "financialObservations": sorted(
                observations_for_episode,
                key=lambda row: (row.get("observedDate", ""), row["id"]),
            ),
            "sourcedEvents": sorted(
                events_for_episode,
                key=lambda row: (row.get("effectiveDate") or row.get("observedAt") or "",
                                 row["id"]),
            ),
            "reviewFindings": sorted(
                reviews, key=lambda row: (row.get("reviewedAt", ""), row["id"])
            ),
        }
        if state == "unreviewed-signal" and dates:
            episode["unreviewedSince"] = dates[0]
            episode["unreviewedAgeDays"] = max(
                0, (date.fromisoformat(as_of) - date.fromisoformat(dates[0])).days
            )
        episodes.append(episode)

    known = {episode["id"] for episode in episodes}
    orphaned = sorted({row.get("episodeId") for row in findings
                       if row.get("episodeId") not in known})
    if orphaned:
        raise ValueError(f"review findings reference unknown episodes: {orphaned}")
    return sorted(episodes, key=lambda row: (
        row.get("lastObserved") or "", row["id"]), reverse=True)


def build(repo, as_of=None):
    repo = Path(repo)
    as_of = as_of or date.today().isoformat()
    date.fromisoformat(as_of)
    config_path = repo / "config" / "funding_sentinel.json"
    config = json.loads(config_path.read_text())
    if config.get("schemaVersion") != SCHEMA_VERSION:
        raise ValueError("funding sentinel registry schema must be v1")
    stores = load_sentinel_stores(repo)
    ledger_events, accounts = load_ledger_events(repo)
    for row in ledger_events:
        account = accounts.get(row["federalAccount"], {})
        row["accountPath"] = account.get("path", "")

    observations = detect_financial_observations(
        ledger_events, config["financialDetector"], as_of,
        stores["observations"]["observations"],
    )
    sourced_events = stores["events"]["events"]
    findings = stores["reviews"]["findings"]
    sources = apply_source_freshness(
        stores["sources"]["sources"], config.get("sources", []), as_of
    )
    episodes = build_episodes(observations, sourced_events, findings, as_of)
    root = repo / "data" / "sentinel"
    config_hash = content_sha256(config)

    _write_store(root / STORE_FILES["observations"], {
        "schemaVersion": SCHEMA_VERSION,
        "kind": "financial-observations",
        "generated": as_of,
        "detectorConfigSha256": config_hash,
        "observations": observations,
    })
    for key, kind, field, values in (
        ("events", "sourced-events", "events", sourced_events),
        ("reviews", "review-findings", "findings", findings),
        ("sources", "source-status", "sources", sources),
    ):
        value = dict(stores[key])
        value.update({"schemaVersion": SCHEMA_VERSION, "kind": kind,
                      field: values})
        _write_store(root / STORE_FILES[key], value)
    _write_store(root / STORE_FILES["episodes"], {
        "schemaVersion": SCHEMA_VERSION,
        "kind": "episodes",
        "generated": as_of,
        "episodes": episodes,
    })

    counts = {state: 0 for state in sorted(PUBLIC_STATES)}
    for episode in episodes:
        counts[episode["state"]] += 1
    dashboard = {
        "schemaVersion": SCHEMA_VERSION,
        "kind": "sentinel",
        "generated": as_of,
        "title": "Funding-action sentinel",
        "source": "Mechanical File C signals and registered authoritative sources",
        "summary": {
            "episodeCount": len(episodes),
            "financialObservationCount": len(observations),
            "sourcedEventCount": len(sourced_events),
            "reviewFindingCount": len(findings),
            "stateCounts": counts,
        },
        "detector": config["financialDetector"],
        "episodes": episodes,
        "sourceStatuses": sources,
        "limitations": LIMITATIONS,
        "maintenanceEstimates": MAINTENANCE_ESTIMATES,
        "reviewPolicy": (
            "Review is optional. Unreviewed signals remain publishable indefinitely; "
            "no award pull, obligation pull, validation, rollup, or deployment waits "
            "for a person, agent, issue, or finding."
        ),
        "classificationPolicy": (
            "A financial observation is not a confirmed cancellation. Confirmation "
            "requires an accepted authoritative sourced status event."
        ),
    }
    _write_store(root / "dashboard.json", dashboard)
    return dashboard
