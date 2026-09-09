#!/usr/bin/env python3
"""Pull one File B/File C account into the independent obligation ledger."""

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from adapters.obligation_common import (
    baseline_file_b_cents, baseline_pin_problems, event_fingerprint,
    file_sha256, load_store, partition_diff, write_store,
)
from adapters.usaspending_obligations import (
    alias_map, archive_rows, combine_file_b_file_c, file_b_period_events,
    finish_download, parse_file_b_snapshot, parse_file_c, request_download,
    resolve_account, resume_download,
)
from scripts.rollup_obligations import build


FILE_B_COLUMNS = [
    "submission_period", "federal_account_symbol", "program_activity_reporting_key",
    "program_activity_code", "program_activity_name", "obligations_incurred",
]
FILE_C_COLUMNS = [
    "submission_period", "federal_account_symbol", "program_activity_reporting_key",
    "program_activity_code", "program_activity_name", "transaction_obligated_amount",
    "award_unique_key", "award_id_piid", "parent_award_id_piid", "award_id_fain",
    "award_id_uri", "recipient_uei", "recipient_name",
    "prime_award_base_transaction_description", "usaspending_permalink",
]


def _resume_request(repo, account, account_id, fy, period, kind, columns):
    path = Path(repo) / "reference" / "obligation_download_resumes.json"
    if not path.exists():
        return None
    document = json.loads(path.read_text())
    if document.get("schemaVersion") != 1:
        raise ValueError("obligation download resume manifest must be schema v1")
    requests = document.get("requests")
    if not isinstance(requests, list):
        raise ValueError("obligation download resume manifest requests must be a list")
    matches = [row for row in requests if (
        row.get("account") == account["path"]
        and row.get("fiscalYear") == fy
        and row.get("period") == period
        and row.get("submissionType") == kind
    )]
    if len(matches) > 1:
        raise ValueError(
            f"duplicate obligation download resumes for {account['path']} "
            f"FY{fy} P{period:02} {kind}"
        )
    if not matches:
        return None
    result = matches[0].get("result")
    if not isinstance(result, dict):
        raise ValueError("obligation download resume result must be an object")
    return resume_download(
        account_id, fy, period, kind, columns, result
    )


def _resume_handoff_path(raw_archive_dir, account, fy, period, kind):
    if not raw_archive_dir:
        return None
    return Path(raw_archive_dir) / (
        f"obligation-download-resume-{account['path'].replace('/', '--')}-"
        f"FY{fy}P{period:02}-{kind}.json"
    )


def _write_resume_handoff(path, account, fy, period, kind, request):
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    value = {
        "schemaVersion": 1,
        "requests": [{
            "account": account["path"],
            "fiscalYear": fy,
            "period": period,
            "submissionType": kind,
            "result": request,
        }],
    }
    path.write_text(json.dumps(value, indent=1, sort_keys=True) + "\n")


def _download(repo, account, account_id, fy, period, kind, columns,
              raw_archive_dir=None):
    print(f"requesting FY{fy} P{period:02} {kind}", flush=True)
    resumed = _resume_request(
        repo, account, account_id, fy, period, kind, columns
    )
    if resumed:
        print(f"resuming accepted FY{fy} P{period:02} {kind}", flush=True)
        request, request_scope = resumed
    else:
        request, request_scope = request_download(
            account_id, fy, period, kind, columns
        )
    handoff_path = _resume_handoff_path(
        raw_archive_dir, account, fy, period, kind
    )
    _write_resume_handoff(
        handoff_path, account, fy, period, kind, request
    )
    try:
        payload, status = finish_download(request)
    except ValueError:
        # A source-declared terminal failure cannot be resumed.  Preserve
        # handoffs only for timeouts or transient transport interruptions.
        if handoff_path is not None:
            handoff_path.unlink(missing_ok=True)
        raise
    archive_sha = hashlib.sha256(payload).hexdigest()
    archive_name = (
        f"{account['path'].replace('/', '--')}-FY{fy}P{period:02}-"
        f"{kind}-{archive_sha[:12]}.zip"
    )
    if raw_archive_dir:
        raw_path = Path(raw_archive_dir) / archive_name
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(payload)
    if handoff_path is not None:
        handoff_path.unlink(missing_ok=True)
    members = archive_rows(payload)
    expected = status.get("total_rows")
    parsed = sum(len(rows) for rows in members.values())
    if expected is None:
        raise ValueError(f"FY{fy} P{period:02} {kind}: source status omitted total_rows")
    if parsed != int(expected):
        raise ValueError(f"FY{fy} P{period:02} {kind}: parsed {parsed} rows, status says {expected}")
    audit = {
        "submissionType": kind,
        "requestScope": request_scope,
        "acceptedRequestScope": request.get("download_request") or None,
        "status": str(status.get("status", "")).lower(),
        "statusRowCount": int(expected),
        "parsedRowCount": parsed,
        "memberRowCounts": {name: len(rows) for name, rows in sorted(members.items())},
        "archiveSha256": archive_sha,
        "rawArtifactFile": archive_name,
    }
    print(f"accepted FY{fy} P{period:02} {kind}: {parsed:,} rows", flush=True)
    return members, audit


