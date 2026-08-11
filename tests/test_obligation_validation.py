import json
import tempfile
import unittest
from pathlib import Path

from adapters.obligation_common import normalize_event, write_store
from scripts.validate_obligations import validate


class ObligationValidationTests(unittest.TestCase):
    def fixture(self, expected):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        (root / "config").mkdir()
        (root / "reference").mkdir()
        (root / "config" / "obligation_accounts.json").write_text(json.dumps({
            "accounts": [{"path": "doe/sc", "federalAccount": "089-0222",
                          "baseline": "reference/doe_sc_obligation_baseline.json",
                          "programActivities": [{"code": "0001"}]}]}))
        (root / "reference" / "doe_sc_obligation_baseline.json").write_text(json.dumps({
            "federalAccount": "089-0222",
            "fiscalYears": {"2024": {"status": "complete", "obligationsCents": expected}}}))
        row = normalize_event({"id": "one", "source": "file_b_residual",
            "submissionPeriod": "FY2024P12", "federalAccount": "089-0222",
            "programActivityCode": "0001", "programActivityName": "BES",
            "amountCents": 100, "awardId": "", "linked": False})
        write_store(
            root / "data" / "obligations" / "doe" / "sc" / "events",
            [row], {"federalAccount": "089-0222"},
        )
        return temp, root

    def test_exact_gtas_cents_pass(self):
        temp, root = self.fixture(100)
        try:
            self.assertEqual([], validate(root, require_data=False))
        finally:
            temp.cleanup()

    def test_one_cent_difference_fails(self):
        temp, root = self.fixture(101)
        try:
            self.assertTrue(any("!= GTAS" in e for e in validate(root, require_data=False)))
        finally:
            temp.cleanup()

    def test_foreign_award_url_fails(self):
        temp, root = self.fixture(100)
        try:
            store = root / "data" / "obligations" / "doe" / "sc" / "events"
            rows = [normalize_event({"id": "one", "source": "file_b_residual",
                "submissionPeriod": "FY2024P12", "federalAccount": "089-0222",
                "programActivityCode": "0001", "programActivityName": "BES",
                "amountCents": 100, "awardId": "", "linked": False}),
                normalize_event({"id": "linked", "source": "file_c",
                "submissionPeriod": "FY2024P12", "federalAccount": "089-0222",
                "programActivityCode": "0001", "programActivityName": "BES",
                "amountCents": 0, "awardId": "A1", "linked": True,
                "awardUrl": "https://example.com/award/A1"})]
            write_store(store, rows, {"federalAccount": "089-0222"})
            self.assertTrue(any("invalid public USAspending award URL" in e
                                for e in validate(root, require_data=False)))
        finally:
            temp.cleanup()

    def test_manifest_fingerprint_mismatch_fails(self):
        temp, root = self.fixture(100)
        try:
            manifest = root / "data" / "obligations" / "doe" / "sc" / "events" / "manifest.json"
            value = json.loads(manifest.read_text())
            value["sha256"] = "bad"
            manifest.write_text(json.dumps(value))
            self.assertTrue(any("manifest fingerprint mismatch" in e
                                for e in validate(root, require_data=False)))
        finally:
            temp.cleanup()

    def test_missing_required_fiscal_year_fails(self):
        temp, root = self.fixture(100)
        try:
            baseline = root / "reference" / "doe_sc_obligation_baseline.json"
            value = json.loads(baseline.read_text())
            value["fiscalYears"]["2023"] = {
                "status": "complete", "obligationsCents": 0,
            }
            baseline.write_text(json.dumps(value))
            self.assertTrue(any("FY2023: required complete snapshot is missing" in e
                                for e in validate(root, require_data=False)))
        finally:
            temp.cleanup()


if __name__ == "__main__":
    unittest.main()
