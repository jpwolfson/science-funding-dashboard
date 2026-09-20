#!/usr/bin/env python3
"""Atomically stage accepted account-year artifacts into the ledger snapshot."""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from adapters.obligation_common import (
    baseline_file_b_cents, baseline_pin_problems, file_sha256, load_store,
    rebuild_manifest, write_partition_provenance,
)
from adapters.funding_sentinel import build as build_sentinel
from scripts.rollup_obligations import build as build_obligations

# Written by update-obligations.yml's "Detect account-years missing from
# this run's partitions" step: the planned account-years (or the plan's
# full "include" matrix) that this run's serial pull matrix did not upload
# a partition for. Read by default so a plain
# `reconcile_obligation_artifacts.py --staging _partitions` invocation from
# the workflow still enforces the current-FY guarantee without an explicit
# --plan flag; tests and ad hoc invocations pass --plan (or the `plan`
# keyword argument) explicitly instead.
DEFAULT_MISSING_PARTITIONS_PATH = Path("_missing_partitions.json")

# Fiscal years pulled to satisfy the account's mandatory current-FY refresh.
# A missing partition with this purpose fails the reconcile outright, per
# the atomic all-or-nothing contract in docs/obligation-ledger.md, "Refresh,
# freshness, and publication". Every other purpose
# (rotating-historical/historical/custom -- a rotation re-pull of a fiscal
# year the store already has a committed partition for) loses no data when
# its re-pull fails, so a missing partition there is skipped and retried by
# the rotation instead of blocking the whole weekly pass.
MANDATORY_PURPOSE = "current"


def _load_plan_jobs(path):
    """Load the planned account-year jobs to check for missing partitions.

    ``path`` may point either at a full plan matrix (the JSON
    ``{"include": [...]}`` object ``scripts/plan_obligation_refresh.py``
    emits) or at an already-filtered list of missing jobs (the shape
    ``update-obligations.yml`` writes to ``_missing_partitions.json``).
    Both shapes carry the same per-job fields (``account``, ``fiscalYear``,
    ``purpose``, ...), so callers never need to know which one they have.
    """
    if path:
        data = json.loads(Path(path).read_text())
    elif DEFAULT_MISSING_PARTITIONS_PATH.exists():
        data = json.loads(DEFAULT_MISSING_PARTITIONS_PATH.read_text())
    else:
        return []
    return data.get("include", []) if isinstance(data, dict) else list(data)


def _resolve_missing(plan_jobs, seen):
    """Planned account-years with no partition among the reconciled set."""
    return [
        job for job in plan_jobs
        if (job["account"], int(job["fiscalYear"])) not in seen
    ]


def _apply_missing_partition_tolerance(missing):
    """Fail closed on a missing current-FY partition; skip the rest.

    Returns the list of tolerated skips (for the job summary). Raises
    ``ValueError`` immediately on the first missing mandatory (current-FY)
    account-year -- the atomic reconcile cannot proceed without it.
    """
    skipped = []
    for job in missing:
        account, fy = job["account"], int(job["fiscalYear"])
        purpose = job.get("purpose", MANDATORY_PURPOSE)
        if purpose == MANDATORY_PURPOSE:
            raise ValueError(
                f"{account} FY{fy}: current-FY pull produced no partition; "
                "the atomic reconcile cannot proceed without it "
                "(docs/obligation-ledger.md, \"Refresh, freshness, and "
                "publication\")"
            )
        print(
            f"SKIPPED (pull failed): {account} FY{fy}, committed partition "
            "retained"
        )
        skipped.append({"account": account, "fiscalYear": fy, "purpose": purpose})
    return skipped


def _write_job_summary(skipped):
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    with open(summary_path, "a", encoding="utf-8") as handle:
        handle.write("## Obligation reconcile: tolerated pull failures\n\n")
        if not skipped:
            handle.write("All planned account-years produced a partition.\n\n")
            return
        handle.write(
            "The committed partition for each account-year below is "
            "retained unchanged; the weekly rotation will retry it.\n\n"
        )
        handle.write("| Account | Fiscal year | Purpose |\n")
        handle.write("|---|---|---|\n")
        for job in skipped:
            handle.write(
                f"| {job['account']} | FY{job['fiscalYear']} | {job['purpose']} |\n"
            )
        handle.write("\n")


def _reject_zero_collapse_pin(account_path, fy, current_pin, pin):
    """Defense in depth for the not-reported acceptance rule at the pin grain.

    ``scripts/pull_obligation_account.py`` already refuses to advance a
    partial pin's ``asOfPeriod``/``obligationsCents`` onto a notReported
    period (see docs/obligation-ledger.md "Snapshot acceptance and
    not-reported periods"; the ed/ies FY2026 P10 empty-pin regression is
    the motivating case). This is the reconcile-stage backstop: even a
    provenance file produced by an older pull binary, or a hand-assembled
    artifact, may never publish a File A/File B pin of exactly zero cents
    over a previously accepted positive pin in the same fiscal year.
    """
    if not current_pin:
        return
    try:
        previous_amount = baseline_file_b_cents(current_pin)
    except (KeyError, TypeError):
        previous_amount = current_pin.get("obligationsCents")
    try:
        new_amount = baseline_file_b_cents(pin)
    except (KeyError, TypeError):
        new_amount = pin.get("obligationsCents")
    if previous_amount and new_amount == 0:
        raise ValueError(
            f"{account_path} FY{fy}: refusing to advance the baseline pin "
            f"to a zero-cent snapshot after a previously accepted "
            f"{previous_amount} cents (not-reported acceptance rule)"
        )


