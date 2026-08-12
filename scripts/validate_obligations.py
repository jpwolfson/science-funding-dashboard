#!/usr/bin/env python3
"""Offline, fail-closed validation for the obligation ledger."""

import json
import re
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from adapters.obligation_common import (
    aggregate, event_fingerprint, file_sha256, load_partition_provenance,
    load_store, period_info,
)


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def load_baseline(repo, account):
    path = account.get("baseline")
    if not path:
        raise ValueError(f"{account['path']}: missing baseline path")
    baseline = json.loads((repo / path).read_text())
    if baseline.get("schemaVersion") != 2:
        raise ValueError(f"{account['path']}: baseline schema must be v2")
    if baseline.get("federalAccount") != account["federalAccount"]:
        raise ValueError(f"{account['path']}: baseline account mismatch")
    return baseline


def _validate_provenance(store, account, fy, rows):
    errors = []
    value = load_partition_provenance(store, fy)
    prefix = f"{account['path']} FY{fy}"
    if not value:
        return [f"{prefix}: missing partition provenance"]
    if value.get("schemaVersion") != 2:
        errors.append(f"{prefix}: provenance schema must be v2")
    if value.get("accountPath") != account["path"]:
        errors.append(f"{prefix}: provenance account path mismatch")
    if value.get("federalAccount") != account["federalAccount"]:
        errors.append(f"{prefix}: provenance federal account mismatch")
    if value.get("fiscalYear") != fy:
        errors.append(f"{prefix}: provenance fiscal year mismatch")
    normalized = value.get("normalized") or {}
    if normalized.get("recordCount") != len(rows):
        errors.append(f"{prefix}: provenance record count mismatch")
    if normalized.get("eventFingerprint") != event_fingerprint(rows):
        errors.append(f"{prefix}: normalized event fingerprint mismatch")
    if normalized.get("netObligationsCents") != sum(e["amountCents"] for e in rows):
        errors.append(f"{prefix}: provenance net obligations mismatch")
    diff = value.get("diff") or {}
    for key in ("previousRecordCount", "recordCount", "addedCount",
                "removedCount", "changedCount", "netAmountChangeCents",
                "addedIdsSha256", "removedIdsSha256", "changedIdsSha256"):
        if key not in diff:
            errors.append(f"{prefix}: replacement diff is missing {key}")
    for key in ("addedIdsSha256", "removedIdsSha256", "changedIdsSha256"):
        if key in diff and not SHA256_RE.fullmatch(str(diff[key])):
            errors.append(f"{prefix}: replacement diff has invalid {key}")
    replacement = value.get("replacement") or {}
    if "previousEventFingerprint" not in replacement or "previousProvenanceSha256" not in replacement:
        errors.append(f"{prefix}: replacement lineage is incomplete")
    for key in ("previousEventFingerprint", "previousProvenanceSha256"):
        if replacement.get(key) is not None and not SHA256_RE.fullmatch(
                str(replacement[key])):
            errors.append(f"{prefix}: replacement lineage has invalid {key}")
    if diff.get("recordCount") != len(rows):
        errors.append(f"{prefix}: replacement diff record count mismatch")
    if not value.get("baselinePin"):
        errors.append(f"{prefix}: provenance is missing its baseline pin")

    status = value.get("collectionStatus")
    if status == "legacy-migrated":
        if value.get("downloads"):
            errors.append(f"{prefix}: legacy migration must not invent downloads")
        if not value.get("migration", {}).get("note"):
            errors.append(f"{prefix}: legacy migration disclosure is missing")
        try:
            datetime.fromisoformat(value.get("migratedAt", ""))
        except (TypeError, ValueError):
            errors.append(f"{prefix}: invalid migratedAt timestamp")
    elif status == "accepted":
        downloads = value.get("downloads") or []
        if not downloads:
            errors.append(f"{prefix}: accepted provenance has no downloads")
        for index, download in enumerate(downloads):
            label = f"{prefix} download {index + 1}"
            scope = download.get("requestScope") or {}
            filters = scope.get("filters") or {}
            if int(filters.get("fy", -1)) != fy:
                errors.append(f"{label}: request fiscal year mismatch")
            if int(filters.get("period", -1)) not in range(2, 13):
                errors.append(f"{label}: request period is invalid")
            if filters.get("submission_types") != [download.get("submissionType")]:
                errors.append(f"{label}: request submission type mismatch")
            if not str(filters.get("federal_account", "")):
                errors.append(f"{label}: internal federal account scope is missing")
            if not scope.get("columns"):
                errors.append(f"{label}: requested columns are missing")
            accepted_scope = download.get("acceptedRequestScope")
            if accepted_scope:
                accepted_filters = accepted_scope.get("filters") or {}
                if (str(accepted_filters.get("federal_account")) != str(filters.get("federal_account"))
                        or int(accepted_filters.get("fy", -1)) != fy
                        or int(accepted_filters.get("period", -1)) != int(filters.get("period", -1))
                        or accepted_scope.get("download_types") != [download.get("submissionType")]):
                    errors.append(f"{label}: accepted request scope differs from requested scope")
            if str(download.get("status", "")).lower() != "finished":
                errors.append(f"{label}: source status was not finished")
            if download.get("statusRowCount") != download.get("parsedRowCount"):
                errors.append(f"{label}: status and parsed row counts differ")
            if sum((download.get("memberRowCounts") or {}).values()) != download.get("parsedRowCount"):
                errors.append(f"{label}: member row counts do not reconcile")
            if not SHA256_RE.fullmatch(str(download.get("archiveSha256", ""))):
                errors.append(f"{label}: archive SHA-256 is invalid")
            if not str(download.get("rawArtifactFile", "")).endswith(".zip"):
                errors.append(f"{label}: raw artifact filename is missing")
        kinds = [row.get("submissionType") for row in downloads]
        if "award_financial" not in kinds or "object_class_program_activity" not in kinds:
            errors.append(f"{prefix}: accepted provenance is missing File B or File C")
        availability = account.get("availability", {})
        first_fy = int(availability.get("firstFiscalYear", 2017))
        first_period = int(
            availability.get("firstFiscalYearPeriod", 6)
            if fy == first_fy else availability.get("regularFirstPeriod", 2)
        )
        requested_b = sorted(
            int((row.get("requestScope") or {}).get("filters", {}).get("period", -1))
            for row in downloads
            if row.get("submissionType") == "object_class_program_activity"
        )
        if requested_b != list(range(first_period, int(value.get("asOfPeriod", -1)) + 1)):
            errors.append(f"{prefix}: File B request-period sequence is incomplete")
        requested_c = [
            int((row.get("requestScope") or {}).get("filters", {}).get("period", -1))
            for row in downloads if row.get("submissionType") == "award_financial"
        ]
        if requested_c != [value.get("asOfPeriod")]:
            errors.append(f"{prefix}: File C request period is not the accepted endpoint")
        try:
            datetime.fromisoformat(value.get("acceptedAt", ""))
        except (TypeError, ValueError):
            errors.append(f"{prefix}: invalid acceptedAt timestamp")
    else:
        errors.append(f"{prefix}: unsupported collection status {status!r}")
    return errors