def _baseline_pin(repo, account, fy, last_period, file_b_total,
                  first_event_period=None):
    baseline = json.loads((repo / account["baseline"]).read_text())
    if baseline.get("schemaVersion") != 2:
        raise ValueError(f"{account['path']}: baseline schema must be v2")
    if baseline.get("federalAccount") != account["federalAccount"]:
        raise ValueError(f"{account['path']}: baseline account mismatch")
    existing = baseline.get("fiscalYears", {}).get(str(fy))
    if existing and existing.get("status") == "unavailable":
        raise ValueError(f"FY{fy} is marked source-unavailable")
    if existing and "fileBObligationsCents" in existing:
        problems = baseline_pin_problems(existing)
        if problems:
            raise ValueError(f"FY{fy}: invalid baseline pin: {'; '.join(problems)}")
        if existing.get("status") in {"complete", "available"} and last_period != 12:
            raise ValueError(f"FY{fy} is complete and must be reconciled through P12")
        if (existing.get("status") == "partial"
                and last_period != existing.get("asOfPeriod")):
            raise ValueError(
                f"FY{fy}: dual File A/File B pin is as-of "
                f"P{int(existing.get('asOfPeriod', -1)):02}"
            )
        expected_file_b = baseline_file_b_cents(existing)
        if file_b_total != expected_file_b:
            raise ValueError(
                f"FY{fy}: File B {file_b_total} cents != pinned "
                f"File B {expected_file_b}"
            )
        return dict(existing)
    if existing and existing.get("status") in {"complete", "available"}:
        if last_period != 12:
            raise ValueError(f"FY{fy} is complete and must be reconciled through P12")
        problems = baseline_pin_problems(existing)
        if problems:
            raise ValueError(f"FY{fy}: invalid baseline pin: {'; '.join(problems)}")
        expected_file_b = baseline_file_b_cents(existing)
        if file_b_total != expected_file_b:
            raise ValueError(
                f"FY{fy}: File B {file_b_total} cents != pinned "
                f"File B {expected_file_b}"
            )
        return dict(existing)
    pin = dict(existing or {})
    first_fy = int(account.get("availability", {}).get("firstFiscalYear", 2017))
    if last_period == 12 and fy != first_fy:
        pin = {"status": "complete", "obligationsCents": file_b_total}
    else:
        pin.update({"status": "partial", "asOfPeriod": last_period,
                    "obligationsCents": file_b_total})
    if fy == first_fy:
        # Availability identifies the first official request period.  A new
        # account can publish finished, empty snapshots before its first
        # material File B activity (OCED FY2022 is P02/P03 empty, P04 first
        # material).  Pin the event boundary, not merely the request boundary.
        pin["firstPeriod"] = int(first_event_period or
            account.get("availability", {}).get("firstFiscalYearPeriod", 6))
    return pin