def _preserve_current_dual_pin(account_path, fy, current, artifact, normalized_total):
    """Keep a newer approved dual pin when the accepted shard matches exactly."""
    if not current or "fileBObligationsCents" not in current:
        return artifact
    problems = baseline_pin_problems(current)
    if problems:
        raise ValueError(
            f"{account_path} FY{fy}: invalid current dual pin: {'; '.join(problems)}"
        )
    problems = baseline_pin_problems(artifact)
    if problems:
        raise ValueError(
            f"{account_path} FY{fy}: invalid artifact baseline pin: "
            f"{'; '.join(problems)}"
        )
    current_file_b = baseline_file_b_cents(current)
    artifact_file_b = baseline_file_b_cents(artifact)
    if artifact_file_b != current_file_b or normalized_total != current_file_b:
        raise ValueError(
            f"{account_path} FY{fy}: current dual-pin File B {current_file_b} "
            f"cents does not match artifact pin {artifact_file_b} and normalized "
            f"total {normalized_total}"
        )
    for field in ("status", "asOfPeriod", "firstPeriod"):
        if current.get(field) != artifact.get(field):
            raise ValueError(
                f"{account_path} FY{fy}: current dual-pin {field} "
                f"{current.get(field)!r} does not match artifact "
                f"{artifact.get(field)!r}"
            )
    return dict(current)


def _preserve_current_complete_pin(account_path, fy, current, artifact,
                                   normalized_total, as_of_period):
    """Keep an established complete pin only after exact P12 agreement."""
    if not current or current.get("status") not in {"complete", "available"}:
        return artifact
    if "fileBObligationsCents" in current:
        artifact = _preserve_current_dual_pin(
            account_path, fy, current, artifact, normalized_total,
        )
    current_problems = baseline_pin_problems(current)
    artifact_problems = baseline_pin_problems(artifact)
    if current_problems or artifact_problems:
        problems = current_problems or artifact_problems
        raise ValueError(
            f"{account_path} FY{fy}: invalid complete baseline pin: "
            f"{'; '.join(problems)}"
        )
    current_file_b = baseline_file_b_cents(current)
    artifact_file_b = baseline_file_b_cents(artifact)
    if (artifact.get("status") not in {"complete", "available"}
            or int(as_of_period) != 12
            or artifact_file_b != current_file_b
            or normalized_total != current_file_b
            or artifact != current):
        raise ValueError(
            f"{account_path} FY{fy}: established complete pin does not match "
            "the accepted P12 artifact and normalized total"
        )
    return dict(current)


