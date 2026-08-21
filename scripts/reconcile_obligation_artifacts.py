#!/usr/bin/env python3
"""Atomically stage accepted account-year artifacts into the ledger snapshot."""

import argparse
import json
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


def reconcile(staging, repo=REPO):
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
            first_fy = int(
                account.get("availability", {}).get("firstFiscalYear", 2017)
            )
            if int(fy) == first_fy:
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
            current_pin = baselines[account["path"]]["fiscalYears"].get(str(fy))
            preserved = _preserve_current_dual_pin(
                account["path"], int(fy), current_pin, pin,
                provenance.get("normalized", {}).get("netObligationsCents"),
            )
            if preserved != pin:
                pin = preserved
                provenance = dict(provenance)
                provenance["baselinePin"] = pin
            planned.append((account, int(fy), descriptor_path.parent, provenance))
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
    return len(planned), sorted(touched)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--staging", required=True)
    args = parser.parse_args()
    count, accounts = reconcile(args.staging)
    print(f"Reconciled {count} account-year partitions across {len(accounts)} accounts")


if __name__ == "__main__":
    main()
