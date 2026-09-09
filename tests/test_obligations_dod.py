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

DHP_FY2025_FILE_B_CENTS = 4_676_524_125_773
DHP_FY2025_VARIANCE_CENTS = 15_545_187_780
DHP_FY2025_VARIANCE_REASON = (
    "Official FY2025 GTAS/File A is 4692069313553 cents while the accepted "
    "P12 File B and independent date-filtered Program Activity totals are "
    "4676524125773 cents; preserve the exact 15545187780-cent official source "
    "variance with File B canonical and no synthetic residual or tolerance."
)

DEFENSE_WIDE_FY2023_FILE_B_CENTS = 3_507_738_877_251
DEFENSE_WIDE_FY2023_VARIANCE_CENTS = 100_858
DEFENSE_WIDE_FY2023_VARIANCE_REASON = (
    "Official FY2023 GTAS/File A is 3507738978109 cents while the accepted "
    "P12 File B and independent date-filtered Program Activity totals are "
    "3507738877251 cents; preserve the exact 100858-cent official source "
    "variance with File B canonical and no synthetic residual or tolerance."
)

DEFENSE_WIDE_FY2025_FILE_B_CENTS = 3_812_362_307_540
DEFENSE_WIDE_FY2025_VARIANCE_CENTS = 1_283_575_232
DEFENSE_WIDE_FY2025_VARIANCE_REASON = (
    "Official FY2025 GTAS/File A is 3813645882772 cents while the accepted "
    "P12 File B and independent date-filtered Program Activity totals are "
    "3812362307540 cents; preserve the exact 1283575232-cent official source "
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

STAGE_THREE_META = {
    "dod/defense-wide-rdte": {
        "federalAccount": "097-0400",
        "name": "Research, Development, Test, and Evaluation, Defense-Wide",
        "baseline": "reference/dod_defense_wide_rdte_obligation_baseline.json",
        "programActivities": 17,
        "historicalPins": [
            2251362677352, 2457216636704, 2645819709252,
            2710538880746, 2875140199888, 2943303100353,
            3507738978109, 3845905263059, 3813645882772,
        ],
    },
    "dod/defense-health-program": {
        "federalAccount": "097-0130",
        "name": "Defense Health Program, Defense",
        "baseline": "reference/dod_defense_health_program_obligation_baseline.json",
        "programActivities": 16,
        "historicalPins": [
            3735497424800, 3815667849023, 3945894755468,
            4144696246716, 4047318547619, 4178537884292,
            4401952664476, 4571628570276, 4692069313553,
        ],
    },
}

STAGE_THREE_REVIEWED_INVENTORY = {
    "dod/defense-wide-rdte": {
        "parks": {
            "PRE2018", "5ZC3NHWYKE5", "5ZC3NHWYJZZ", "5ZC3NHWYJZR",
            "5ZC3NHWYJZQ", "5ZC3NHWYJZP", "5ZC3NHWYJZN",
            "5ZC3NHWYJZM", "5ZC3NHWYJZL", "5ZC3NHWYJP6",
            "5TA3ETJ2DXY",
        },
        "code_names": {
            ("0801", "REIMBURSABLE"), ("00ZZ", "N/A"),
            ("00ZZ", "UNDISTRIBUTED"), ("00ZX", "UNIDENTIFIED"),
            ("00RB", "REIMBURSABLE PROGRAM"),
            ("00CA", "CLOSED ACCOUNT"),
            ("00CA", "CLOSED ACCOUNT ADJUSTMENT"), ("00CA", "N/A"),
            ("NAMI", "SCELLANEOUS"),
            ("009S", "MISCELLANEOUS"), ("0099", "N/A"),
            ("0099", "OPERATIONAL SYSTEMS DEVELOPMENT"), ("0090", "N/A"),
            ("0070", "N/A"), ("0030", "N/A"), ("0020", "N/A"),
            ("0020", "UNDISTRIBUTED"), ("0012", "N/A"),
            ("0009", "N/A"), ("0009", "RECERT OR LIMITED LIAB"),
            ("0008", "N/A"),
            ("0007", "ADVANCED COMPONENT DEVELOPMENT AND PROTOTYPES"),
            ("0007", "N/A"), ("0007", "OPERATIONAL SYSTEM DEVELOPMENT"),
            ("0006", "MANAGEMENT SUPPORT"),
            ("0005", "SYSTEM DEVELOPMENT AND DEMONSTRATION"),
            ("0004", "ADVANCED COMPONENT DEVELOPMENT AND PROTOTYPES"),
            ("0004", "DOD/VA INCENTIVE FUND"), ("0004", "N/A"),
            ("0003", "ADVANCED TECHNOLOGY DEVELOPMENT"), ("0003", "N/A"),
            ("0002", "APPLIED RESEARCH"), ("0002", "N/A"),
            ("0001", "BASIC RESEARCH"),
            ("0000", "BUDGET ACTIVITY NOT APPLICABLE"),
            ("0000", "MANAGEMENT SUPPORT"), ("0000", "N/A"),
            ("0000", "UNKNOWN/OTHER"), ("0000", "UNSPECIFIED"),
            ("OPTN", "FIELD IS OPTIONAL PRIOR TO FY21"),
        },
    },
    "dod/defense-health-program": {
        "parks": {
            "PRE2018", "5ZC3H196KXF", "5ZC3H196KAG", "5ZC3H196K9X",
            "5ZC3H196K9W", "5ZC3H196K9V", "5Q03E54NTZ6",
        },
        "code_names": {
            ("0801", "REIMBURSABLE"), ("00ZZ", "UNDISTRIBUTED"),
            ("00ZX", "N/A"), ("00ZX", "UNIDENTIFIED"), ("00Z9", "N/A"),
            ("00RB", "REIMBURSABLE PROGRAM"),
            ("NARE", "IMBURSABLE PROGRAM"), ("00B8", "N/A"),
            ("0099", "N/A"), ("0020", "N/A"),
            ("0020", "UNKNOWN/OTHER"),
            ("0020", "UNDISTRIBUTED"), ("0009", "N/A"),
            ("0006", "N/A"),
            ("0004", "ADMINISTRATION AND SERVICE-WIDE ACTIVITIES"),
            ("0004", "N/A"), ("0003", "N/A"), ("0003", "PROCUREMENT"),
            ("0003", "RDT&E"), ("0002", "3 YR RDT&E"),
            ("008B", "DEFENSE HEALTH PROGRAM"),
            ("0002", "APPLIED RESEARCH"), ("0002", "N/A"),
            ("0002", "RDT&E"),
            ("0002", "RESEARCH DEVELOPMENT TEST AND EVALUATION"),
            ("0002", "RESEARCH  DEVELOPMENT  TEST  & EVALUATION"),
            ("0002", "RESEARCH  DEVELOPMENT  TEST &  EVALUATION"),
            ("0002", "RESEARCH DEVELOPMENT TEST    & EVALUATION"),
            ("0002", "RESEARCH DEVELOPMENT TEST & EVALUATION"),
            ("0002", "RESEARCH DEVELOPMENTTESTEVALUATION"),
            ("0002", "RESEARCH, DEVELOPMENT, TEST, & EVALUATION"),
            ("0001", "BASIC RESEARCH"), ("0001", "MAJOR EQUIPMENT"),
            ("0001", "N/A"), ("0001", "OPERATING FORCES"),
            ("0001", "OPERATION AND MAINTENANCE"),
            ("0001", "OPERATION & MAINTENANCE"), ("0001", "PROCUREMENT"),
            ("0001", "REIMBURSABLE PROGRAM"),
            ("0000", "BUDGET ACTIVITY NOT APPLICABLE"),
            ("0000", "GFEBS UNDISTRIBUTED"), ("0000", "NA"),
            ("0000", "N/A"), ("0000", "UNKNOWN/OTHER"),
            ("0000", "USUHS"),
            ("OPTN", "FIELD IS OPTIONAL PRIOR TO FY21"),
        },
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
        cls.stage_three_accounts = {
            row["path"]: row for row in registry["accounts"]
            if row["path"] in STAGE_THREE_META
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

    def test_stage_three_preserves_approved_exact_source_variances(self):
        cases = {
            "reference/dod_defense_health_program_obligation_baseline.json": {
                "fiscalYear": "2025",
                "fileA": 4_692_069_313_553,
                "fileB": DHP_FY2025_FILE_B_CENTS,
                "variance": DHP_FY2025_VARIANCE_CENTS,
                "reason": DHP_FY2025_VARIANCE_REASON,
            },
            "reference/dod_defense_wide_rdte_obligation_baseline.json": {
                "fiscalYear": "2023",
                "fileA": 3_507_738_978_109,
                "fileB": DEFENSE_WIDE_FY2023_FILE_B_CENTS,
                "variance": DEFENSE_WIDE_FY2023_VARIANCE_CENTS,
                "reason": DEFENSE_WIDE_FY2023_VARIANCE_REASON,
            },
            "reference/dod_defense_wide_rdte_obligation_baseline.json#FY2025": {
                "baseline": "reference/dod_defense_wide_rdte_obligation_baseline.json",
                "fiscalYear": "2025",
                "fileA": 3_813_645_882_772,
                "fileB": DEFENSE_WIDE_FY2025_FILE_B_CENTS,
                "variance": DEFENSE_WIDE_FY2025_VARIANCE_CENTS,
                "reason": DEFENSE_WIDE_FY2025_VARIANCE_REASON,
            },
        }
        for path, expected in cases.items():
            with self.subTest(path=path):
                baseline_path = expected.get("baseline", path)
                baseline = json.loads((REPO / baseline_path).read_text())
                row = baseline["fiscalYears"][expected["fiscalYear"]]
                self.assertEqual({
                    "status": "complete",
                    "obligationsCents": expected["fileA"],
                    "fileBObligationsCents": expected["fileB"],
                    "fileAFileBVarianceCents": expected["variance"],
                    "fileAFileBVarianceReason": expected["reason"],
                }, row)

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

    def test_stage_three_has_exact_account_contracts(self):
        self.assertEqual(set(STAGE_THREE_META), set(self.stage_three_accounts))
        for path, expected in STAGE_THREE_META.items():
            with self.subTest(path=path):
                account = self.stage_three_accounts[path]
                self.assertEqual(expected["federalAccount"],
                                 account["federalAccount"])
                self.assertEqual(expected["name"], account["name"])
                self.assertEqual("Department of Defense", account["agency"])
                self.assertEqual("097", account["agencyIdentifier"])
                self.assertEqual("usaspending_obligations", account["adapter"])
                self.assertEqual(expected["baseline"], account["baseline"])
                self.assertEqual(expected["programActivities"],
                                 len(account["programActivities"]))
                self.assertEqual({
                    "firstFiscalYear": 2017,
                    "firstFiscalYearPeriod": 6,
                    "regularFirstPeriod": 2,
                }, account["availability"])

    def test_stage_three_reviewed_inventories_resolve_without_collisions(self):
        for path, reviewed in STAGE_THREE_REVIEWED_INVENTORY.items():
            with self.subTest(path=path):
                aliases = alias_map(self.stage_three_accounts[path])
                self.assertTrue(aliases)
                self.assertEqual(len(aliases), len(set(aliases)))
                for park in reviewed["parks"]:
                    self.assertIn(("park", park), aliases)
                for code, name in reviewed["code_names"]:
                    self.assertIn(
                        ("code-name", code.zfill(4), name.strip().lower()),
                        aliases,
                    )

        defense_wide = alias_map(
            self.stage_three_accounts["dod/defense-wide-rdte"]
        )
        self.assertEqual(
            "advanced-component-development-prototypes",
            defense_wide[(
                "code-name", "0007",
                "advanced component development and prototypes",
            )]["slug"],
        )
        self.assertEqual(
            "operational-system-development",
            defense_wide[(
                "code-name", "0007", "operational system development",
            )]["slug"],
        )
        self.assertEqual(
            "dod-va-incentive-fund",
            defense_wide[(
                "code-name", "0004", "dod/va incentive fund",
            )]["slug"],
        )
        self.assertEqual(
            "unknown-other",
            defense_wide[("code-name", "0004", "n/a")]["slug"],
        )
        self.assertEqual(
            "closed-account-adjustment",
            defense_wide[("code-name", "00CA", "closed account")]["slug"],
        )
        self.assertEqual(
            "miscellaneous",
            defense_wide[("code-name", "NAMI", "scellaneous")]["slug"],
        )
        self.assertEqual(
            "unknown-other",
            defense_wide[(
                "code-name", "OPTN", "field is optional prior to fy21",
            )]["slug"],
        )
        self.assertEqual(
            "unknown-other",
            defense_wide[("code-name", "0030", "n/a")]["slug"],
        )

        dhp = alias_map(self.stage_three_accounts["dod/defense-health-program"])
        self.assertEqual(
            "operation-maintenance",
            dhp[("code-name", "0001", "operation and maintenance")]["slug"],
        )
        self.assertEqual(
            "procurement",
            dhp[("code-name", "0001", "procurement")]["slug"],
        )
        self.assertEqual(
            "research-development-test-evaluation",
            dhp[("code-name", "0002", "rdt&e")]["slug"],
        )
        self.assertEqual(
            "research-development-test-evaluation",
            dhp[(
                "code-name", "0002", "research developmenttestevaluation",
            )]["slug"],
        )
        self.assertEqual(
            "research-development-test-evaluation",
            dhp[(
                "code-name", "0002",
                "research, development, test, & evaluation",
            )]["slug"],
        )
        self.assertEqual(
            "research-development-test-evaluation",
            dhp[(
                "code-name", "0002",
                "research  development  test &  evaluation",
            )]["slug"],
        )
        self.assertEqual(
            "applied-research",
            dhp[("code-name", "0002", "applied research")]["slug"],
        )
        self.assertEqual(
            "reimbursable",
            dhp[("code-name", "NARE", "imbursable program")]["slug"],
        )
        self.assertEqual(
            "unknown-other",
            dhp[(
                "code-name", "OPTN", "field is optional prior to fy21",
            )]["slug"],
        )
        self.assertEqual(
            "unknown-other",
            dhp[("code-name", "0020", "unknown/other")]["slug"],
        )
        self.assertEqual(
            "defense-health-program",
            dhp[("code-name", "008B", "defense health program")]["slug"],
        )
        self.assertEqual(
            "source-label-unavailable-5q03e54ntz6",
            dhp[("park", "5Q03E54NTZ6")]["slug"],
        )

    def test_stage_three_preserves_exact_file_a_pins(self):
        for path, expected in STAGE_THREE_META.items():
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
                self.assertEqual("partial", years["2017"]["status"])
                self.assertEqual(6, years["2017"]["firstPeriod"])
                self.assertEqual(12, years["2017"]["asOfPeriod"])
                for fy in range(2018, 2026):
                    self.assertEqual("complete", years[str(fy)]["status"])
                observed = [years[str(fy)]["obligationsCents"]
                            for fy in range(2017, 2026)]
                self.assertEqual(expected["historicalPins"], observed)

                # The current year is source-refreshable rather than frozen
                # to the scaffold-time amount. Reconciliation replaces this
                # partial pin from the accepted P09 artifact while completed
                # years above remain immutable.
                current = years["2026"]
                self.assertEqual("partial", current["status"])
                self.assertEqual(9, current["asOfPeriod"])
                self.assertIs(type(current["obligationsCents"]), int)
                self.assertGreaterEqual(current["obligationsCents"], 0)

    def test_stage_three_full_plan_is_exactly_twenty_serial_partitions(self):
        matrix = plan(
            repo=REPO,
            mode="full",
            selectors="dod/defense-wide-rdte,dod/defense-health-program",
        )["include"]
        self.assertEqual(20, len(matrix))
        self.assertEqual(set(STAGE_THREE_META), {row["account"] for row in matrix})
        for path in STAGE_THREE_META:
            rows = [row for row in matrix if row["account"] == path]
            self.assertEqual(list(range(2017, 2027)),
                             [row["fiscalYear"] for row in rows])
            self.assertEqual([12] * 9 + [9], [row["period"] for row in rows])

    def test_darpa_is_included_without_relabeling_defense_wide(self):
        handoff = (REPO / "docs" / "phase-3.2d-dod-handoff.md").read_text()
        normalized = " ".join(handoff.split())
        self.assertIn(
            "DARPA is included within Defense-Wide RDT&E (`097-0400`)",
            normalized,
        )
        self.assertIn("not a standalone account total", normalized)
        self.assertIn("must not be labeled as DARPA", normalized)


if __name__ == "__main__":
    unittest.main()
