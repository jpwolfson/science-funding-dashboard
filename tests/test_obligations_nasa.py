"""Offline account contracts for the staged Phase 3.2d NASA rollout."""

import json
import unittest
from pathlib import Path

from adapters.usaspending_obligations import alias_map, parse_file_b_snapshot
from scripts.plan_obligation_refresh import plan


REPO = Path(__file__).resolve().parent.parent
EXPECTED_ACCOUNTS = {
    "nasa/science": ("080-0120", "Science"),
    "nasa/aeronautics": ("080-0126", "Aeronautics"),
    "nasa/space-technology": ("080-0131", "Space Technology"),
    "nasa/stem-engagement": (
        "080-0128",
        "Science, Technology, Engineering, and Mathematics Engagement",
    ),
}
EXPECTED_CENTS = {
    "nasa/science": [
        580635184620, 615406027421, 668434852041, 727742760754,
        710528050433, 781081970082, 792504133274, 726300678004,
        760283157214, 473335964862,
    ],
    "nasa/aeronautics": [
        66013033435, 68558100461, 72900591151, 78834274091,
        84508616452, 87399166899, 94425768765, 97417704263,
        96680983467, 50861750910,
    ],
    "nasa/space-technology": [
        72019958276, 77158674286, 90789788516, 109112319017,
        117511331201, 111068326813, 119919391987, 108979017841,
        96593899268, 36122857204,
    ],
    "nasa/stem-engagement": [
        10543835769, 10493930251, 11033682312, 12072228456,
        12925056091, 13230090452, 15380938964, 14151489463,
        12782240041, 7540313657,
    ],
}
STAGE_SELECTORS = {
    "nasa/science": 10,
    "nasa/aeronautics,nasa/space-technology,nasa/stem-engagement": 30,
}


class NASAObligationScaffoldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        registry = json.loads(
            (REPO / "config" / "obligation_accounts.json").read_text()
        )
        cls.accounts = {
            row["path"]: row for row in registry["accounts"]
            if row["path"].startswith("nasa/")
        }

    def test_exact_registered_stage_scope_and_titles(self):
        self.assertEqual(set(EXPECTED_ACCOUNTS), set(self.accounts))
        for path, (symbol, title) in EXPECTED_ACCOUNTS.items():
            account = self.accounts[path]
            self.assertEqual(symbol, account["federalAccount"])
            self.assertEqual(title, account["name"])
            self.assertEqual("080", account["agencyIdentifier"])
            self.assertEqual(
                "National Aeronautics and Space Administration", account["agency"]
            )
            self.assertEqual("usaspending_obligations", account["adapter"])
            self.assertEqual({
                "firstFiscalYear": 2017,
                "firstFiscalYearPeriod": 6,
                "regularFirstPeriod": 2,
            }, account["availability"])

    def test_exact_baseline_statuses_and_cents(self):
        for path, account in self.accounts.items():
            baseline = json.loads((REPO / account["baseline"]).read_text())
            self.assertEqual(2, baseline["schemaVersion"])
            self.assertEqual(account["federalAccount"], baseline["federalAccount"])
            self.assertIn("api.usaspending.gov/api/v2/federal_accounts/", baseline["source"])
            years = baseline["fiscalYears"]
            self.assertEqual({str(year) for year in range(2015, 2027)}, set(years))
            for year in ("2015", "2016"):
                self.assertEqual("unavailable", years[year]["status"])
                self.assertTrue(years[year]["reason"])
            self.assertEqual(
                {"status": "partial", "asOfPeriod": 12,
                 "firstPeriod": 6, "obligationsCents": EXPECTED_CENTS[path][0]},
                years["2017"],
            )
            for fiscal_year, cents in zip(range(2018, 2026), EXPECTED_CENTS[path][1:9]):
                self.assertEqual(
                    {"status": "complete", "obligationsCents": cents},
                    years[str(fiscal_year)],
                )
            self.assertEqual(
                {"status": "partial", "asOfPeriod": 9,
                 "obligationsCents": EXPECTED_CENTS[path][9]},
                years["2026"],
            )

    def test_program_activity_tokens_are_unique_and_resolve(self):
        for path, account in self.accounts.items():
            pairs, parks = [], []
            aliases = alias_map(account)
            for activity in account["programActivities"]:
                pairs.append((activity["code"].zfill(4), activity["name"].lower()))
                pairs.extend(
                    (item["code"].zfill(4), item["name"].lower())
                    for item in activity.get("codeNameAliases", [])
                )
                parks.extend(filter(None, [
                    activity.get("park"), *activity.get("parkAliases", [])
                ]))
                rows = [{
                    "federal_account_symbol": account["federalAccount"],
                    "program_activity_code": activity["code"],
                    "program_activity_name": activity["name"].upper(),
                    "obligations_incurred": "1.00",
                }]
                self.assertEqual(100, next(iter(parse_file_b_snapshot(
                    rows, account["federalAccount"], aliases
                ).values())))
                if activity.get("park"):
                    rows = [{
                        "federal_account_symbol": account["federalAccount"],
                        "program_activity_reporting_key": activity["park"],
                        "obligations_incurred": "1.00",
                    }]
                    self.assertEqual(100, next(iter(parse_file_b_snapshot(
                        rows, account["federalAccount"], aliases
                    ).values())))
            self.assertEqual(len(pairs), len(set(pairs)), path)
            self.assertEqual(len(parks), len(set(parks)), path)

    def test_unregistered_program_activity_fails_closed(self):
        for account in self.accounts.values():
            aliases = alias_map(account)
            for row in ({
                "program_activity_code": "9999",
                "program_activity_name": "Unregistered",
            }, {"program_activity_reporting_key": "UNREGISTERED-PARK"}):
                with self.assertRaisesRegex(ValueError, "unmapped Program Activity"):
                    parse_file_b_snapshot([{
                        "federal_account_symbol": account["federalAccount"],
                        "obligations_incurred": "1.00", **row,
                    }], account["federalAccount"], aliases)

    def test_historical_code_name_aliases_resolve(self):
        for account in self.accounts.values():
            aliases = alias_map(account)
            for activity in account["programActivities"]:
                for historical in activity.get("codeNameAliases", []):
                    rows = [{
                        "federal_account_symbol": account["federalAccount"],
                        "program_activity_code": historical["code"],
                        "program_activity_name": historical["name"],
                        "obligations_incurred": "1.00",
                    }]
                    parsed = parse_file_b_snapshot(
                        rows, account["federalAccount"], aliases
                    )
                    self.assertEqual(100, next(iter(parsed.values())))
                    identity_key, code, name, park = next(iter(parsed))[0:4]
                    self.assertEqual(activity["code"].zfill(4), identity_key)
                    self.assertEqual(activity["code"].zfill(4), code)
                    self.assertEqual(activity["name"], name)
                    self.assertEqual(activity.get("park", ""), park)

    def test_stage_plans_have_exact_job_counts_and_periods(self):
        for selector, count in STAGE_SELECTORS.items():
            jobs = plan(REPO, mode="full", selectors=selector)["include"]
            self.assertEqual(count, len(jobs), selector)
            selected = selector.split(",")
            self.assertEqual(set(selected), {job["account"] for job in jobs})
            for path in selected:
                account_jobs = [job for job in jobs if job["account"] == path]
                self.assertEqual(list(range(2017, 2027)), [
                    job["fiscalYear"] for job in account_jobs
                ])
                self.assertEqual(
                    [12] * 9 + [9], [job["period"] for job in account_jobs]
                )


if __name__ == "__main__":
    unittest.main()
