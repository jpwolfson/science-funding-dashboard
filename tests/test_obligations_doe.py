"""Phase 3.2d DOE account-onboarding contracts."""

import json
import unittest
from pathlib import Path

from adapters.usaspending_obligations import alias_map
from scripts.plan_obligation_refresh import plan


REPO = Path(__file__).resolve().parent.parent

EXPECTED = {
    "doe/arpa-e": ("089-0337", "Advanced Research Projects Agency-Energy", 4),
    "doe/eere": ("089-0321", "Energy Efficiency and Renewable Energy", 26),
    "doe/oced": ("089-2297", "Clean Energy Demonstrations", 16),
    "doe/fossil-energy": ("089-0213", "Fossil Energy", 27),
    "doe/electricity": ("089-0318", "Electricity", 19),
    "doe/ceser": (
        "089-2250", "Cybersecurity, Energy Security, and Emergency Response", 11,
    ),
    "doe/nuclear-energy": ("089-0319", "Nuclear Energy", 29),
    "doe/nnsa-weapons-activities": ("089-0240", "Weapons Activities", 29),
    "doe/nnsa-defense-nuclear-nonproliferation": (
        "089-0309", "Defense Nuclear Nonproliferation", 16,
    ),
    "doe/eia": ("089-0216", "Energy Information Administration", 3),
}

NATIVE_PARK_IDENTITIES = {
    "doe/eere": {"5WKQ3U7VKXN", "63YPT7SFFAZ"},
    "doe/fossil-energy": {"5UWQ6Q4BYMT", "5ZCQYAMAF08"},
    "doe/electricity": {"63YPT7S7RDC"},
    "doe/ceser": {"63YPTC2RBEP", "63YPTC2RBF1"},
    "doe/nuclear-energy": {"63YPT7SACCH"},
    "doe/nnsa-defense-nuclear-nonproliferation": {"608PP9VRRFG"},
}


class DoeOnboardingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        registry = json.loads(
            (REPO / "config" / "obligation_accounts.json").read_text()
        )
        cls.accounts = {row["path"]: row for row in registry["accounts"]}

    def test_expected_resolved_accounts_and_official_titles(self):
        for path, (federal_account, title, count) in EXPECTED.items():
            with self.subTest(path=path):
                row = self.accounts[path]
                self.assertEqual(federal_account, row["federalAccount"])
                self.assertEqual(title, row["name"])
                self.assertEqual("Department of Energy", row["agency"])
                self.assertEqual(count, len(row["programActivities"]))

    def test_office_of_science_remains_the_separate_regression_fixture(self):
        science = self.accounts["doe/sc"]
        self.assertEqual("089-0222", science["federalAccount"])
        self.assertEqual("reference/doe_sc_obligation_baseline.json", science["baseline"])
        self.assertNotIn("doe/sc", EXPECTED)

    def test_program_activity_aliases_are_unambiguous(self):
        for path in EXPECTED:
            with self.subTest(path=path):
                account = self.accounts[path]
                activities = account["programActivities"]
                codes = [row["code"] for row in activities]
                slugs = [row["slug"] for row in activities]
                parks = [row["park"] for row in activities if row["park"]]
                self.assertEqual(len(codes), len(set(codes)))
                self.assertEqual(len(slugs), len(set(slugs)))
                self.assertEqual(len(parks), len(set(parks)))
                self.assertIn("0000", codes)
                aliases = alias_map(account)
                for activity in activities:
                    self.assertIs(activity, aliases[activity["code"]])
                    if activity["park"]:
                        self.assertIs(activity, aliases[activity["park"]])

    def test_park_native_identities_are_not_silently_forced_into_legacy_codes(self):
        for path, expected in NATIVE_PARK_IDENTITIES.items():
            with self.subTest(path=path):
                activities = self.accounts[path]["programActivities"]
                actual = {
                    row["code"] for row in activities
                    if len(row["code"]) > 4 and row["code"] == row["park"]
                }
                self.assertEqual(expected, actual)

    def test_nnsa_account_boundary_stays_explicit(self):
        weapons = {
            row["code"]: row for row in
            self.accounts["doe/nnsa-weapons-activities"]["programActivities"]
        }
        nonproliferation = {
            row["code"]: row for row in self.accounts[
                "doe/nnsa-defense-nuclear-nonproliferation"
            ]["programActivities"]
        }
        self.assertEqual("5UWPV21LNPR", weapons["0001"]["park"])
        self.assertEqual("5UWPV26R8KX", nonproliferation["0001"]["park"])
        self.assertEqual("Weapons Activities (Direct)", weapons["0001"]["name"])
        self.assertEqual(
            "Defense Nuclear Nonproliferation (Direct)",
            nonproliferation["0001"]["name"],
        )
        self.assertNotIn("0010", weapons)
        self.assertEqual(
            "Defense Nuclear Nonproliferation Research and Development",
            nonproliferation["0010"]["name"],
        )

    def test_full_backfill_plan_replaces_every_partial_scaffold(self):
        for path in EXPECTED:
            with self.subTest(path=path):
                jobs = plan(REPO, mode="full", selectors=path)["include"]
                self.assertEqual(list(range(2017, 2027)), [
                    row["fiscalYear"] for row in jobs
                ])
                self.assertEqual(12, jobs[0]["period"])
                self.assertEqual(9, jobs[-1]["period"])

                baseline = json.loads((REPO / self.accounts[path]["baseline"]).read_text())
                self.assertEqual("unavailable", baseline["fiscalYears"]["2015"]["status"])
                self.assertEqual("unavailable", baseline["fiscalYears"]["2016"]["status"])
                self.assertEqual(6, baseline["fiscalYears"]["2017"]["firstPeriod"])
                self.assertEqual(12, baseline["fiscalYears"]["2017"]["asOfPeriod"])
                self.assertEqual("partial", baseline["fiscalYears"]["2026"]["status"])
                self.assertEqual(9, baseline["fiscalYears"]["2026"]["asOfPeriod"])

                store = REPO / "data" / "obligations" / path / "events"
                if store.exists():
                    for fiscal_year in range(2017, 2027):
                        self.assertIn(
                            "obligationsCents",
                            baseline["fiscalYears"][str(fiscal_year)],
                            f"{path} FY{fiscal_year} retained an unfilled scaffold",
                        )


if __name__ == "__main__":
    unittest.main()
