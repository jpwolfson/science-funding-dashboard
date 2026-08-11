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
                          "programActivities": [{"code": "0001"}]}]}))
        (root / "reference" / "doe_sc_obligation_baseline.json").write_text(json.dumps({
            "fiscalYears": {"2024": {"status": "complete", "obligationsCents": expected}}}))
        row = normalize_event({"id": "one", "source": "file_b_residual",
            "submissionPeriod": "FY2024P12", "federalAccount": "089-0222",
            "programActivityCode": "0001", "programActivityName": "BES",
            "amountCents": 100, "awardId": "", "linked": False})
        write_store(root / "data" / "obligations" / "doe" / "sc" / "events", [row])
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


if __name__ == "__main__":
    unittest.main()
