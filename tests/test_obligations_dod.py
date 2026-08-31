import json
import unittest
from pathlib import Path

from adapters.usaspending_obligations import alias_map
from scripts.plan_obligation_refresh import plan


REPO = Path(__file__).resolve().parent.parent

NAVY_FY2025_FILE_B_CENTS = 2_788_488_646_275
NAVY_FY2025_VARIANCE_CENTS = 46_929_636
NAVY_FY2025_VARIANCE_REASON = (
    "Official FY2025 GTAS/File A is 2788535575911 cents while the accepted "
    "P12 File B and independent date-filtered Program Activity totals are "
    "2788488646275 cents; preserve the exact 46929636-cent official source "
    "variance with File B canonical and no synthetic residual or tolerance."
)

ACCOUNT_META = {
    "dod/army-rdte": {
        "federalAccount": "021-2040",
        "name": "Research, Development, Test and Evaluation, Army",
        "baseline": "reference/dod_army_rdte_obligation_baseline.json",
        "programActivities": 12,
        "pins": [
            1335551508911, 1658237560606, 1941282900467,
            2944022806618, 5649553107182, 5252715920406,
            2826746057722, 2462016948008, 2432841622809,
            1899886149032,
        ],
    },
    "dod/navy-rdte": {
        "federalAccount": "017-1319",
        "name": "Research, Development, Test, and Evaluation, Navy",
        "baseline": "reference/dod_navy_rdte_obligation_baseline.json",
        "programActivities": 12,
        "pins": [
            1815670608261, 1906604818960, 1989612897412,
            2110379803523, 2104077406079, 2211161457342,
            2645738486155, 2956285398710, 2788535575911,
            2552546450852,
        ],
    },
}

STAGE_TWO_META = {
    "dod/air-force-rdte": {
        "federalAccount": "057-3600",
        "name": "Research, Development, Test, and Evaluation, Air Force",
        "baseline": "reference/dod_air_force_rdte_obligation_baseline.json",
        "programActivities": 13,
        "availability": {
            "firstFiscalYear": 2017,
            "firstFiscalYearPeriod": 6,
            "regularFirstPeriod": 2,
        },
        "pins": [
            3039261892426, 3946023359082, 4926097145714,
            4966143569342, 4189223395703, 4358980604532,
            5046972337780, 5092889515726, 5587181366148,
            4748612733074,
        ],
    },
    "dod/space-force-rdte": {
        "federalAccount": "057-3620",
        "name": "Research, Development, Test, and Evaluation, Space Force, Air Force",
        "baseline": "reference/dod_space_force_rdte_obligation_baseline.json",
        "programActivities": 11,
        "availability": {
            "firstFiscalYear": 2021,
            "firstFiscalYearPeriod": 2,
            "regularFirstPeriod": 2,
        },
        "pins": [
            1052753427202, 1255327250863, 1790303171627,
            2036070402666, 2004458733008, 1740110018139,
        ],
    },
}


class DoDObligationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        registry = json.loads(
            (REPO / "config" / "obligation_accounts.json").read_text()
        )
        cls.accounts = {
            row["path"]: row for row in registry["accounts"]
            if row["path"] in ACCOUNT_META
        }
        cls.stage_two_accounts = {
            row["path"]: row for row in registry["accounts"]
            if row["path"] in STAGE_TWO_META
        }

    def test_stage_one_has_exact_account_contracts(self):
        self.assertEqual(set(ACCOUNT_META), set(self.accounts))
        for path, expected in ACCOUNT_META.items():
            with self.subTest(path=path):
                account = self.accounts[path]
                self.assertEqual(expected["federalAccount"], account["federalAccount"])
                self.assertEqual(expected["name"], account["name"])
                self.assertEqual("Department of Defense", account["agency"])
                self.assertEqual("usaspending_obligations", account["adapter"])
                self.assertEqual(expected["baseline"], account["baseline"])
                self.assertEqual(expected["programActivities"],
                                 len(account["programActivities"]))
                self.assertEqual({
                    "firstFiscalYear": 2017,
                    "firstFiscalYearPeriod": 6,
                    "regularFirstPeriod": 2,
                }, account["availability"])

    def test_stage_one_aliases_are_collision_free(self):
        for path, account in self.accounts.items():
            with self.subTest(path=path):
                aliases = alias_map(account)
                self.assertTrue(aliases)
                self.assertEqual(len(aliases), len(set(aliases)))

        army_aliases = alias_map(self.accounts["dod/army-rdte"])
        operational = army_aliases[
            ("code-name", "0007", "operational systems development")
        ]
        self.assertEqual("0007", operational["code"])
        self.assertEqual("Operational System Development", operational["name"])
        system_development = army_aliases[
            ("code-name", "0005",
             "system development & demonstration ($dd)")
        ]
        self.assertEqual("0005", system_development["code"])
        self.assertEqual(
            "System Development and Demonstration",
            system_development["name"],
        )
        for code, name in [
            ("0002", "n/a"),
            ("0006", "n/a"),
            ("0050", "n/a"),
            ("OPTN", "field is optional prior to fy21"),
        ]:
            with self.subTest(code=code, name=name):
                unknown = army_aliases[("code-name", code, name)]
                self.assertEqual("0000", unknown["code"])
                self.assertEqual("Unknown / other", unknown["name"])

        navy_aliases = alias_map(self.accounts["dod/navy-rdte"])
        navy_unknown = navy_aliases[
            ("code-name", "OPTN", "field is optional prior to fy21")
        ]
        self.assertEqual("0000", navy_unknown["code"])
        self.assertEqual("Unknown / other", navy_unknown["name"])
        navy_pre2018 = navy_aliases[("park", "PRE2018")]
        self.assertEqual("PRE2018", navy_pre2018["code"])
        self.assertEqual(
            "ACTIVITY FROM OBLIGATION BEFORE FY 2018: "
            "PROGRAM ACTIVITY NOT SPECIFIED",
            navy_pre2018["name"],
        )

    def test_stage_one_preserves_exact_file_a_pins(self):
        for path, expected in ACCOUNT_META.items():
            with self.subTest(path=path):
                baseline = json.loads((REPO / expected["baseline"]).read_text())
                self.assertEqual(2, baseline["schemaVersion"])
                self.assertEqual(expected["federalAccount"],
                                 baseline["federalAccount"])
                self.assertIn("api.usaspending.gov/api/v2/federal_accounts/",
                              baseline["source"])
                years = baseline["fiscalYears"]
                self.assertEqual({str(fy) for fy in range(2015, 2027)}, set(years))
                for fy in (2015, 2016):
                    self.assertEqual("unavailable", years[str(fy)]["status"])
                self.assertEqual(6, years["2017"]["firstPeriod"])
                self.assertEqual(12, years["2017"]["asOfPeriod"])
                self.assertEqual(9, years["2026"]["asOfPeriod"])
                observed = [years[str(fy)]["obligationsCents"]
                            for fy in range(2017, 2027)]
                self.assertEqual(expected["pins"], observed)

    def test_navy_fy2025_preserves_approved_exact_source_variance(self):
        baseline = json.loads(
            (REPO / "reference/dod_navy_rdte_obligation_baseline.json").read_text()
        )
        self.assertEqual({
            "status": "complete",
            "obligationsCents": 2_788_535_575_911,
            "fileBObligationsCents": NAVY_FY2025_FILE_B_CENTS,
            "fileAFileBVarianceCents": NAVY_FY2025_VARIANCE_CENTS,
            "fileAFileBVarianceReason": NAVY_FY2025_VARIANCE_REASON,
        }, baseline["fiscalYears"]["2025"])

    def test_stage_one_custom_plan_is_exactly_twenty_serial_partitions(self):
        matrix = plan(
            repo=REPO,
            mode="custom",
            selectors="dod/army-rdte,dod/navy-rdte",
            from_fy=2017,
            to_fy=2026,
            current_period=9,
        )["include"]
        self.assertEqual(20, len(matrix))
        self.assertEqual(set(ACCOUNT_META), {row["account"] for row in matrix})
        for path in ACCOUNT_META:
            rows = [row for row in matrix if row["account"] == path]
            self.assertEqual(list(range(2017, 2027)),
                             [row["fiscalYear"] for row in rows])
            self.assertEqual([12] * 9 + [9], [row["period"] for row in rows])

    def test_public_semantics_keep_file_b_canonical(self):
        handoff = (REPO / "docs" / "phase-3.2d-dod-handoff.md").read_text()
        self.assertIn("File B account obligations are canonical", handoff)
        self.assertIn("not evidence of missing account dollars", handoff)
        self.assertNotIn("completeness percentage", handoff.lower())

    def test_stage_two_has_exact_account_contracts(self):
        self.assertEqual(set(STAGE_TWO_META), set(self.stage_two_accounts))
        for path, expected in STAGE_TWO_META.items():
            with self.subTest(path=path):
                account = self.stage_two_accounts[path]
                self.assertEqual(expected["federalAccount"],
                                 account["federalAccount"])
                self.assertEqual(expected["name"], account["name"])
                self.assertEqual("Department of Defense", account["agency"])
                self.assertEqual("057", account["agencyIdentifier"])
                self.assertEqual("usaspending_obligations", account["adapter"])
                self.assertEqual(expected["baseline"], account["baseline"])
                self.assertEqual(expected["programActivities"],
                                 len(account["programActivities"]))
                self.assertEqual(expected["availability"],
                                 account["availability"])

    def test_stage_two_aliases_cover_reviewed_inventory_without_collisions(self):
        for path, account in self.stage_two_accounts.items():
            with self.subTest(path=path):
                aliases = alias_map(account)
                self.assertTrue(aliases)
                self.assertEqual(len(aliases), len(set(aliases)))

        air_force = alias_map(self.stage_two_accounts["dod/air-force-rdte"])
        self.assertEqual(
            "operational-system-development",
            air_force[("code-name", "0007", "operational system development")][
                "slug"
            ],
        )
        self.assertEqual(
            "rdte-air-force-five-year",
            air_force[(
                "code-name", "0007",
                "research development test and evaluation air force (5 year)",
            )]["slug"],
        )
        self.assertEqual(
            "unidentified",
            air_force[("code-name", "00ZX", "unidentified")]["slug"],
        )
        self.assertEqual(
            "software-digital-pilot-program",
            air_force[(
                "code-name", "NASO", "ftware and digital pilot program",
            )]["slug"],
        )
        for code in ("0000", "0001", "0004", "0006", "0007", "0020", "00ZX"):
            with self.subTest(account="air-force", code=code):
                self.assertEqual(
                    "unknown-other",
                    air_force[("code-name", code, "n/a")]["slug"],
                )
        self.assertEqual(
            "unknown-other",
            air_force[(
                "code-name", "OPTN", "field is optional prior to fy21",
            )]["slug"],
        )
        for park in (
            "5ZC3NP008BB", "5ZC3NP008BC", "5ZC3NP008BD",
            "5ZC3NP008BE", "5ZC3NP008BF", "5ZC3NP008BG",
            "5ZC3NP008BH", "5ZC3NP008BU", "5ZC3NP0090T",
        ):
            self.assertIn(("park", park), air_force)

        space_force = alias_map(self.stage_two_accounts["dod/space-force-rdte"])
        self.assertEqual(
            space_force[("park", "5UW3C6HY83T")]["slug"],
            space_force[("park", "63Y30LXJBQR")]["slug"],
        )
        self.assertEqual(
            "software-digital-technology-pilots",
            space_force[(
                "code-name", "0008",
                "software & digital technology pilot program",
            )]["slug"],
        )
        self.assertEqual(
            "advanced-technology-development",
            space_force[(
                "code-name", "NAAD", "vanced technology development",
            )]["slug"],
        )
        self.assertEqual(
            "reimbursable",
            space_force[(
                "code-name", "00RB", "reimbursable program",
            )]["slug"],
        )
        self.assertEqual(
            "reimbursable",
            space_force[(
                "code-name", "NARE", "imbursable program",
            )]["slug"],
        )
        for code in ("0004", "0006", "0008"):
            with self.subTest(account="space-force", code=code):
                self.assertEqual(
                    "unknown-other",
                    space_force[("code-name", code, "n/a")]["slug"],
                )
        self.assertEqual(
            "unknown-other",
            space_force[("code-name", "0099", "n/a")]["slug"],
        )
        for park in (
            "60836E8YQW9", "5TA3F2M0WNK", "5UW3C6HY83T",
            "63Y30LXJBQR", "5TA3F2M0WNM", "5TA3F2M0WNN",
            "5TA3F2M0WNZ", "5TA3F2M0WNP", "5TA3F2M0WNQ",
            "5WK39AD1HYK", "5TA3F2M0XD3",
        ):
            self.assertIn(("park", park), space_force)

    def test_stage_two_preserves_exact_file_a_pins(self):
        for path, expected in STAGE_TWO_META.items():
            with self.subTest(path=path):
                baseline = json.loads((REPO / expected["baseline"]).read_text())
                self.assertEqual(2, baseline["schemaVersion"])
                self.assertEqual(expected["federalAccount"],
                                 baseline["federalAccount"])
                self.assertIn("api.usaspending.gov/api/v2/federal_accounts/",
                              baseline["source"])
                years = baseline["fiscalYears"]
                self.assertEqual({str(fy) for fy in range(2015, 2027)}, set(years))
                first_fy = expected["availability"]["firstFiscalYear"]
                for fy in range(2015, first_fy):
                    self.assertEqual("unavailable", years[str(fy)]["status"])
                self.assertEqual(9, years["2026"]["asOfPeriod"])
                observed = [
                    years[str(fy)]["obligationsCents"]
                    for fy in range(first_fy, 2027)
                ]
                self.assertEqual(expected["pins"], observed)

    def test_stage_two_full_plan_is_exactly_sixteen_serial_partitions(self):
        matrix = plan(
            repo=REPO,
            mode="full",
            selectors="dod/air-force-rdte,dod/space-force-rdte",
        )["include"]
        self.assertEqual(16, len(matrix))
        self.assertEqual(set(STAGE_TWO_META), {row["account"] for row in matrix})
        air_force = [row for row in matrix
                     if row["account"] == "dod/air-force-rdte"]
        space_force = [row for row in matrix
                       if row["account"] == "dod/space-force-rdte"]
        self.assertEqual(list(range(2017, 2027)),
                         [row["fiscalYear"] for row in air_force])
        self.assertEqual([12] * 9 + [9], [row["period"] for row in air_force])
        self.assertEqual(list(range(2021, 2027)),
                         [row["fiscalYear"] for row in space_force])
        self.assertEqual([12] * 5 + [9], [row["period"] for row in space_force])


if __name__ == "__main__":
    unittest.main()
