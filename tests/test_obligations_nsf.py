import json
import unittest
from pathlib import Path

from adapters.usaspending_obligations import alias_map
from scripts.plan_obligation_refresh import plan


REPO = Path(__file__).resolve().parent.parent


class NSFObligationOnboardingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        registry = json.loads(
            (REPO / "config" / "obligation_accounts.json").read_text()
        )
        cls.accounts = {
            row["path"]: row for row in registry["accounts"]
            if row["path"].startswith("nsf/")
        }
        cls.crosswalk = json.loads(
            (REPO / "reference" / "aaas_federal_account_crosswalk.json").read_text()
        )["rows"]

    def test_exact_resolved_account_scope_and_titles(self):
        expected = {
            "nsf/rra": (
                "049-0100",
                "Research and Related Activities, National Science Foundation",
            ),
            "nsf/stem-education": (
                "049-0106",
                "STEM Education, National Science Foundation",
            ),
            "nsf/aoam": (
                "049-0180",
                "Agency Operations and Award Management, National Science Foundation",
            ),
            "nsf/mrefc": (
                "049-0551",
                "Major Research Equipment and Facilities Construction, National Science Foundation",
            ),
        }
        self.assertEqual(set(expected), set(self.accounts))
        for path, (symbol, official_title) in expected.items():
            account = self.accounts[path]
            self.assertEqual(symbol, account["federalAccount"])
            matches = [
                row for row in self.crosswalk
                if any(item.get("code") == symbol
                       for item in row.get("federal_accounts", []))
            ]
            self.assertTrue(matches)
            self.assertTrue(all(row["status"] == "resolved" for row in matches))
            self.assertTrue(any(
                item.get("title") == official_title
                for row in matches for item in row.get("federal_accounts", [])
                if item.get("code") == symbol
            ))

    def test_baseline_scaffolds_cover_the_full_source_window(self):
        for account in self.accounts.values():
            baseline = json.loads((REPO / account["baseline"]).read_text())
            self.assertEqual(2, baseline["schemaVersion"])
            self.assertEqual(account["federalAccount"], baseline["federalAccount"])
            years = baseline["fiscalYears"]
            self.assertEqual(set(map(str, range(2015, 2027))), set(years))
            self.assertEqual("unavailable", years["2015"]["status"])
            self.assertEqual("unavailable", years["2016"]["status"])
            self.assertEqual(
                {"status": "partial", "asOfPeriod": 12, "firstPeriod": 6},
                years["2017"],
            )
            for fiscal_year in range(2018, 2026):
                self.assertEqual(
                    {"status": "partial", "asOfPeriod": 12},
                    years[str(fiscal_year)],
                )
            self.assertEqual(
                {"status": "partial", "asOfPeriod": 9}, years["2026"]
            )
            self.assertFalse(any(
                "obligationsCents" in row for row in years.values()
                if row["status"] != "unavailable"
            ))

    def test_full_backfill_plan_replaces_every_scaffold(self):
        jobs = plan(repo=REPO, mode="full", selectors="nsf")["include"]
        self.assertEqual(40, len(jobs))
        by_account = {}
        for job in jobs:
            by_account.setdefault(job["account"], []).append(
                (job["fiscalYear"], job["period"])
            )
        self.assertEqual(set(self.accounts), set(by_account))
        expected = [(fy, 9 if fy == 2026 else 12) for fy in range(2017, 2027)]
        for rows in by_account.values():
            self.assertEqual(expected, rows)

    def test_reviewed_program_activity_aliases_are_unique(self):
        expected_codes = {
            "nsf/rra": {
                "0000", "0001", "0002", "0003", "0005", "0006", "0007",
                "0008", "0009", "0010", "0011", "0013", "0015", "0016",
                "00U1", "00U2", "0401", "0402", "0801",
            },
            "nsf/stem-education": {"0000", "0001", "0302", "0303", "0401", "0801"},
            "nsf/aoam": {"0000", "0001", "0401", "0801"},
            "nsf/mrefc": {"0000", "0001", "0401"},
        }
        for path, account in self.accounts.items():
            activities = account["programActivities"]
            codes = [row["code"] for row in activities]
            slugs = [row["slug"] for row in activities]
            parks = [row["park"] for row in activities if row.get("park")]
            self.assertEqual(expected_codes[path], set(codes))
            self.assertEqual(len(codes), len(set(codes)))
            self.assertEqual(len(slugs), len(set(slugs)))
            self.assertEqual(len(parks), len(set(parks)))
            aliases = alias_map(account)
            for activity in activities:
                self.assertIs(activity, aliases[activity["code"]])
                if activity.get("park"):
                    self.assertIs(activity, aliases[activity["park"]])


if __name__ == "__main__":
    unittest.main()
