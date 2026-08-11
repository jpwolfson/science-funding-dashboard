import json
import tempfile
import unittest
from pathlib import Path

from adapters.funding_sentinel import build
from adapters.obligation_common import normalize_event, write_store
from scripts.validate_funding_sentinel import validate


class FundingSentinelValidationTests(unittest.TestCase):
    def fixture(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        (root / "config").mkdir()
        (root / "config" / "funding_sentinel.json").write_text(json.dumps({
            "schemaVersion": 1,
            "financialDetector": {
                "materialGrossNegativeCents": 2_500,
                "clusterGrossNegativeCents": 2_500,
                "clusterMinimumDistinctAwards": 5,
            },
            "sources": [],
        }))
        (root / "config" / "obligation_accounts.json").write_text(json.dumps({
            "schemaVersion": 2,
            "accounts": [{
                "path": "doe/sc", "agency": "Department of Energy",
                "name": "Office of Science", "abbrev": "DOE SC",
                "federalAccount": "089-0222",
            }],
        }))
        file_c = normalize_event({
            "id": "file-c", "source": "file_c",
            "submissionPeriod": "FY2025P02", "federalAccount": "089-0222",
            "programActivityCode": "0001", "programActivityName": "BES",
            "amountCents": 7_500, "grossPositiveCents": 10_000,
            "grossNegativeCents": -2_500, "awardId": "A1", "linked": True,
        })
        residual = normalize_event({
            "id": "residual", "source": "file_b_residual",
            "submissionPeriod": "FY2025P02", "federalAccount": "089-0222",
            "programActivityCode": "0001", "programActivityName": "BES",
            "amountCents": -100_000, "awardId": "", "linked": False,
        })
        write_store(
            root / "data" / "obligations" / "doe" / "sc" / "events",
            [file_c, residual], {"federalAccount": "089-0222"},
        )
        build(root, "2026-08-11")
        return temp, root

    def test_valid_core_store_passes(self):
        temp, root = self.fixture()
        try:
            self.assertEqual([], validate(root))
            dashboard = json.loads(
                (root / "data" / "sentinel" / "dashboard.json").read_text()
            )
            self.assertEqual("089-0222", dashboard["coverage"]
                             ["financialAccounts"][0]["federalAccount"])
            self.assertEqual([], dashboard["coverage"]["authoritativeSources"])
        finally:
            temp.cleanup()

    def test_file_b_residual_join_fails(self):
        temp, root = self.fixture()
        try:
            path = root / "data" / "sentinel" / "financial-observations.json"
            value = json.loads(path.read_text())
            value["observations"][0]["ledgerEventIds"].append("residual")
            path.write_text(json.dumps(value))
            errors = validate(root)
            self.assertTrue(any("File B residual" in error for error in errors))
        finally:
            temp.cleanup()

    def test_missing_limitations_and_optional_review_policy_fail(self):
        temp, root = self.fixture()
        try:
            path = root / "data" / "sentinel" / "dashboard.json"
            value = json.loads(path.read_text())
            value["limitations"] = []
            value["reviewPolicy"] = "Reviews required."
            path.write_text(json.dumps(value))
            errors = validate(root)
            self.assertTrue(any("coverage limitation" in error for error in errors))
            self.assertTrue(any("non-blocking review policy" in error
                                for error in errors))
        finally:
            temp.cleanup()

    def test_stale_coverage_contract_fails(self):
        temp, root = self.fixture()
        try:
            path = root / "data" / "sentinel" / "dashboard.json"
            value = json.loads(path.read_text())
            value["coverage"]["financialAccounts"] = []
            path.write_text(json.dumps(value))
            errors = validate(root)
            self.assertTrue(any("coverage does not match" in error
                                for error in errors))
        finally:
            temp.cleanup()


if __name__ == "__main__":
    unittest.main()