def _validate_account_total(fy, last_period, detail_total, file_b_total,
                            baseline_pin):
    if last_period != 12 or not detail_total:
        return
    expected_file_b = baseline_file_b_cents(baseline_pin)
    if file_b_total != expected_file_b:
        raise ValueError(
            f"FY{fy}: File B {file_b_total} cents != pinned File B "
            f"{expected_file_b}"
        )
    file_a_total = baseline_pin.get("obligationsCents")
    if detail_total == file_a_total:
        return
    if ("fileBObligationsCents" in baseline_pin
            and detail_total == expected_file_b):
        return
    if "fileBObligationsCents" in baseline_pin:
        raise ValueError(
            f"FY{fy}: account snapshot {detail_total} cents != pinned File A "
            f"{file_a_total} or pinned File B {expected_file_b}"
        )
    else:
        raise ValueError(
            f"FY{fy}: account snapshot {detail_total} cents != pinned File A "
            f"{file_a_total}"
        )


def _provenance(account, fy, last_period, events, previous, previous_provenance_sha,
                downloads, baseline_pin):
    return {
        "schemaVersion": 2,
        "collectionStatus": "accepted",
        "acceptedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "accountPath": account["path"],
        "federalAccount": account["federalAccount"],
        "fiscalYear": fy,
        "asOfPeriod": last_period,
        "downloads": downloads,
        "normalized": {
            "recordCount": len(events),
            "eventFingerprint": event_fingerprint(events),
            "netObligationsCents": sum(e["amountCents"] for e in events),
        },
        "replacement": {
            "previousEventFingerprint": event_fingerprint(previous),
            "previousProvenanceSha256": previous_provenance_sha,
        },
        "diff": partition_diff(previous, events),
        "baselinePin": baseline_pin,
    }


