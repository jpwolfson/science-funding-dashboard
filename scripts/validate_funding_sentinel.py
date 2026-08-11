#!/usr/bin/env python3
"""Fail-closed validation for the funding-action sentinel core."""

import argparse
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from adapters.funding_sentinel import (
    COVERAGE_DISCLAIMER,
    LIMITATIONS,
    PUBLIC_STATES,
    SCHEMA_VERSION,
    SEPARATE_AMOUNT_FIELDS,
    VALID_EVENT_TYPES,
    VALID_REVIEW_FINDINGS,
    apply_source_freshness,
    build_coverage,
    build_episodes,
    content_sha256,
    detect_financial_observations,
    load_ledger_events,
    load_sentinel_stores,
    normalize_sourced_event,
)


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _duplicates(rows):
    counts = Counter(row.get("id") for row in rows)
    return sorted(key for key, count in counts.items() if key and count > 1)


def validate(repo=REPO, require_data=True):
    repo = Path(repo)
    errors = []
    try:
        config = json.loads((repo / "config" / "funding_sentinel.json").read_text())
    except (OSError, json.JSONDecodeError) as error:
        return [f"funding sentinel registry cannot be read: {error}"]
    if config.get("schemaVersion") != SCHEMA_VERSION:
        errors.append("funding sentinel registry schema must be v1")
    detector = config.get("financialDetector") or {}
    for key in ("materialGrossNegativeCents", "clusterGrossNegativeCents",
                "clusterMinimumDistinctAwards"):
        if not isinstance(detector.get(key), int) or detector.get(key, 0) <= 0:
            errors.append(f"financial detector requires a positive integer {key}")
    try:
        stores = load_sentinel_stores(repo)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        return errors + [str(error)]

    observations = stores["observations"]["observations"]
    events = stores["events"]["events"]
    findings = stores["reviews"]["findings"]
    sources = stores["sources"]["sources"]
    episodes = stores["episodes"]["episodes"]
    for label, rows in (("financial observations", observations),
                        ("sourced events", events),
                        ("review findings", findings),
                        ("source statuses", sources),
                        ("episodes", episodes)):
        duplicate_ids = _duplicates(rows)
        if duplicate_ids:
            errors.append(f"duplicate {label} IDs: {duplicate_ids}")

    try:
        ledger_rows, accounts = load_ledger_events(repo)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        errors.append(f"obligation ledger cannot be read: {error}")
        ledger_rows, accounts = [], {}
    for row in ledger_rows:
        row["accountPath"] = accounts.get(row["federalAccount"], {}).get("path", "")
    ledger = {row["id"]: row for row in ledger_rows}
    active = [row for row in observations if row.get("active", True)]
    generated = stores["observations"].get("generated") or date.today().isoformat()
    try:
        date.fromisoformat(generated)
        expected = detect_financial_observations(
            ledger_rows, detector, generated, previous=[]
        )
    except (KeyError, TypeError, ValueError) as error:
        errors.append(f"financial detector cannot be reproduced: {error}")
        expected = []
    actual_by_id = {row["id"]: row for row in active}
    expected_by_id = {row["id"]: row for row in expected}
    if set(actual_by_id) != set(expected_by_id):
        errors.append("active financial observation IDs do not match detector output")
    for observation_id in sorted(set(actual_by_id) & set(expected_by_id)):
        if actual_by_id[observation_id].get("contentSha256") != expected_by_id[observation_id].get("contentSha256"):
            errors.append(f"{observation_id}: content differs from detector output")
    if require_data and not active:
        errors.append("sentinel has no active financial observations")
    for observation in observations:
        prefix = observation.get("id", "financial observation")
        if observation.get("recordType") != "financial-observation":
            errors.append(f"{prefix}: incorrect record type")
        if not SHA256_RE.fullmatch(str(observation.get("contentSha256", ""))):
            errors.append(f"{prefix}: invalid content SHA-256")
        if observation.get("grossNegativeCents", 0) >= 0:
            errors.append(f"{prefix}: gross negative activity must remain signed negative")
        if observation.get("grossPositiveCents", -1) < 0:
            errors.append(f"{prefix}: gross positive activity cannot be negative")
        if (observation.get("grossNegativeCents", 0) +
                observation.get("grossPositiveCents", 0) !=
                observation.get("netActivityCents")):
            errors.append(f"{prefix}: gross components do not reconcile to net activity")
        event_ids = observation.get("ledgerEventIds") or []
        if not event_ids:
            errors.append(f"{prefix}: no stable ledger event joins")
        for event_id in event_ids:
            event = ledger.get(event_id)
            if not event:
                if observation.get("active", True):
                    errors.append(f"{prefix}: active join {event_id} is missing from the ledger")
                continue
            if event.get("source") != "file_c":
                errors.append(f"{prefix}: File B residual {event_id} cannot trigger a signal")

    registered_sources = config.get("sources", [])
    source_ids = {row.get("id") for row in registered_sources}
    if len(source_ids) != len(registered_sources):
        errors.append("funding source registry contains duplicate IDs")
    for source in registered_sources:
        prefix = source.get("id", "funding source")
        if not source.get("adapter"):
            errors.append(f"{prefix}: source adapter is missing")
        if not re.fullmatch(r"https://[^\s]+", str(source.get("url", ""))):
            errors.append(f"{prefix}: source URL must be public HTTPS")
        if not isinstance(source.get("freshnessMaxDays"), int) or source.get(
                "freshnessMaxDays", 0) <= 0:
            errors.append(f"{prefix}: freshnessMaxDays must be positive")
    status_ids = {row.get("id") for row in sources}
    if require_data and source_ids - status_ids:
        errors.append(
            f"registered sources lack a first attempted snapshot: "
            f"{sorted(source_ids - status_ids)}"
        )
    expected_sources = apply_source_freshness(
        sources, config.get("sources", []), generated
    )
    if sources != expected_sources:
        errors.append("source status store does not apply the registered freshness SLA")
    for status in sources:
        prefix = status.get("id", "source status")
        if prefix not in source_ids:
            errors.append(f"{prefix}: source status is not registered")
        if status.get("status") not in {"current", "stale", "error"}:
            errors.append(f"{prefix}: unsupported source status")
        if status.get("lastAcceptedSha256") is not None and not SHA256_RE.fullmatch(
                str(status.get("lastAcceptedSha256"))):
            errors.append(f"{prefix}: invalid last accepted source SHA-256")
        history = status.get("snapshotHistory") or []
        if status.get("lastAcceptedSha256") and (
                not history or history[-1].get("sha256") !=
                status.get("lastAcceptedSha256")):
            errors.append(f"{prefix}: accepted snapshot history is missing or stale")
        if history and any(not SHA256_RE.fullmatch(str(row.get("sha256", "")))
                           for row in history):
            errors.append(f"{prefix}: snapshot history contains an invalid SHA-256")
        if status.get("status") in {"stale", "error"} and status.get("lastAcceptedAt"):
            accepted = set(status.get("acceptedEventIds") or [])
            retained = {event["id"] for event in events
                        if event.get("sourceId") == prefix}
            if not accepted <= retained:
                errors.append(f"{prefix}: failure did not preserve the last accepted events")
        if status.get("status") == "stale" and status.get("ageDays", -1) <= status.get(
                "freshnessMaxDays", 0):
            errors.append(f"{prefix}: source is marked stale before its SLA expires")

    for event in events:
        prefix = event.get("id", "sourced event")
        if event.get("recordType") != "sourced-status-event":
            errors.append(f"{prefix}: incorrect sourced event record type")
        if event.get("eventType") not in VALID_EVENT_TYPES:
            errors.append(f"{prefix}: unsupported sourced event type")
        if event.get("sourceId") not in source_ids:
            errors.append(f"{prefix}: source is not registered")
        try:
            normalized = normalize_sourced_event(event, event.get("sourceId"))
            if normalized["id"] != event.get("id"):
                errors.append(f"{prefix}: sourced event ID is not stable")
        except (TypeError, ValueError) as error:
            errors.append(f"{prefix}: {error}")
        for field in SEPARATE_AMOUNT_FIELDS:
            if event.get(field) is not None and not isinstance(event[field], int):
                errors.append(f"{prefix}: {field} must be exact integer cents")
        if (event.get("announcedAffectedValueQualifier") is not None and
                event.get("announcedAffectedValueCents") is None):
            errors.append(
                f"{prefix}: announced amount qualifier lacks an announced amount"
            )
        for field in ("announcedAwardCount", "announcedProjectCount"):
            if event.get(field) is not None and (
                    not isinstance(event[field], int) or event[field] < 0):
                errors.append(f"{prefix}: {field} must be a nonnegative integer")
        award_ids = event.get("awardIds") or []
        if (not isinstance(award_ids, list) or
                len(award_ids) != len(set(award_ids)) or
                any(not isinstance(value, str) or not value for value in award_ids)):
            errors.append(f"{prefix}: awardIds must be unique nonempty strings")
        source_status = next(
            (row for row in sources if row.get("id") == event.get("sourceId")),
            None,
        )
        if (event.get("active", True) and source_status and
                source_status.get("lastAcceptedSha256") and
                event.get("sourceSha256") != source_status["lastAcceptedSha256"]):
            errors.append(f"{prefix}: active event does not match last accepted source")

    active_doe = [row for row in events if row.get("active", True) and
                  row.get("sourceId") == "doe-october-2025-portfolio-action"]
    if "doe-october-2025-portfolio-action" in source_ids and active_doe:
        if len(active_doe) != 1:
            errors.append("DOE October 2025 source must contain one announcement event")
        else:
            event = active_doe[0]
            expected_offices = next(
                row["expectedOffices"] for row in registered_sources
                if row["id"] == "doe-october-2025-portfolio-action"
            )
            if (event.get("eventType"), event.get("announcedAction")) != (
                    "announcement", "termination"):
                errors.append("DOE October 2025 action must remain a termination announcement")
            if event.get("announcedAffectedValueDisplay") != "approximately $7.56 billion":
                errors.append("DOE October 2025 amount qualifier or source amount changed")
            if (event.get("announcedAwardCount"),
                    event.get("announcedProjectCount")) != (321, 223):
                errors.append("DOE October 2025 award/project counts changed")
            if event.get("namedOffices") != expected_offices:
                errors.append("DOE October 2025 six-office attribution changed")
            for field in ("observedDeobligationCents", "eliminatedFutureValueCents",
                          "restoredValueCents"):
                if event.get(field) is not None:
                    errors.append(f"DOE announcement cannot populate {field}")

    known_episode_ids = {row.get("id") for row in episodes}
    for finding in findings:
        prefix = finding.get("id", "review finding")
        if finding.get("finding") not in VALID_REVIEW_FINDINGS:
            errors.append(f"{prefix}: unsupported bounded review finding")
        if finding.get("episodeId") not in known_episode_ids:
            errors.append(f"{prefix}: review references an unknown episode")
        if not finding.get("reviewedAt"):
            errors.append(f"{prefix}: review timestamp is missing")

    try:
        expected_episodes = build_episodes(observations, events, findings, generated)
        if episodes != expected_episodes:
            errors.append("episode store does not match deterministic correlation output")
    except (KeyError, TypeError, ValueError) as error:
        errors.append(f"episode correlation cannot be reproduced: {error}")
    for episode in episodes:
        prefix = episode.get("id", "episode")
        if episode.get("state") not in PUBLIC_STATES:
            errors.append(f"{prefix}: unsupported public state")
        if episode.get("state") == "unreviewed-signal":
            if not isinstance(episode.get("unreviewedAgeDays"), int):
                errors.append(f"{prefix}: unreviewed age is missing")
            if episode.get("sourcedEventIds") or episode.get("reviewFindingIds"):
                errors.append(f"{prefix}: sourced/reviewed episode is mislabeled unreviewed")

    dashboard_path = repo / "data" / "sentinel" / "dashboard.json"
    try:
        dashboard = json.loads(dashboard_path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        errors.append(f"sentinel dashboard cannot be read: {error}")
        dashboard = {}
    if (dashboard.get("kind"), dashboard.get("schemaVersion")) != (
            "sentinel", SCHEMA_VERSION):
        errors.append("sentinel dashboard kind/schema mismatch")
    if dashboard.get("episodes") != episodes:
        errors.append("sentinel dashboard episodes differ from the durable store")
    if dashboard.get("sourceStatuses") != sources:
        errors.append("sentinel dashboard source statuses differ from the durable store")
    expected_coverage = build_coverage(accounts, config.get("sources", []))
    if dashboard.get("coverage") != expected_coverage:
        errors.append(
            "sentinel dashboard coverage does not match the account and source registries"
        )
    if (dashboard.get("coverage") or {}).get("disclaimer") != COVERAGE_DISCLAIMER:
        errors.append("sentinel dashboard coverage disclaimer is missing")
    summary = dashboard.get("summary") or {}
    if summary.get("episodeCount") != len(episodes):
        errors.append("sentinel dashboard episode count mismatch")
    if summary.get("financialObservationCount") != len(observations):
        errors.append("sentinel dashboard financial observation count mismatch")
    if len(dashboard.get("limitations") or []) != len(LIMITATIONS):
        errors.append("sentinel dashboard does not publish every coverage limitation")
    policy = (dashboard.get("reviewPolicy") or "").lower()
    if "review is optional" not in policy or "no award pull" not in policy:
        errors.append("sentinel dashboard does not publish its non-blocking review policy")
    if "not a confirmed cancellation" not in (
            dashboard.get("classificationPolicy") or "").lower():
        errors.append("sentinel dashboard classification disclaimer is missing")
    if not dashboard.get("maintenanceEstimates"):
        errors.append("sentinel dashboard maintenance-cost estimates are missing")
    if stores["observations"].get("detectorConfigSha256") != content_sha256(config):
        errors.append("financial observation store detector config hash mismatch")
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=REPO)
    parser.add_argument("--allow-empty", action="store_true")
    args = parser.parse_args()
    errors = validate(args.repo, require_data=not args.allow_empty)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print("Funding-action sentinel validation passed")


if __name__ == "__main__":
    main()
