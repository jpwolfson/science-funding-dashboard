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
    "nasa/exploration": ("080-0124", "Exploration"),
    "nasa/space-operations": ("080-0115", "Space Operations"),
}
EXPECTED_IDENTITIES = {
    "nasa/science": [
        ("science-direct", "0001", "Science (Direct)", "5ZD5GGPDU49"),
    ],
    "nasa/aeronautics": [
        ("aeronautics-direct", "0001", "Aeronautics (Direct)", "5ZD5GGPT55B"),
    ],
    "nasa/space-technology": [
        ("space-technology-direct", "0001", "Space Technology (Direct)", "5ZD5GGQ7TN7"),
    ],
    "nasa/stem-engagement": [
        ("education-direct", "0001", "Education (Direct)", "5ZD5GGQ085N"),
    ],
    "nasa/exploration": [
        ("deep-space-exploration-systems", "0001", "Deep Space Exploration Systems", "5RN5AZGZKXF"),
        ("unknown-other", "0000", "Unknown / other", ""),
        (
            "activity-from-obligation-before-fy-2018-program-activity-not-specified",
            "PRE2018",
            "ACTIVITY FROM OBLIGATION BEFORE FY 2018: PROGRAM ACTIVITY NOT SPECIFIED",
            "PRE2018",
        ),
    ],
    "nasa/space-operations": [
        ("space-operations-direct", "0001", "Space Operations (Direct)", "5ZD5GGP15KD"),
        ("space-operations-reimbursable", "0801", "Space Operations (Reimbursable)", ""),
        ("unknown-other", "0000", "Unknown / other", ""),
        (
            "activity-from-obligation-before-fy-2018-program-activity-not-specified",
            "PRE2018",
            "ACTIVITY FROM OBLIGATION BEFORE FY 2018: PROGRAM ACTIVITY NOT SPECIFIED",
            "PRE2018",
        ),
    ],
}
EXPECTED_CODE_NAME_ALIASES = {
    "nasa/stem-engagement": {
        "education-direct": [
            ("0001", "SCIENCE, TECHNOLOGY, ENGINEERING, AND MATHEMATICS ENGAGEMENT (DIRECT)"),
        ],
    },
    "nasa/exploration": {
        "deep-space-exploration-systems": [
            ("0001", "EXPLORATION (DIRECT)"),
            ("0001", "DEEP SPACE EXPLORATION SYSTEMS (DIRECT)"),
        ],
        "unknown-other": [("0000", "UNKNOWN/OTHER")],
    },
    "nasa/space-operations": {
        "unknown-other": [
            ("0000", "0"),
            ("0000", "OTHER/UNKNOWN"),
            ("0000", "UNKNOWN/OTHER"),
        ],
    },
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
    "nasa/exploration": [
        431912621327, 448394604078, 531578518020, 599850295094,
        659116058115, 688314506847, 762268175145, 782735099075,
        792386697438, 579775944800,
    ],
    "nasa/space-operations": [
        500236863132, 478526162989, 479202003631, 436087332797,
        392629207884, 415856980781, 454586690568, 433838713167,
        498761927454, 239842355296,
    ],
}
STAGE_SELECTORS = {
    "nasa/science": 10,
    "nasa/aeronautics,nasa/space-technology,nasa/stem-engagement": 30,
    "nasa/exploration,nasa/space-operations": 20,
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
        self.assertEqual(EXPECTED_IDENTITIES, {
            path: [
                (activity["slug"], activity["code"], activity["name"],
                 activity.get("park", ""))
                for activity in account["programActivities"]
            ]
            for path, account in self.accounts.items()
        })
        self.assertEqual(11, sum(map(len, EXPECTED_IDENTITIES.values())))
        self.assertEqual(EXPECTED_CODE_NAME_ALIASES, {
            path: {
                activity["slug"]: [
                    (alias["code"], alias["name"])
                    for alias in activity.get("codeNameAliases", [])
                ]
                for activity in account["programActivities"]
                if activity.get("codeNameAliases")
            }
            for path, account in self.accounts.items()
            if any(
                activity.get("codeNameAliases")
                for activity in account["programActivities"]
            )
        })

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

    def test_space_operations_identities_remain_distinct(self):
        account = self.accounts["nasa/space-operations"]
        rows = [{
            "federal_account_symbol": account["federalAccount"],
            "program_activity_code": code,
            "program_activity_name": name,
            "obligations_incurred": "1.00",
        } for code, name in (
            ("0001", "SPACE OPERATIONS (DIRECT)"),
            ("0801", "SPACE OPERATIONS (REIMBURSABLE)"),
            ("0000", "UNKNOWN/OTHER"),
        )]
        parsed = parse_file_b_snapshot(
            rows, account["federalAccount"], alias_map(account)
        )
        self.assertEqual({"0000", "0001", "0801"}, {
            key[0] for key in parsed
        })

    def test_exploration_fy2026_pre2018_sentinel_is_distinct(self):
        account = self.accounts["nasa/exploration"]
        rows = [
            {
                "federal_account_symbol": "080-0124",
                "program_activity_reporting_key": "5RN5AZGZKXF",
                "obligations_incurred": "1139741650.42",
            },
            {
                "federal_account_symbol": "080-0124",
                "program_activity_reporting_key": "PRE2018",
                "obligations_incurred": "0.00",
            },
        ]
        parsed = parse_file_b_snapshot(rows, "080-0124", alias_map(account))
        self.assertEqual(113_974_165_042, sum(parsed.values()))
        self.assertEqual({"5RN5AZGZKXF", "PRE2018"}, {
            key[3] for key in parsed
        })
        self.assertEqual({
            "Deep Space Exploration Systems",
            "ACTIVITY FROM OBLIGATION BEFORE FY 2018: PROGRAM ACTIVITY NOT SPECIFIED",
        }, {key[2] for key in parsed})

    def test_space_operations_fy2026_park_transition_and_pre2018(self):
        account = self.accounts["nasa/space-operations"]
        aliases = alias_map(account)
        self.assertEqual(
            aliases[("park", "5ZD5GGP15KD")]["slug"],
            aliases[("park", "5Q15DKKYF0L")]["slug"],
        )
        rows = [
            {
                "federal_account_symbol": "080-0115",
                "program_activity_reporting_key": "5Q15DKKYF0L",
                "obligations_incurred": "0.00",
            },
            {
                "federal_account_symbol": "080-0115",
                "program_activity_reporting_key": "5ZD5GGP15KD",
                "obligations_incurred": "216336753.88",
            },
            {
                "federal_account_symbol": "080-0115",
                "program_activity_reporting_key": "PRE2018",
                "obligations_incurred": "0.00",
            },
        ]
        parsed = parse_file_b_snapshot(rows, "080-0115", aliases)
        self.assertEqual(21_633_675_388, sum(parsed.values()))
        self.assertEqual(2, len(parsed))
        self.assertEqual({
            "Space Operations (Direct)",
            "ACTIVITY FROM OBLIGATION BEFORE FY 2018: PROGRAM ACTIVITY NOT SPECIFIED",
        }, {key[2] for key in parsed})

    def test_aaas_budget_lines_are_not_program_activity_slugs(self):
        slugs = {
            activity["slug"]
            for account in self.accounts.values()
            for activity in account["programActivities"]
        }
        self.assertTrue(slugs.isdisjoint({
            "astrophysics", "earth-science", "heliophysics",
            "planetary-science", "bio-physical-sciences", "sls", "orion",
            "gateway", "mars-exploration", "mars-sample-return",
        }))

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
