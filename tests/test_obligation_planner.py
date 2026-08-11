import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from scripts.plan_obligation_refresh import plan, source_period


class ObligationPlannerTests(unittest.TestCase):
    def fixture(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        (root / "config").mkdir()
        (root / "reference").mkdir()
        (root / "config" / "obligation_accounts.json").write_text(json.dumps({
            "schemaVersion": 2,
            "refreshDefaults": {"reportingLagMonths": 2},
            "accounts": [{"path": "doe/sc", "federalAccount": "089-0222",
                          "baseline": "reference/doe.json"}],
        }))
        (root / "reference" / "doe.json").write_text(json.dumps({
            "schemaVersion": 2, "federalAccount": "089-0222",
            "fiscalYears": {
                "2023": {"status": "complete"},
                "2024": {"status": "complete"},
                "2025": {"status": "complete"},
                "2026": {"status": "partial", "asOfPeriod": 9},
            },
        }))
        return temp, root

    def test_reporting_lag_maps_to_federal_period(self):
        self.assertEqual((2026, 9), source_period(date(2026, 8, 11), 2))
        self.assertEqual((2025, 12), source_period(date(2025, 11, 10), 2))

    def test_weekly_refresh_has_current_and_one_rotating_history(self):
        temp, root = self.fixture()
        try:
            rows = plan(root, today=date(2026, 8, 11))["include"]
            self.assertEqual(2, len(rows))
            current = next(row for row in rows if row["purpose"] == "current")
            self.assertEqual((2026, 9), (current["fiscalYear"], current["period"]))
            self.assertEqual(1, len([
                row for row in rows if row["purpose"] == "rotating-historical"
            ]))
        finally:
            temp.cleanup()

    def test_full_uses_registry_baseline_statuses(self):
        temp, root = self.fixture()
        try:
            rows = plan(root, mode="full")["include"]
            self.assertEqual([2023, 2024, 2025, 2026],
                             [row["fiscalYear"] for row in rows])
            self.assertEqual(9, rows[-1]["period"])
        finally:
            temp.cleanup()

    def test_new_fiscal_year_starts_at_p02_and_p01_finishes_prior_year(self):
        temp, root = self.fixture()
        try:
            december = plan(root, today=date(2026, 12, 15))["include"]
            current = next(row for row in december if row["purpose"] == "current")
            self.assertEqual((2026, 12),
                             (current["fiscalYear"], current["period"]))
            january = plan(root, today=date(2027, 1, 15))["include"]
            current = next(row for row in january if row["purpose"] == "current")
            self.assertEqual((2027, 2),
                             (current["fiscalYear"], current["period"]))
        finally:
            temp.cleanup()


if __name__ == "__main__":
    unittest.main()