def reconcile(staging, repo=REPO, plan=None):
    repo, staging = Path(repo), Path(staging)
    config = json.loads((repo / "config" / "obligation_accounts.json").read_text())
    accounts = {row["path"]: row for row in config["accounts"]}
    baselines = {
        path: json.loads((repo / account["baseline"]).read_text())
        for path, account in accounts.items()
    }
    planned = []
    seen = set()
    for descriptor_path in sorted(staging.rglob("partition.json")):
        descriptor = json.loads(descriptor_path.read_text())
        if descriptor.get("schemaVersion") != 2:
            raise ValueError(f"{descriptor_path}: artifact descriptor schema must be v2")
        account = accounts.get(descriptor.get("accountPath"))
        if not account:
            raise ValueError(f"unregistered artifact account: {descriptor.get('accountPath')}")
        if descriptor.get("federalAccount") != account["federalAccount"]:
            raise ValueError(f"{account['path']}: artifact account mismatch")
        if descriptor.get("baselinePath") != account["baseline"]:
            raise ValueError(f"{account['path']}: artifact baseline mismatch")
        files = {row["name"]: row for row in descriptor.get("files", [])}
        for fy in descriptor.get("fiscalYears", []):
            key = (account["path"], int(fy))
            if key in seen:
                raise ValueError(f"duplicate account-year artifact: {key}")
            seen.add(key)
            required = [f"FY{fy}.csv.gz", f"FY{fy}.provenance.json"]
            for name in required:
                source = descriptor_path.parent / name
                if not source.exists() or name not in files:
                    raise ValueError(f"{key}: missing artifact file {name}")
                if file_sha256(source) != files[name].get("sha256"):
                    raise ValueError(f"{key}: artifact hash mismatch for {name}")
            provenance = json.loads(
                (descriptor_path.parent / required[1]).read_text()
            )
            if (provenance.get("collectionStatus") != "accepted"
                    or provenance.get("accountPath") != account["path"]
                    or provenance.get("fiscalYear") != int(fy)):
                raise ValueError(f"{key}: invalid accepted provenance")
            pin = dict(provenance.get("baselinePin") or {})
            current_pin = baselines[account["path"]]["fiscalYears"].get(str(fy))
            _reject_zero_collapse_pin(account["path"], int(fy), current_pin, pin)
            pin = _preserve_current_complete_pin(
                account["path"], int(fy), current_pin, pin,
                provenance.get("normalized", {}).get("netObligationsCents"),
                provenance.get("asOfPeriod"),
            )
            first_fy = int(
                account.get("availability", {}).get("firstFiscalYear", 2017)
            )
            if (int(fy) == first_fy
                    and not (current_pin and current_pin.get("status")
                             in {"complete", "available"})):
                # Older partitions derived firstPeriod from the request
                # boundary, or classified the year before a branch repair
                # established that it was the account's first source year.
                # Reapply the current registry's partial-year contract and
                # recompute the material boundary from the already
                # hash-verified normalized shard.
                pin["status"] = "partial"
                pin["asOfPeriod"] = int(provenance["asOfPeriod"])
                material_periods = [
                    event["fiscalPeriod"] for event in load_store(
                        descriptor_path.parent
                    ) if event["fiscalYear"] == int(fy)
                ]
                pin["firstPeriod"] = min(material_periods) if material_periods else int(
                    account.get("availability", {}).get(
                        "firstFiscalYearPeriod", 6
                    )
                )
                provenance = dict(provenance)
                provenance["baselinePin"] = pin
            preserved = _preserve_current_dual_pin(
                account["path"], int(fy), current_pin, pin,
                provenance.get("normalized", {}).get("netObligationsCents"),
            )
            if preserved != pin:
                pin = preserved
                provenance = dict(provenance)
                provenance["baselinePin"] = pin
            planned.append((account, int(fy), descriptor_path.parent, provenance))

    # A planned account-year with no partition in staging means its pull job
    # failed (or never uploaded). A missing current-FY partition fails the
    # reconcile outright -- the atomic all-or-nothing contract is load-
    # bearing there. A missing rotating-historical/historical/custom
    # partition loses no data (the committed partition is untouched) and is
    # tolerated: skipped here and retried by the next rotation.
    missing = _resolve_missing(plan or [], seen)
    skipped = _apply_missing_partition_tolerance(missing)

    if not planned:
        raise ValueError("no obligation account-year artifacts found")

    # The workflow workspace is disposable.  Validate every artifact before
    # applying any replacement, then publish only after the global validator
    # and rendered-page matrix both pass.
    touched = set()
    baseline_updates = {}
    for account, fy, source_dir, provenance in planned:
        store = repo / "data" / "obligations" / account["path"] / "events"
        store.mkdir(parents=True, exist_ok=True)
        for suffix in (".csv.gz", ".provenance.json"):
            shutil.copy2(source_dir / f"FY{fy}{suffix}", store / f"FY{fy}{suffix}")
        # The accepted source/download audit remains byte-semantic; only the
        # derived baseline pin above may be corrected for leading empty
        # snapshots before the candidate manifest is rebuilt.
        write_partition_provenance(store, fy, provenance)
        touched.add(account["path"])
        baseline_updates.setdefault(account["path"], {})[str(fy)] = provenance["baselinePin"]

    for account_path, updates in baseline_updates.items():
        account = accounts[account_path]
        baseline_path = repo / account["baseline"]
        baseline = json.loads(baseline_path.read_text())
        for fy, pin in updates.items():
            existing = baseline["fiscalYears"].get(fy)
            if existing and existing.get("status") == "complete":
                if pin != existing:
                    raise ValueError(f"{account_path} FY{fy}: complete baseline changed")
            else:
                baseline["fiscalYears"][fy] = pin
        baseline_path.write_text(json.dumps(baseline, indent=1) + "\n")

    for account in accounts.values():
        store = repo / "data" / "obligations" / account["path"] / "events"
        if store.exists():
            rebuild_manifest(store, metadata={
                "federalAccount": account["federalAccount"],
                "baseline": account["baseline"],
            })
    build_obligations(repo)
    # The sentinel's financial-coverage disclosure is registry-derived and
    # its observations are downstream of the exact File C candidate above.
    # Rebuild it inside the same disposable candidate tree so verification
    # and publication can never see a newly live account with stale coverage.
    build_sentinel(repo)
    return len(planned), sorted(touched), skipped


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--staging", required=True)
    parser.add_argument(
        "--plan",
        help="Path to the planned account x fiscal-year matrix JSON "
             "(plan_obligation_refresh.py's {\"include\": [...]} output) or "
             "an already-filtered missing-jobs list. Defaults to "
             f"{DEFAULT_MISSING_PARTITIONS_PATH} if present.",
    )
    args = parser.parse_args()
    plan_jobs = _load_plan_jobs(args.plan)
    count, accounts, skipped = reconcile(args.staging, plan=plan_jobs)
    print(f"Reconciled {count} account-year partitions across {len(accounts)} accounts")
    _write_job_summary(skipped)


if __name__ == "__main__":
    main()
