import json
import unittest
from pathlib import Path

from adapters.usaspending_obligations import alias_map
from scripts.plan_obligation_refresh import plan


REPO = Path(__file__).resolve().parent.parent

# The current fiscal year's partial baseline pin (status "partial",
# asOfPeriod, obligationsCents) advances every week the scheduled
# obligation refresh runs. Unit tests may not pin its literal value --
# doing so guarantees the suite goes red on the first advance after any
# release (docs/phase-3.2d-remediation-brief.md, W6). Historical rows
# (status "complete", or FY2017's frozen partial start-of-series row) are
# not moving and keep exact literal pins.
MINIMUM_CURRENT_FY_PERIOD = 9


def current_partial_fiscal_year(fiscal_years):
    """Return the highest FY still 'partial' in a baseline -- the live
    current FY. FY2017's frozen historical partial pin is always older
    than the live current year, so max() finds it without a hard-coded
    year number.
    """
    return max(
        int(fy) for fy, row in fiscal_years.items()
        if row.get("status") == "partial"
    )


def assert_current_partial_row(test, row, minimum_period=MINIMUM_CURRENT_FY_PERIOD):
    """Structural-only assertion for the current (moving) partial FY row.
    Exact-cent equality against the source is already enforced by
    scripts/validate_obligations.py.
    """
    test.assertEqual("partial", row["status"])
    test.assertIsInstance(row["asOfPeriod"], int)
    test.assertGreaterEqual(row["asOfPeriod"], minimum_period)
    test.assertLessEqual(row["asOfPeriod"], 12)
    test.assertIsInstance(row["obligationsCents"], int)


def assert_current_period_job(test, job, minimum_period=MINIMUM_CURRENT_FY_PERIOD):
    """Structural-only assertion for a planner job covering the current FY."""
    test.assertIsInstance(job["period"], int)
    test.assertGreaterEqual(job["period"], minimum_period)
    test.assertLessEqual(job["period"], 12)


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

    def test_baselines_cover_the_full_source_window_before_and_after_backfill(self):
        for path, account in self.accounts.items():
            baseline = json.loads((REPO / account["baseline"]).read_text())
            self.assertEqual(2, baseline["schemaVersion"])
            self.assertEqual(account["federalAccount"], baseline["federalAccount"])
            years = baseline["fiscalYears"]
            self.assertEqual(set(map(str, range(2015, 2027))), set(years))
            self.assertEqual("unavailable", years["2015"]["status"])
            self.assertEqual("unavailable", years["2016"]["status"])
            self.assertEqual("partial", years["2017"]["status"])
            self.assertEqual(12, years["2017"]["asOfPeriod"])
            self.assertEqual(6, years["2017"]["firstPeriod"])
            assert_current_partial_row(self, years["2026"])
            store = REPO / "data" / "obligations" / path / "events"
            if store.exists():
                for fiscal_year in range(2017, 2027):
                    self.assertIn(
                        "obligationsCents",
                        years[str(fiscal_year)],
                        f"{path} FY{fiscal_year} retained an unfilled scaffold",
                    )
                for fiscal_year in range(2018, 2026):
                    self.assertEqual("complete", years[str(fiscal_year)]["status"])
            else:
                for fiscal_year in range(2018, 2026):
                    self.assertEqual(
                        {"status": "partial", "asOfPeriod": 12},
                        years[str(fiscal_year)],
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
        expected_historical = [(fy, 12) for fy in range(2017, 2026)]
        for rows in by_account.values():
            self.assertEqual(expected_historical, rows[:-1])
            self.assertEqual(2026, rows[-1][0])
            assert_current_period_job(
                self, {"period": rows[-1][1]}
            )

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
                pair = (
                    "code-name",
                    str(activity["code"]).zfill(4),
                    activity["name"].strip().lower(),
                )
                self.assertEqual(activity["slug"], aliases[pair]["slug"])
                self.assertEqual(
                    activity["slug"],
                    aliases[("code", str(activity["code"]).zfill(4))]["slug"],
                )
                if activity.get("park"):
                    self.assertEqual(
                        activity["slug"],
                        aliases[("park", activity["park"])]["slug"],
                    )


if __name__ == "__main__":
    unittest.main()
