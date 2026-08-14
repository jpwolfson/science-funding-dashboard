import json
import shutil
import tempfile
import unittest
from pathlib import Path

from adapters.obligation_common import (
    event_fingerprint, file_sha256, normalize_event, partition_diff, write_store,
)
from scripts.reconcile_obligation_artifacts import reconcile
from scripts.validate_funding_sentinel import validate as validate_sentinel
from scripts.validate_obligations import validate


class ObligationReconcileTests(unittest.TestCase):
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
                                          "asOfPeriod": 8,
                                          "obligationsCents": 90}},
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
                "baselinePin": {"status": "partial", "asOfPeriod": 9,
                                "firstPeriod": 2, "obligationsCents": 100},
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
            self.assertEqual(9, baseline["fiscalYears"]["2026"]["asOfPeriod"])
            self.assertEqual(9, baseline["fiscalYears"]["2026"]["firstPeriod"])
            accepted = json.loads(
                (root / "data" / "obligations" / "doe" / "sc" / "events"
                 / "FY2026.provenance.json").read_text()
            )
            self.assertEqual(9, accepted["baselinePin"]["firstPeriod"])
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