def _export_partitions(repo, account, years, destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    store = repo / "data" / "obligations" / account["path"] / "events"
    files = []
    for fy in years:
        for suffix in (".csv.gz", ".provenance.json"):
            source = store / f"FY{fy}{suffix}"
            target = destination / source.name
            shutil.copy2(source, target)
            files.append({"name": target.name, "sha256": file_sha256(target)})
    value = {"schemaVersion": 2, "accountPath": account["path"],
             "federalAccount": account["federalAccount"],
             "baselinePath": account["baseline"], "fiscalYears": list(years),
             "files": files}
    (destination / "partition.json").write_text(
        json.dumps(value, indent=1, sort_keys=True) + "\n"
    )


def _export_skipped_partition(account, years, destination):
    """Emit an auditable no-op artifact for a frozen matrix job.

    A workflow matrix is fixed when its plan job starts. If later evidence
    corrects one of its queued account-years to source-unavailable, that job
    must finish without inventing a zero-dollar financial observation.
    Reconciliation ignores descriptors whose fiscalYears list is empty.
    """
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    value = {
        "schemaVersion": 2,
        "accountPath": account["path"],
        "federalAccount": account["federalAccount"],
        "baselinePath": account["baseline"],
        "fiscalYears": [],
        "files": [],
        "skippedFiscalYears": list(years),
        "skipReason": "registry baseline marks the fiscal year source-unavailable",
    }
    (destination / "partition.json").write_text(
        json.dumps(value, indent=1, sort_keys=True) + "\n"
    )


def pull(account, years, current_period=12, repo=REPO, rollup=True,
         raw_archive_dir=None, partition_output=None):
    repo = Path(repo)
    years = list(years)
    baseline = json.loads((repo / account["baseline"]).read_text())
    for fy, pin in (baseline.get("fiscalYears") or {}).items():
        problems = baseline_pin_problems(pin)
        if problems:
            raise ValueError(
                f"{account['path']} FY{fy}: invalid baseline pin: "
                + "; ".join(problems)
            )
    unavailable_years = [
        fy for fy in years
        if baseline.get("fiscalYears", {}).get(str(fy), {}).get("status")
        == "unavailable"
    ]
    if unavailable_years:
        if len(unavailable_years) != len(years):
            raise ValueError(
                "a pull range cannot mix source-available and unavailable years"
            )
        if partition_output:
            _export_skipped_partition(account, unavailable_years, partition_output)
            print(
                "skipping " + ", ".join(f"FY{fy}" for fy in unavailable_years)
                + ": registry baseline marks source-unavailable",
                flush=True,
            )
            return
        raise ValueError(
            ", ".join(f"FY{fy}" for fy in unavailable_years)
            + " is marked source-unavailable"
        )
    aliases = alias_map(account)
    all_events = []
    audit = {}
    partition_metadata = {}
    store = repo / "data" / "obligations" / account["path"] / "events"
    existing = load_store(store) if store.exists() else []
    for fy in years:
        last_period = current_period if fy == max(years) else 12
        account_id, detail = resolve_account(account["federalAccount"], fy)
        snapshots = {}
        downloads = []
        availability = account.get("availability", {})
        first_fy = int(availability.get("firstFiscalYear", 2017))
        first_period = int(
            availability.get("firstFiscalYearPeriod", 6)
            if fy == first_fy else availability.get("regularFirstPeriod", 2)
        )
        for period in range(first_period, last_period + 1):
            members, download = _download(
                repo, account, account_id, fy, period,
                "object_class_program_activity",
                FILE_B_COLUMNS, raw_archive_dir,
            )
            downloads.append(download)
            rows = [row for part in members.values() for row in part]
            snapshots[f"FY{fy}P{period:02}"] = parse_file_b_snapshot(
                rows, account["federalAccount"], aliases)
        file_b = file_b_period_events(snapshots, account["federalAccount"])
        c_members, download = _download(
            repo, account, account_id, fy, last_period, "award_financial",
            FILE_C_COLUMNS, raw_archive_dir,
        )
        downloads.append(download)
        file_c = parse_file_c(c_members, account["federalAccount"], aliases)
        events = combine_file_b_file_c(file_b, file_c, account["federalAccount"])
        file_b_total = sum(e["amountCents"] for e in file_b)
        from adapters.obligation_common import cents
        detail_total = cents(detail.get("total_obligated_amount") or 0)
        all_events.extend(events)
        first_event_period = min(
            (event["fiscalPeriod"] for event in events), default=None
        )
        baseline_pin = _baseline_pin(
            repo, account, fy, last_period, file_b_total, first_event_period
        )
        _validate_account_total(
            fy, last_period, detail_total, file_b_total, baseline_pin
        )
        previous = [e for e in existing if e["fiscalYear"] == fy]
        previous_provenance = store / f"FY{fy}.provenance.json"
        partition_metadata[fy] = _provenance(
            account, fy, last_period, events, previous,
            file_sha256(previous_provenance) if previous_provenance.exists() else None,
            downloads, baseline_pin,
        )
        audit[str(fy)] = {"asOfPeriod": last_period, "eventCount": len(events),
                          "fileBObligationsCents": file_b_total,
                          "fileCObligationsCents": sum(e["amountCents"] for e in file_c)}
    retained = [e for e in existing if e["fiscalYear"] not in set(years)]
    write_store(store, retained + all_events,
                {"federalAccount": account["federalAccount"], "pulls": audit},
                partition_metadata=partition_metadata)
    if partition_output:
        _export_partitions(repo, account, years, partition_output)
    if rollup:
        build(repo)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", default="doe/sc")
    parser.add_argument("--from-fy", type=int, default=2017)
    parser.add_argument("--to-fy", type=int, required=True)
    parser.add_argument("--current-period", type=int, default=12)
    parser.add_argument("--no-rollup", action="store_true")
    parser.add_argument("--raw-archive-dir")
    parser.add_argument("--partition-output")
    args = parser.parse_args()
    config = json.loads((REPO / "config" / "obligation_accounts.json").read_text())
    account = next((a for a in config["accounts"] if a["path"] == args.account), None)
    if not account:
        raise SystemExit(f"unknown obligation account {args.account}")
    pull(account, range(args.from_fy, args.to_fy + 1), args.current_period,
         rollup=not args.no_rollup, raw_archive_dir=args.raw_archive_dir,
         partition_output=args.partition_output)


if __name__ == "__main__":
    main()
