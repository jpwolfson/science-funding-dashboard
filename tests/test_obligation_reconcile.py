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
    _preserve_current_complete_pin, _preserve_current_dual_pin, reconcile,
)
from scripts.validate_funding_sentinel import validate as validate_sentinel
from scripts.validate_obligations import validate


class ObligationReconcileTests(unittest.TestCase):
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
                    (1, ["dod/space-force-rdte"]), reconcile(staging.parent, root)
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

            self.assertEqual((1, ["doe/sc"]), reconcile(staging.parent, root))
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


if __name__ == "__main__":
    unittest.main()