def validate(repo=REPO, require_data=True, check_freshness=False,
             as_of=None, require_current_provenance=False):
    repo = Path(repo)
    as_of = as_of or date.today()
    errors = []
    config = json.loads((repo / "config" / "obligation_accounts.json").read_text())
    if config.get("schemaVersion") != 2:
        errors.append("obligation account registry schema must be v2")
    freshness_default = int(config.get("refreshDefaults", {}).get(
        "freshnessMaxDays", 10
    ))
    data_root = repo / "data" / "obligations"
    for path in sorted(data_root.rglob("dashboard.json")) if data_root.exists() else []:
        page = json.loads(path.read_text())
        if page.get("kind") != "obligations" or page.get("schemaVersion") != 2:
            errors.append(f"{path.relative_to(repo)}: obligation dashboard schema mismatch")
        if "fileCCoverage" in json.dumps(page):
            errors.append(f"{path.relative_to(repo)}: legacy fileCCoverage field remains")
        freshness = page.get("freshness") or {}
        if not isinstance(freshness.get("maxAgeDays"), int) or freshness.get("maxAgeDays", 0) <= 0:
            errors.append(f"{path.relative_to(repo)}: freshness SLA metadata is missing")
    index_path = data_root / "index.json"
    if index_path.exists() and json.loads(index_path.read_text()).get("schemaVersion") != 2:
        errors.append("data/obligations/index.json: schema must be v2")
    all_events = []
    agency_events = defaultdict(list)
    for account in config["accounts"]:
        store = repo / "data" / "obligations" / account["path"] / "events"
        events = load_store(store) if store.exists() else []
        try:
            baseline = load_baseline(repo, account)
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
            errors.append(str(error))
            continue
        if not events:
            if require_data:
                errors.append(f"{account['path']}: no obligation events")
            continue
        all_events.extend(events)
        agency_events[account["path"].split("/")[0]].extend(events)
        ids = [e["id"] for e in events]
        if len(ids) != len(set(ids)):
            errors.append(f"{account['path']}: duplicate event IDs")
        known = {(pa["code"], pa["name"])
                 for pa in account["programActivities"]}
        unknown = sorted({(e["programActivityCode"], e["programActivityName"])
                          for e in events} - known)
        if unknown:
            errors.append(f"{account['path']}: unmapped Program Activities {unknown}")
        by_fy = defaultdict(list)
        residual_buckets = defaultdict(int)
        file_c_buckets = set()
        for event in events:
            if event["federalAccount"] != account["federalAccount"]:
                errors.append(f"{event['id']}: federal account mismatch")
            if event["source"] not in {"file_c", "file_b_residual"}:
                errors.append(f"{event['id']}: unsupported source {event['source']!r}")
            if event["grossPositiveCents"] < 0 or event["grossNegativeCents"] > 0 or (
                    event["grossPositiveCents"] + event["grossNegativeCents"] !=
                    event["amountCents"]):
                errors.append(f"{event['id']}: signed gross amounts do not reconcile")
            bucket = (event["submissionPeriod"], event["programActivityCode"])
            if event["source"] == "file_b_residual":
                residual_buckets[bucket] += 1
                if event["linked"] or event["awardId"]:
                    errors.append(f"{event['id']}: residual must not be award-linked")
            else:
                file_c_buckets.add(bucket)
            if (event["source"] == "file_c" and event["linked"] and
                    not event["awardUrl"].startswith(
                        "https://www.usaspending.gov/award/")):
                errors.append(f"{event['id']}: invalid public USAspending award URL")
            fy, period, end = period_info(event["submissionPeriod"])
            if (fy, period, end.isoformat()) != (
                    event["fiscalYear"], event["fiscalPeriod"], event["date"]):
                errors.append(f"{event['id']}: period metadata mismatch")
            by_fy[fy].append(event)
        for fy, rows in sorted(by_fy.items()):
            shard = store / f"FY{fy}.csv.gz"
            if not shard.exists():
                errors.append(f"{account['path']} FY{fy}: missing required shard")
            errors.extend(_validate_provenance(store, account, fy, rows))
        for bucket in sorted(file_c_buckets):
            if residual_buckets[bucket] != 1:
                errors.append(
                    f"{account['path']}: {bucket} has {residual_buckets[bucket]} "
                    "File B residual rows"
                )
        manifest_path = store / "manifest.json"
        manifest = {}
        if not manifest_path.exists():
            errors.append(f"{account['path']}: missing obligation manifest")
        else:
            manifest = json.loads(manifest_path.read_text())
            if manifest.get("schemaVersion") != 2 or manifest.get("format") != "obligation-events-csv-gzip-v2":
                errors.append(f"{account['path']}: manifest schema/format is not v2")
            if manifest.get("recordCount") != len(events):
                errors.append(f"{account['path']}: manifest record count mismatch")
            if manifest.get("fiscalYears") != sorted(by_fy):
                errors.append(f"{account['path']}: manifest fiscal years mismatch")
            if manifest.get("eventFingerprint") != event_fingerprint(events):
                errors.append(f"{account['path']}: manifest fingerprint mismatch")
            if manifest.get("federalAccount") != account["federalAccount"]:
                errors.append(f"{account['path']}: manifest account mismatch")
            partitions = {row.get("fiscalYear"): row
                          for row in manifest.get("partitions", [])}
            if set(partitions) != set(by_fy):
                errors.append(f"{account['path']}: manifest partition set mismatch")
            for fy, rows in by_fy.items():
                row = partitions.get(fy, {})
                if row.get("recordCount") != len(rows):
                    errors.append(f"{account['path']} FY{fy}: manifest partition count mismatch")
                if row.get("eventFingerprint") != event_fingerprint(rows):
                    errors.append(f"{account['path']} FY{fy}: manifest partition fingerprint mismatch")
                shard = store / f"FY{fy}.csv.gz"
                if shard.exists() and row.get("sha256") != file_sha256(shard):
                    errors.append(f"{account['path']} FY{fy}: manifest shard hash mismatch")
                provenance = load_partition_provenance(store, fy) or {}
                if row.get("file") != f"FY{fy}.csv.gz" or row.get("provenance") != f"FY{fy}.provenance.json":
                    errors.append(f"{account['path']} FY{fy}: manifest partition paths mismatch")
                if row.get("collectionStatus") != provenance.get("collectionStatus"):
                    errors.append(f"{account['path']} FY{fy}: manifest provenance status mismatch")
            latest_fy = max(by_fy) if by_fy else None
            latest_provenance = load_partition_provenance(store, latest_fy) if latest_fy else None
            expected_accepted = (
                latest_provenance.get("acceptedAt")
                if latest_provenance and latest_provenance.get("collectionStatus") == "accepted"
                else None
            )
            if manifest.get("latestAcceptedAt") != expected_accepted:
                errors.append(f"{account['path']}: manifest current acceptance timestamp mismatch")
        expected_fys = {
            int(fy): row for fy, row in baseline["fiscalYears"].items()
            if row["status"] in {"complete", "partial"}
        }
        for fy in sorted(set(expected_fys) - set(by_fy)):
            errors.append(f"FY{fy}: required {expected_fys[fy]['status']} snapshot is missing")
        for fy in sorted(expected_fys):
            if not (store / f"FY{fy}.csv.gz").exists():
                errors.append(f"{account['path']} FY{fy}: required shard file is missing")
        for fy, row in baseline["fiscalYears"].items():
            if row["status"] == "unavailable" and int(fy) in by_fy:
                errors.append(f"FY{fy}: events exist for a source-unavailable year")
        for fy, rows in sorted(by_fy.items()):
            pin = baseline["fiscalYears"].get(str(fy))
            if not pin:
                errors.append(f"FY{fy}: missing GTAS baseline")
                continue
            actual = sum(e["amountCents"] for e in rows)
            if pin["status"] == "complete" and actual != pin["obligationsCents"]:
                errors.append(f"FY{fy}: {actual} cents != GTAS {pin['obligationsCents']} cents")
            if pin["status"] == "partial":
                first = min(e["fiscalPeriod"] for e in rows)
                last = max(e["fiscalPeriod"] for e in rows)
                if pin.get("firstPeriod") is not None and pin["firstPeriod"] != first:
                    errors.append(
                        f"FY{fy}: first P{first:02} != pinned P{pin['firstPeriod']:02}"
                    )
                if pin.get("asOfPeriod") != last:
                    errors.append(f"FY{fy}: latest P{last:02} has no same-period GTAS pin")
                elif actual != pin["obligationsCents"]:
                    errors.append(f"FY{fy} P{last:02}: {actual} cents != pinned {pin['obligationsCents']} cents")
        partial_fys = {fy for fy, pin in expected_fys.items() if pin["status"] == "partial"}
        latest_fy = max(expected_fys) if expected_fys else None
        if latest_fy and require_current_provenance:
            provenance = load_partition_provenance(store, latest_fy)
            if not provenance or provenance.get("collectionStatus") != "accepted":
                errors.append(
                    f"{account['path']} FY{latest_fy}: current partition lacks accepted v2 provenance"
                )
        if latest_fy and check_freshness:
            provenance = load_partition_provenance(store, latest_fy)
            if not provenance or provenance.get("collectionStatus") != "accepted":
                errors.append(
                    f"{account['path']} FY{latest_fy}: no accepted source snapshot for freshness SLA"
                )
            else:
                try:
                    accepted = datetime.fromisoformat(provenance["acceptedAt"]).date()
                except (TypeError, KeyError, ValueError):
                    errors.append(f"{account['path']} FY{latest_fy}: freshness timestamp is invalid")
                    accepted = None
            if provenance and provenance.get("collectionStatus") == "accepted" and accepted:
                age = (as_of - accepted).days
                max_days = int(account.get("freshnessMaxDays", freshness_default))
                if age < -1 or age > max_days:
                    errors.append(
                        f"{account['path']} FY{latest_fy}: source snapshot age {age} days "
                        f"is outside the 0–{max_days}-day SLA"
                    )
        covered_periods = {event["submissionPeriod"] for event in events}
        stats = aggregate(events, max(by_fy), covered_periods, partial_fys)
        if stats["netObligationsCents"] != sum(e["amountCents"] for e in events):
            errors.append(f"{account['path']}: aggregate total mismatch")
        for row in stats["fiscalYears"]:
            endpoint = next((s["points"][-1] for s in stats["fyCumulative"]
                             if s["fy"] == row["fy"] and s["points"]), None)
            if endpoint and endpoint["netObligationsCents"] != row["netObligationsCents"]:
                errors.append(f"FY{row['fy']}: cumulative endpoint mismatch")
        dashboard = repo / "data" / "obligations" / account["path"] / "dashboard.json"
        if dashboard.exists():
            page = json.loads(dashboard.read_text())
            if page.get("kind") != "obligations":
                errors.append(f"{account['path']}: dashboard kind mismatch")
            if page.get("schemaVersion") != 2:
                errors.append(f"{account['path']}: dashboard schema must be v2")
            if "fileCCoverage" in json.dumps(page):
                errors.append(f"{account['path']}: legacy fileCCoverage field remains")
            if page.get("warnings") or not page.get("dataComplete"):
                errors.append(f"{account['path']}: dashboard is not warning-free and complete")
            if page.get("totalNetObligationsCents") != stats["totalNetObligationsCents"]:
                errors.append(f"{account['path']}: dashboard total is stale")
            if page.get("currentFY") != stats["currentFY"] or page.get("asOfPeriod") != stats["asOfPeriod"]:
                errors.append(f"{account['path']}: dashboard coverage period is stale")
            if check_freshness:
                dashboard_freshness = page.get("freshness") or {}
                if dashboard_freshness.get("latestAcceptedAt") != manifest.get("latestAcceptedAt"):
                    errors.append(f"{account['path']}: dashboard freshness metadata is stale")
            page_fys = {row["fy"]: row for row in page.get("fiscalYears", [])}
            for row in stats["fiscalYears"]:
                actual = page_fys.get(row["fy"])
                if not actual or (actual.get("netObligationsCents"), actual.get("partial")) != (
                        row["netObligationsCents"], row["partial"]):
                    errors.append(f"FY{row['fy']}: dashboard fiscal-year status is stale")
            if [row.get("submissionPeriod") for row in page.get("reportingPeriods", [])] != [
                    row["submissionPeriod"] for row in stats["reportingPeriods"]]:
                errors.append(f"{account['path']}: dashboard reporting periods are stale")
            children = page.get("children", [])
            if round(sum(c.get("currentFYNetObligations", 0) for c in children) * 100) != next(
                    r["netObligationsCents"] for r in stats["fiscalYears"] if r["fy"] == stats["currentFY"]):
                errors.append(f"{account['path']}: child current-FY dollars do not add to parent")
            for pa in account["programActivities"]:
                child = repo / "data" / "obligations" / account["path"] / pa["slug"] / "dashboard.json"
                if not child.exists():
                    errors.append(f"{account['path']}/{pa['slug']}: missing dashboard.json")
                    continue
                child_page = json.loads(child.read_text())
                child_events = [
                    event for event in events
                    if (event["programActivityCode"], event["programActivityName"])
                    == (pa["code"], pa["name"])
                ]
                child_stats = aggregate(
                    child_events, stats["currentFY"], covered_periods, partial_fys
                )
                if child_page.get("totalNetObligationsCents") != child_stats["totalNetObligationsCents"]:
                    errors.append(f"{account['path']}/{pa['slug']}: dashboard total is stale")
                if child_page.get("asOfPeriod") != stats["asOfPeriod"]:
                    errors.append(f"{account['path']}/{pa['slug']}: coverage period is stale")
                if [row.get("submissionPeriod") for row in child_page.get("reportingPeriods", [])] != [
                        row["submissionPeriod"] for row in stats["reportingPeriods"]]:
                    errors.append(f"{account['path']}/{pa['slug']}: reporting periods are incomplete")
        elif require_data:
            errors.append(f"{account['path']}: missing dashboard.json")
    root_dashboard = data_root / "dashboard.json"
    if all_events and (require_data or root_dashboard.exists()):
        for agency, events in agency_events.items():
            path = data_root / agency / "dashboard.json"
            if not path.exists():
                errors.append(f"obligations/{agency}: missing agency dashboard")
                continue
            page = json.loads(path.read_text())
            if page.get("totalNetObligationsCents") != sum(e["amountCents"] for e in events):
                errors.append(f"obligations/{agency}: agency dashboard total is stale")
        if not root_dashboard.exists():
            errors.append("obligations: missing root dashboard")
        else:
            page = json.loads(root_dashboard.read_text())
            if page.get("totalNetObligationsCents") != sum(e["amountCents"] for e in all_events):
                errors.append("obligations: root dashboard total is stale")
    return errors


def main():
    require = "--allow-empty" not in sys.argv
    check_freshness = "--check-freshness" in sys.argv
    require_current = "--require-current-provenance" in sys.argv
    errors = validate(require_data=require, check_freshness=check_freshness,
                      require_current_provenance=require_current)
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        raise SystemExit(f"obligation validation failed with {len(errors)} error(s)")
    print("Obligation ledger validation passed" + ("" if require else " (empty stores allowed)"))


if __name__ == "__main__":
    main()
