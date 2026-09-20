import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from adapters.obligation_common import (
    event_fingerprint, file_sha256, normalize_event, partition_diff, write_store,
)
from scripts.reconcile_obligation_artifacts import (
    _preserve_current_complete_pin, _preserve_current_dual_pin,
    _reject_zero_collapse_pin, reconcile,
)
from scripts.validate_funding_sentinel import validate as validate_sentinel
from scripts.validate_obligations import validate


class ObligationReconcileTests(unittest.TestCase):
    def test_reject_zero_collapse_pin_defense_in_depth(self):
        # Defense in depth for the same ed/ies FY2026 P10 regression that
        # scripts/pull_obligation_account.py's _baseline_pin now refuses at
        # the source: even if a provenance artifact somehow still carries a
        # zero-cent pin after a previously positive one, reconcile must
        # refuse to publish it.
        current_pin = {"status": "partial", "asOfPeriod": 9,
                       "obligationsCents": 500}
        zero_pin = {"status": "partial", "asOfPeriod": 10,
                   "obligationsCents": 0}
        with self.assertRaisesRegex(ValueError, "refusing to advance"):
            _reject_zero_collapse_pin("ed/ies", 2026, current_pin, zero_pin)
        # A genuinely fresh account (no current pin yet) is unaffected.
        _reject_zero_collapse_pin("ed/ies", 2026, None, zero_pin)
        # A non-zero advance is unaffected.
        _reject_zero_collapse_pin(
            "ed/ies", 2026, current_pin,
            {"status": "partial", "asOfPeriod": 10, "obligationsCents": 600},
        )

    def test_established_complete_pin_fails_closed_on_artifact_mismatch(self):
        current = {"status": "complete", "obligationsCents": 100}
        for artifact, normalized_total, as_of_period in (
            ({"status": "complete", "obligationsCents": 99}, 99, 12),
            ({"status": "complete", "obligationsCents": 100}, 99, 12),
            ({"status": "partial", "asOfPeriod": 12,
              "obligationsCents": 100}, 100, 12),
            ({"status": "complete", "obligationsCents": 100}, 100, 11),
        ):
            with self.subTest(artifact=artifact,
                              normalized_total=normalized_total,
                              as_of_period=as_of_period):
                with self.assertRaisesRegex(ValueError, "does not match"):
                    _preserve_current_complete_pin(
                        "dod/space-force-rdte", 2021, current, artifact,
                        normalized_total, as_of_period,
                    )

    def test_first_fiscal_year_preserves_matching_complete_pin(self):
        temp = tempfile.TemporaryDirectory()
        try:
            root = Path(temp.name) / "repo"
            staging = Path(temp.name) / "staging" / "artifact"
            producer = Path(temp.name) / "producer"
            for path in (root / "config", root / "reference", staging, producer):
                path.mkdir(parents=True, exist_ok=True)
            (root / "config" / "obligation_accounts.json").write_text(json.dumps({
                "schemaVersion": 2,
                "accounts": [{
                    "path": "dod/space-force-rdte", "name": "Space Force",
                    "abbrev": "USSF", "agency": "Defense",
                    "federalAccount": "057-3620", "baseline": "reference/dod.json",
                    "availability": {"firstFiscalYear": 2021,
                                     "firstFiscalYearPeriod": 2,
                                     "regularFirstPeriod": 2},
                    "programActivities": [{"slug": "rdte", "code": "0001",
                                           "name": "RDT&E"}],
                }],
            }))
            complete_pin = {"status": "complete", "obligationsCents": 100}
            (root / "reference" / "dod.json").write_text(json.dumps({
                "schemaVersion": 2, "federalAccount": "057-3620",
                "fiscalYears": {"2021": complete_pin},
            }))
            row = normalize_event({
                "id": "one", "source": "file_b_residual",
                "submissionPeriod": "FY2021P12", "federalAccount": "057-3620",
                "programActivityCode": "0001", "programActivityName": "RDT&E",
                "amountCents": 100, "awardId": "", "linked": False,
            })
            provenance = {
                "schemaVersion": 2, "collectionStatus": "accepted",
                "acceptedAt": "2026-08-11T12:00:00+00:00",
                "accountPath": "dod/space-force-rdte",
                "federalAccount": "057-3620", "fiscalYear": 2021,
                "asOfPeriod": 12, "downloads": [],
                "normalized": {"recordCount": 1,
                               "eventFingerprint": event_fingerprint([row]),
                               "netObligationsCents": 100},
                "replacement": {}, "diff": partition_diff([], [row]),
                "baselinePin": complete_pin,
            }
            write_store(producer, [row], {"federalAccount": "057-3620"},
                        partition_metadata={2021: provenance})
            names = ["FY2021.csv.gz", "FY2021.provenance.json"]
            for name in names:
                shutil.copy2(producer / name, staging / name)
            (staging / "partition.json").write_text(json.dumps({
                "schemaVersion": 2, "accountPath": "dod/space-force-rdte",
                "federalAccount": "057-3620", "baselinePath": "reference/dod.json",
                "fiscalYears": [2021],
                "files": [{"name": name, "sha256": file_sha256(staging / name)}
                          for name in names],
            }))

            with patch("scripts.reconcile_obligation_artifacts.build_obligations"), \
                    patch("scripts.reconcile_obligation_artifacts.build_sentinel"):
                self.assertEqual(
                    (1, ["dod/space-force-rdte"], []),
                    reconcile(staging.parent, root),
                )
            baseline = json.loads((root / "reference" / "dod.json").read_text())
            self.assertEqual(complete_pin, baseline["fiscalYears"]["2021"])
            accepted = json.loads(
                (root / "data" / "obligations" / "dod" / "space-force-rdte"
                 / "events" / "FY2021.provenance.json").read_text()
            )
            self.assertEqual(complete_pin, accepted["baselinePin"])
        finally:
            temp.cleanup()

    def test_newer_dual_pin_fails_closed_on_artifact_mismatch(self):
        current = {
            "status": "partial", "asOfPeriod": 9,
            "obligationsCents": 90, "fileBObligationsCents": 100,
            "fileAFileBVarianceCents": -10,
            "fileAFileBVarianceReason": "Approved exact source variance.",
        }
        artifact = {
            "status": "partial", "asOfPeriod": 9,
            "obligationsCents": 100,
        }
        self.assertEqual(
            current,
            _preserve_current_dual_pin(
                "doe/sc", 2026, current, artifact, normalized_total=100
            ),
        )
        for bad_artifact, bad_total in (
            ({**artifact, "obligationsCents": 99}, 100),
            ({**artifact, "asOfPeriod": 8}, 100),
            (artifact, 99),
        ):
            with self.subTest(artifact=bad_artifact, normalized_total=bad_total):
                with self.assertRaisesRegex(ValueError, "does not match"):
                    _preserve_current_dual_pin(
                        "doe/sc", 2026, current, bad_artifact,
                        normalized_total=bad_total,
                    )

    def test_account_year_artifact_updates_baseline_and_atomic_tree(self):
        temp = tempfile.TemporaryDirectory()
        try:
            root = Path(temp.name) / "repo"
            staging = Path(temp.name) / "staging" / "artifact"
            producer = Path(temp.name) / "producer"
            for path in (root / "config", root / "reference", staging, producer):
                path.mkdir(parents=True, exist_ok=True)
            (root / "config" / "obligation_accounts.json").write_text(json.dumps({
                "schemaVersion": 2,
                "refreshDefaults": {"freshnessMaxDays": 10},
                "accounts": [{
                    "path": "doe/sc", "name": "Science", "abbrev": "SC",
                    "agency": "Energy", "federalAccount": "089-0222",
                    "baseline": "reference/doe.json",
                    "availability": {"firstFiscalYear": 2026,
                                     "firstFiscalYearPeriod": 2,
                                     "regularFirstPeriod": 2},
                    "programActivities": [{"slug": "bes", "code": "0001",
                                           "name": "BES"}],
                }],
            }))
            (root / "config" / "funding_sentinel.json").write_text(json.dumps({
                "schemaVersion": 1,
                "financialDetector": {
                    "materialGrossNegativeCents": 2_500,
                    "clusterGrossNegativeCents": 2_500,
                    "clusterMinimumDistinctAwards": 5,
                },
                "sources": [],
            }))
            (root / "reference" / "doe.json").write_text(json.dumps({
                "schemaVersion": 2, "federalAccount": "089-0222",
                "fiscalYears": {"2026": {"status": "partial",
                                          "asOfPeriod": 9,
                                          "firstPeriod": 9,
                                          "obligationsCents": 90,
                                          "fileBObligationsCents": 100,
                                          "fileAFileBVarianceCents": -10,
                                          "fileAFileBVarianceReason":
                                              "Approved exact source variance."}},
            }))
            row = normalize_event({
                "id": "one", "source": "file_b_residual",
                "submissionPeriod": "FY2026P09", "federalAccount": "089-0222",
                "programActivityCode": "0001", "programActivityName": "BES",
                "amountCents": 100, "awardId": "", "linked": False,
            })
            empty_sha = "0" * 64
            downloads = []
            for kind, period in (
                    [("object_class_program_activity", value) for value in range(2, 10)]
                    + [("award_financial", 9)]):
                downloads.append({
                    "submissionType": kind,
                    "requestScope": {"filters": {
                        "fy": 2026, "period": period,
                        "submission_types": [kind], "federal_account": "5778",
                    }, "columns": ["submission_period"]},
                    "acceptedRequestScope": {"filters": {
                        "fy": 2026, "period": period, "federal_account": "5778",
                    }, "download_types": [kind]},
                    "status": "finished", "statusRowCount": 0,
                    "parsedRowCount": 0, "memberRowCounts": {},
                    "archiveSha256": empty_sha,
                    "rawArtifactFile": f"{kind}-P{period:02}.zip",
                })
            provenance = {
                "schemaVersion": 2, "collectionStatus": "accepted",
                "acceptedAt": "2026-08-11T12:00:00+00:00",
                "accountPath": "doe/sc", "federalAccount": "089-0222",
                "fiscalYear": 2026, "asOfPeriod": 9,
                "downloads": downloads,
                "normalized": {"recordCount": 1,
                               "eventFingerprint": event_fingerprint([row]),
                               "netObligationsCents": 100},
                "replacement": {"previousEventFingerprint": empty_sha,
                                "previousProvenanceSha256": None},
                "diff": partition_diff([], [row]),
                # Simulate a partition produced before the branch declared
                # FY2026 as this account's first source year.
                "baselinePin": {"status": "complete", "obligationsCents": 100},
            }
            write_store(producer, [row], {"federalAccount": "089-0222"},
                        partition_metadata={2026: provenance})
            names = ["FY2026.csv.gz", "FY2026.provenance.json"]
            for name in names:
                shutil.copy2(producer / name, staging / name)
            (staging / "partition.json").write_text(json.dumps({
                "schemaVersion": 2, "accountPath": "doe/sc",
                "federalAccount": "089-0222", "baselinePath": "reference/doe.json",
                "fiscalYears": [2026],
                "files": [{"name": name, "sha256": file_sha256(staging / name)}
                          for name in names],
            }))

            self.assertEqual(
                (1, ["doe/sc"], []), reconcile(staging.parent, root)
            )
            baseline = json.loads((root / "reference" / "doe.json").read_text())
            self.assertEqual("partial", baseline["fiscalYears"]["2026"]["status"])
            self.assertEqual(9, baseline["fiscalYears"]["2026"]["asOfPeriod"])
            self.assertEqual(9, baseline["fiscalYears"]["2026"]["firstPeriod"])
            self.assertEqual(90, baseline["fiscalYears"]["2026"]["obligationsCents"])
            self.assertEqual(
                100, baseline["fiscalYears"]["2026"]["fileBObligationsCents"]
            )
            self.assertEqual(
                -10, baseline["fiscalYears"]["2026"]["fileAFileBVarianceCents"]
            )
            accepted = json.loads(
                (root / "data" / "obligations" / "doe" / "sc" / "events"
                 / "FY2026.provenance.json").read_text()
            )
            self.assertEqual(9, accepted["baselinePin"]["firstPeriod"])
            self.assertEqual(90, accepted["baselinePin"]["obligationsCents"])
            self.assertEqual(100,
                             accepted["baselinePin"]["fileBObligationsCents"])
            self.assertEqual([], validate(root, require_data=True,
                                          require_current_provenance=True))
            self.assertEqual([], validate_sentinel(root, require_data=False))
            sentinel = json.loads(
                (root / "data" / "sentinel" / "dashboard.json").read_text()
            )
            self.assertEqual(
                ["089-0222"],
                [row["federalAccount"]
                 for row in sentinel["coverage"]["financialAccounts"]],
            )
        finally:
            temp.cleanup()

    def test_missing_rotating_historical_partition_is_skipped_and_retained(self):
        # A rotating-historical re-pull that fails (e.g. the adapter's
        # per-download cap) loses no data: the committed partition stays.
        # Phase 3.2d remediation W11: reconcile must tolerate this instead
        # of the whole weekly pass committing nothing.
        temp = tempfile.TemporaryDirectory()
        try:
            root = Path(temp.name) / "repo"
            staging = Path(temp.name) / "staging" / "artifact"
            producer = Path(temp.name) / "producer"
            for path in (root / "config", root / "reference", staging, producer):
                path.mkdir(parents=True, exist_ok=True)
            (root / "config" / "obligation_accounts.json").write_text(json.dumps({
                "schemaVersion": 2,
                "accounts": [{
                    "path": "doe/sc", "name": "Science", "abbrev": "SC",
                    "agency": "Energy", "federalAccount": "089-0222",
                    "baseline": "reference/doe.json",
                    "availability": {"firstFiscalYear": 2025,
                                     "firstFiscalYearPeriod": 2,
                                     "regularFirstPeriod": 2},
                    "programActivities": [{"slug": "bes", "code": "0001",
                                           "name": "BES"}],
                }],
            }))

            # A previously committed historical partition (FY2025), complete
            # from an earlier successful reconcile.
            historical_row = normalize_event({
                "id": "hist-one", "source": "file_b_residual",
                "submissionPeriod": "FY2025P12", "federalAccount": "089-0222",
                "programActivityCode": "0001", "programActivityName": "BES",
                "amountCents": 500, "awardId": "", "linked": False,
            })
            historical_provenance = {
                "schemaVersion": 2, "collectionStatus": "accepted",
                "acceptedAt": "2026-08-01T00:00:00+00:00",
                "accountPath": "doe/sc", "federalAccount": "089-0222",
                "fiscalYear": 2025, "asOfPeriod": 12, "downloads": [],
                "normalized": {"recordCount": 1,
                               "eventFingerprint": event_fingerprint([historical_row]),
                               "netObligationsCents": 500},
                "replacement": {}, "diff": partition_diff([], [historical_row]),
                "baselinePin": {"status": "complete", "obligationsCents": 500},
            }
            store = root / "data" / "obligations" / "doe" / "sc" / "events"
            write_store(store, [historical_row], {"federalAccount": "089-0222"},
                        partition_metadata={2025: historical_provenance})
            pre_shard = (store / "FY2025.csv.gz").read_bytes()
            pre_provenance = (store / "FY2025.provenance.json").read_text()

            (root / "reference" / "doe.json").write_text(json.dumps({
                "schemaVersion": 2, "federalAccount": "089-0222",
                "fiscalYears": {"2025": {"status": "complete",
                                          "obligationsCents": 500}},
            }))

            # The mandatory current-FY (2026) pull succeeds and is staged.
            row = normalize_event({
                "id": "one", "source": "file_b_residual",
                "submissionPeriod": "FY2026P09", "federalAccount": "089-0222",
                "programActivityCode": "0001", "programActivityName": "BES",
                "amountCents": 100, "awardId": "", "linked": False,
            })
            provenance = {
                "schemaVersion": 2, "collectionStatus": "accepted",
                "acceptedAt": "2026-08-11T12:00:00+00:00",
                "accountPath": "doe/sc", "federalAccount": "089-0222",
                "fiscalYear": 2026, "asOfPeriod": 9, "downloads": [],
                "normalized": {"recordCount": 1,
                               "eventFingerprint": event_fingerprint([row]),
                               "netObligationsCents": 100},
                "replacement": {}, "diff": partition_diff([], [row]),
                "baselinePin": {"status": "partial", "asOfPeriod": 9,
                                "firstPeriod": 9, "obligationsCents": 100},
            }
            write_store(producer, [row], {"federalAccount": "089-0222"},
                        partition_metadata={2026: provenance})
            names = ["FY2026.csv.gz", "FY2026.provenance.json"]
            for name in names:
                shutil.copy2(producer / name, staging / name)
            (staging / "partition.json").write_text(json.dumps({
                "schemaVersion": 2, "accountPath": "doe/sc",
                "federalAccount": "089-0222", "baselinePath": "reference/doe.json",
                "fiscalYears": [2026],
                "files": [{"name": name, "sha256": file_sha256(staging / name)}
                          for name in names],
            }))

            # FY2025's rotating-historical re-pull failed this run and
            # uploaded no partition; only FY2026 (current) is in staging.
            plan_jobs = [
                {"account": "doe/sc", "fiscalYear": 2026, "purpose": "current"},
                {"account": "doe/sc", "fiscalYear": 2025,
                 "purpose": "rotating-historical"},
            ]
            with patch("scripts.reconcile_obligation_artifacts.build_obligations"), \
                    patch("scripts.reconcile_obligation_artifacts.build_sentinel"):
                count, accounts, skipped = reconcile(
                    staging.parent, root, plan=plan_jobs
                )
            self.assertEqual(1, count)
            self.assertEqual(["doe/sc"], accounts)
            self.assertEqual(
                [{"account": "doe/sc", "fiscalYear": 2025,
                  "purpose": "rotating-historical"}],
                skipped,
            )
            # The committed historical shard/provenance are byte-for-byte
            # untouched -- the failed re-pull lost nothing.
            self.assertEqual(pre_shard, (store / "FY2025.csv.gz").read_bytes())
            self.assertEqual(
                pre_provenance, (store / "FY2025.provenance.json").read_text()
            )
            baseline = json.loads((root / "reference" / "doe.json").read_text())
            self.assertEqual(
                {"status": "complete", "obligationsCents": 500},
                baseline["fiscalYears"]["2025"],
            )
        finally:
            temp.cleanup()

    def test_missing_every_planned_partition_fails_reconcile(self):
        # Phase 3.2d remediation W12: per-account atomicity tolerates any
        # ONE account-year coming up missing, current-FY included -- but a
        # run that stages NOTHING at all (every planned account-year
        # missing) must still fail outright rather than publish a snapshot
        # where every account is silently marked stale.
        temp = tempfile.TemporaryDirectory()
        try:
            root = Path(temp.name) / "repo"
            staging = Path(temp.name) / "staging"
            for path in (root / "config", root / "reference", staging):
                path.mkdir(parents=True, exist_ok=True)
            (root / "config" / "obligation_accounts.json").write_text(json.dumps({
                "schemaVersion": 2,
                "accounts": [{
                    "path": "doe/sc", "name": "Science", "abbrev": "SC",
                    "agency": "Energy", "federalAccount": "089-0222",
                    "baseline": "reference/doe.json",
                    "availability": {"firstFiscalYear": 2025,
                                     "firstFiscalYearPeriod": 2,
                                     "regularFirstPeriod": 2},
                    "programActivities": [{"slug": "bes", "code": "0001",
                                           "name": "BES"}],
                }],
            }))
            (root / "reference" / "doe.json").write_text(json.dumps({
                "schemaVersion": 2, "federalAccount": "089-0222",
                "fiscalYears": {"2025": {"status": "complete",
                                          "obligationsCents": 500}},
            }))
            # Nothing is staged: the current-FY pull job failed outright,
            # and it is the ONLY planned account-year this run.
            plan_jobs = [
                {"account": "doe/sc", "fiscalYear": 2026, "purpose": "current"},
            ]
            with self.assertRaisesRegex(
                    ValueError, "refusing to publish an all-accounts-stale"):
                reconcile(staging, root, plan=plan_jobs)
        finally:
            temp.cleanup()

    def test_missing_current_partition_is_skipped_and_marked_stale(self):
        # Phase 3.2d remediation W12: a missing CURRENT-FY partition for one
        # account is tolerated exactly like a missing historical one -- as
        # long as at least one other planned account-year in this run
        # succeeded, reconcile must not raise, the failed account's
        # committed store must be untouched, and refresh_status.json must
        # record it stale with a reason and a staleSince date.
        temp = tempfile.TemporaryDirectory()
        try:
            root = Path(temp.name) / "repo"
            staging = Path(temp.name) / "staging" / "artifact"
            producer = Path(temp.name) / "producer"
            for path in (root / "config", root / "reference", staging, producer):
                path.mkdir(parents=True, exist_ok=True)
            (root / "config" / "obligation_accounts.json").write_text(json.dumps({
                "schemaVersion": 2,
                "accounts": [
                    {
                        "path": "doe/sc", "name": "Science", "abbrev": "SC",
                        "agency": "Energy", "federalAccount": "089-0222",
                        "baseline": "reference/doe.json",
                        "availability": {"firstFiscalYear": 2025,
                                         "firstFiscalYearPeriod": 2,
                                         "regularFirstPeriod": 2},
                        "programActivities": [{"slug": "bes", "code": "0001",
                                               "name": "BES"}],
                    },
                    {
                        "path": "doe/fossil-energy", "name": "Fossil Energy",
                        "abbrev": "FE", "agency": "Energy",
                        "federalAccount": "089-0223",
                        "baseline": "reference/doe_fe.json",
                        "availability": {"firstFiscalYear": 2025,
                                         "firstFiscalYearPeriod": 2,
                                         "regularFirstPeriod": 2},
                        "programActivities": [{"slug": "fe", "code": "0001",
                                               "name": "FE"}],
                    },
                ],
            }))

            # doe/sc already has a committed, accepted current-FY (2026)
            # partition from a previous week's run at P08.
            stale_row = normalize_event({
                "id": "stale-one", "source": "file_b_residual",
                "submissionPeriod": "FY2026P08", "federalAccount": "089-0222",
                "programActivityCode": "0001", "programActivityName": "BES",
                "amountCents": 300, "awardId": "", "linked": False,
            })
            stale_provenance = {
                "schemaVersion": 2, "collectionStatus": "accepted",
                "acceptedAt": "2026-09-01T00:00:00+00:00",
                "accountPath": "doe/sc", "federalAccount": "089-0222",
                "fiscalYear": 2026, "asOfPeriod": 8, "downloads": [],
                "normalized": {"recordCount": 1,
                               "eventFingerprint": event_fingerprint([stale_row]),
                               "netObligationsCents": 300},
                "replacement": {}, "diff": partition_diff([], [stale_row]),
                "baselinePin": {"status": "partial", "asOfPeriod": 8,
                                "firstPeriod": 8, "obligationsCents": 300},
            }
            sc_store = root / "data" / "obligations" / "doe" / "sc" / "events"
            write_store(sc_store, [stale_row], {"federalAccount": "089-0222"},
                        partition_metadata={2026: stale_provenance})
            pre_shard = (sc_store / "FY2026.csv.gz").read_bytes()
            pre_provenance = (sc_store / "FY2026.provenance.json").read_text()
            (root / "reference" / "doe.json").write_text(json.dumps({
                "schemaVersion": 2, "federalAccount": "089-0222",
                "fiscalYears": {"2026": {"status": "partial", "asOfPeriod": 8,
                                          "firstPeriod": 8,
                                          "obligationsCents": 300}},
            }))

            # doe/fossil-energy's current-FY (2026) pull succeeds this run.
            fresh_row = normalize_event({
                "id": "fresh-one", "source": "file_b_residual",
                "submissionPeriod": "FY2026P09", "federalAccount": "089-0223",
                "programActivityCode": "0001", "programActivityName": "FE",
                "amountCents": 100, "awardId": "", "linked": False,
            })
            fresh_provenance = {
                "schemaVersion": 2, "collectionStatus": "accepted",
                "acceptedAt": "2026-09-20T00:00:00+00:00",
                "accountPath": "doe/fossil-energy", "federalAccount": "089-0223",
                "fiscalYear": 2026, "asOfPeriod": 9, "downloads": [],
                "normalized": {"recordCount": 1,
                               "eventFingerprint": event_fingerprint([fresh_row]),
                               "netObligationsCents": 100},
                "replacement": {}, "diff": partition_diff([], [fresh_row]),
                "baselinePin": {"status": "partial", "asOfPeriod": 9,
                                "firstPeriod": 9, "obligationsCents": 100},
            }
            (root / "reference" / "doe_fe.json").write_text(json.dumps({
                "schemaVersion": 2, "federalAccount": "089-0223",
                "fiscalYears": {}
            }))
            write_store(producer, [fresh_row], {"federalAccount": "089-0223"},
                        partition_metadata={2026: fresh_provenance})
            names = ["FY2026.csv.gz", "FY2026.provenance.json"]
            for name in names:
                shutil.copy2(producer / name, staging / name)
            (staging / "partition.json").write_text(json.dumps({
                "schemaVersion": 2, "accountPath": "doe/fossil-energy",
                "federalAccount": "089-0223",
                "baselinePath": "reference/doe_fe.json",
                "fiscalYears": [2026],
                "files": [{"name": name, "sha256": file_sha256(staging / name)}
                          for name in names],
            }))

            # doe/sc's current-FY pull failed this run and uploaded no
            # partition; only doe/fossil-energy is in staging.
            plan_jobs = [
                {"account": "doe/sc", "fiscalYear": 2026, "purpose": "current"},
                {"account": "doe/fossil-energy", "fiscalYear": 2026,
                 "purpose": "current"},
            ]
            with patch("scripts.reconcile_obligation_artifacts.build_obligations"), \
                    patch("scripts.reconcile_obligation_artifacts.build_sentinel"):
                count, accounts, skipped = reconcile(
                    staging.parent, root, plan=plan_jobs
                )
            self.assertEqual(1, count)
            self.assertEqual(["doe/fossil-energy"], accounts)
            self.assertEqual(
                [{"account": "doe/sc", "fiscalYear": 2026, "purpose": "current"}],
                skipped,
            )
            # doe/sc's committed store is byte-for-byte untouched.
            self.assertEqual(pre_shard, (sc_store / "FY2026.csv.gz").read_bytes())
            self.assertEqual(
                pre_provenance, (sc_store / "FY2026.provenance.json").read_text()
            )

            refresh_status = json.loads(
                (root / "data" / "obligations" / "refresh_status.json").read_text()
            )
            self.assertEqual(1, refresh_status["schemaVersion"])
            sc_status = refresh_status["accounts"]["doe/sc"]
            self.assertEqual("stale", sc_status["status"])
            self.assertEqual("2026-09-01", sc_status["staleSince"])
            self.assertTrue(sc_status["reason"])
            fe_status = refresh_status["accounts"]["doe/fossil-energy"]
            self.assertEqual("fresh", fe_status["status"])
            self.assertEqual(
                "2026-09-20T00:00:00+00:00", fe_status["lastAcceptedAt"]
            )
        finally:
            temp.cleanup()


if __name__ == "__main__":
    unittest.main()
