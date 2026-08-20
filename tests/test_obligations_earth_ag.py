import json
import unittest
from pathlib import Path

from adapters.usaspending_obligations import (
    alias_map,
    combine_file_b_file_c,
    file_b_period_events,
    parse_file_b_snapshot,
)
from scripts.plan_obligation_refresh import plan


ROOT = Path(__file__).resolve().parent.parent

EXPECTED = {
    "014-0804": (
        "doi/usgs-sir", "Surveys, Investigations and Research", "USGS SIR",
        "Department of the Interior", 14,
        "reference/usgs_sir_obligation_baseline.json",
    ),
    "068-0107": (
        "epa/science-technology", "Science and Technology", "EPA S&T",
        "Environmental Protection Agency", 70,
        "reference/epa_science_technology_obligation_baseline.json",
    ),
    "012-1400": (
        "usda/ars-salaries-expenses",
        "Salaries and Expenses, Agricultural Research Service", "ARS S&E",
        "Department of Agriculture", 19,
        "reference/usda_ars_salaries_expenses_obligation_baseline.json",
    ),
    "012-1401": (
        "usda/ars-buildings-facilities",
        "Buildings and Facilities, Agricultural Research Service", "ARS B&F",
        "Department of Agriculture", 2,
        "reference/usda_ars_buildings_facilities_obligation_baseline.json",
    ),
    "012-1104": (
        "usda/forest-rangeland-research",
        "Forest and Rangeland Research, Forest Service", "FS FRR",
        "Department of Agriculture", 7,
        "reference/usda_forest_rangeland_research_obligation_baseline.json",
    ),
    "012-0502": (
        "usda/nifa-extension",
        "Extension Activities, National Institute of Food and Agriculture",
        "NIFA Extension", "Department of Agriculture", 33,
        "reference/usda_nifa_extension_obligation_baseline.json",
    ),
    "012-1500": (
        "usda/nifa-research-education",
        "Research and Education Activities, National Institute of Food and Agriculture",
        "NIFA R&E", "Department of Agriculture", 33,
        "reference/usda_nifa_research_education_obligation_baseline.json",
    ),
    "012-1502": (
        "usda/nifa-integrated-activities",
        "Integrated Activities, National Institute of Food and Agriculture",
        "NIFA Integrated", "Department of Agriculture", 20,
        "reference/usda_nifa_integrated_activities_obligation_baseline.json",
    ),
    "012-1701": (
        "usda/ers", "Economic Research Service", "ERS",
        "Department of Agriculture", 5,
        "reference/usda_ers_obligation_baseline.json",
    ),
    "012-1801": (
        "usda/nass", "National Agricultural Statistics Service", "NASS",
        "Department of Agriculture", 7,
        "reference/usda_nass_obligation_baseline.json",
    ),
}

EXPECTED_CENTS = {
    "014-0804": [161787120454, 168983217931, 176531627440, 180129625611,
                 184193465158, 208965014609, 236823454648, 235433711421,
                 199641676791, 135222460247],
    "068-0107": [78181866813, 71650759190, 72088790861, 78140840897,
                 79241648561, 78078798237, 87798529666, 83491661178,
                 75113801164, 45696293704],
    "012-1400": [132945394707, 134969331024, 143575133309, 159061560226,
                 167334681459, 198261040331, 217181220569, 201349805532,
                 196724438870, 102450943838],
    "012-1401": [14726894234, 2843260298, 1935683810, 78040563883,
                 4552822216, 17006115529, 4836024324, 13736575681,
                 4605238381, 1188949738],
    "012-1104": [34607475435, 32912629669, 32760801632, 33720316533,
                 29427685468, 32971219436, 37774199559, 35251044344,
                 30096473679, 15835624266],
    "012-0502": [52235486544, 57469333055, 59036592965, 62917068832,
                 77926216424, 68556152629, 73619788132, 74259289974,
                 67186128717, 48216700503],
    "012-1500": [82876556103, 89222115889, 91720317035, 99142842131,
                 113086874632, 105331756431, 154712081858, 121523404261,
                 79737696412, 69765629931],
    "012-1502": [13177038348, 12859014121, 15521875776, 12982038717,
                 14469299874, 14747277491, 18647055310, 17641614619,
                 5023499031, 6577702718],
    "012-1701": [9077065484, 9084220806, 8869467675, 9142571870,
                 9310904270, 9437563361, 10191498044, 9672629695,
                 8825852407, 5517026695],
    "012-1801": [20683269798, 22128027516, 21639195413, 21793317412,
                 23454654234, 24180520959, 26172407988, 25081286486,
                 24973409109, 9568182251],
}

REGISTERED = {
    "014-0804",
    "068-0107",
    "012-1400",
    "012-1401",
    "012-1104",
    "012-0502",
    "012-1500",
    "012-1502",
    "012-1701",
    "012-1801",
}
STAGE_SELECTORS = {
    "doi/usgs-sir,epa/science-technology": 20,
    (
        "usda/ars-salaries-expenses,"
        "usda/ars-buildings-facilities,"
        "usda/forest-rangeland-research"
    ): 30,
    (
        "usda/nifa-extension,"
        "usda/nifa-research-education,"
        "usda/nifa-integrated-activities"
    ): 30,
    "usda/ers,usda/nass": 20,
}


class EarthAgricultureObligationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        registry = json.loads(
            (ROOT / "config" / "obligation_accounts.json").read_text()
        )
        cls.accounts = {
            row["federalAccount"]: row for row in registry["accounts"]
            if row["federalAccount"] in REGISTERED
        }

    def test_exact_registry_metadata_and_activity_counts(self):
        self.assertEqual(REGISTERED, set(self.accounts))
        for code in sorted(REGISTERED):
            expected = EXPECTED[code]
            with self.subTest(account=code):
                account = self.accounts[code]
                actual = (
                    account["path"], account["name"], account["abbrev"],
                    account["agency"], len(account["programActivities"]),
                    account["baseline"],
                )
                self.assertEqual(expected, actual)
                self.assertEqual(code[:3], account["agencyIdentifier"])
                self.assertEqual("usaspending_obligations", account["adapter"])
                self.assertEqual({
                    "firstFiscalYear": 2017,
                    "firstFiscalYearPeriod": 6,
                    "regularFirstPeriod": 2,
                }, account["availability"])

    def test_exact_baseline_pins_and_boundaries(self):
        for code in sorted(REGISTERED):
            cents = EXPECTED_CENTS[code]
            with self.subTest(account=code):
                baseline_path = ROOT / EXPECTED[code][-1]
                baseline = json.loads(baseline_path.read_text())
                self.assertEqual(2, baseline["schemaVersion"])
                self.assertEqual(code, baseline["federalAccount"])
                self.assertIn("retrieved 2026-08-12", baseline["source"])
                fiscal_years = baseline["fiscalYears"]
                self.assertEqual(set(map(str, range(2015, 2027))), set(fiscal_years))
                for fiscal_year in (2015, 2016):
                    self.assertEqual("unavailable", fiscal_years[str(fiscal_year)]["status"])
                    self.assertTrue(fiscal_years[str(fiscal_year)]["reason"])
                self.assertEqual("partial", fiscal_years["2017"]["status"])
                self.assertEqual(6, fiscal_years["2017"]["firstPeriod"])
                self.assertEqual(12, fiscal_years["2017"]["asOfPeriod"])
                self.assertEqual("partial", fiscal_years["2026"]["status"])
                self.assertEqual(9, fiscal_years["2026"]["asOfPeriod"])
                actual = [
                    fiscal_years[str(fy)]["obligationsCents"]
                    for fy in range(2017, 2027)
                ]
                self.assertEqual(cents, actual)
                self.assertTrue(all(
                    fiscal_years[str(fy)]["status"] == "complete"
                    for fy in range(2018, 2026)
                ))

    def test_every_declared_source_identity_resolves(self):
        for code, account in self.accounts.items():
            with self.subTest(account=code):
                aliases = alias_map(account)
                for activity in account["programActivities"]:
                    canonical_code = str(activity["code"]).zfill(4)
                    canonical_name = activity["name"].strip().lower()
                    self.assertEqual(
                        activity["slug"],
                        aliases[("code-name", canonical_code, canonical_name)]["slug"],
                    )
                    for token in [activity.get("park"), *(activity.get("parkAliases") or [])]:
                        if token:
                            self.assertEqual(
                                activity["slug"], aliases[("park", token)]["slug"]
                            )
                    for source in activity.get("codeNameAliases") or []:
                        key = (
                            "code-name", str(source["code"]).zfill(4),
                            source["name"].strip().lower(),
                        )
                        self.assertEqual(activity["slug"], aliases[key]["slug"])

    def test_epa_fy2022_preserves_exact_official_file_a_file_b_variance(self):
        baseline = json.loads(
            (ROOT / "reference/epa_science_technology_obligation_baseline.json")
            .read_text()
        )
        row = baseline["fiscalYears"]["2022"]
        self.assertEqual(78_078_798_237, row["obligationsCents"])
        self.assertEqual(78_077_137_843, row["fileBObligationsCents"])
        self.assertEqual(1_660_394, row["fileAFileBVarianceCents"])
        self.assertEqual(
            row["obligationsCents"] - row["fileBObligationsCents"],
            row["fileAFileBVarianceCents"],
        )
        self.assertIn("A19", row["fileAFileBVarianceReason"])
        for fiscal_year, ordinary in baseline["fiscalYears"].items():
            if fiscal_year != "2022":
                self.assertNotIn("fileBObligationsCents", ordinary)
                self.assertNotIn("fileAFileBVarianceCents", ordinary)
                self.assertNotIn("fileAFileBVarianceReason", ordinary)

    def test_ars_salaries_expenses_transient_0014_alias_matches_raw_evidence(self):
        aliases = alias_map(self.accounts["012-1400"])
        raw_rows = [
            {
                "federal_account_symbol": "012-1400",
                "program_activity_code": "0014",
                "program_activity_name": "MISCELLANEOUS FEES/SUPPLEMENTALS",
                "obligations_incurred": "0.00",
            },
        ]
        values = parse_file_b_snapshot(raw_rows, "012-1400", aliases)
        self.assertEqual(1, len(values))
        (key, amount_cents), = values.items()
        self.assertEqual("5ZBXSS9QSGU", key[0])
        self.assertEqual("5ZBXSS9QSGU", key[1])
        self.assertEqual("MISCELLANEOUS FEES/SUPPLEMENTALS", key[2])
        self.assertEqual("5ZBXSS9QSGU", key[3])
        self.assertEqual(0, amount_cents)

    def test_forest_fy2020_unknown_other_matches_exact_raw_evidence(self):
        aliases = alias_map(self.accounts["012-1104"])
        raw_rows = [
            {
                "federal_account_symbol": "012-1104",
                "program_activity_code": "0000",
                "program_activity_name": "UNKNOWN/OTHER",
                "obligations_incurred": "0.00",
            },
        ]
        values = parse_file_b_snapshot(raw_rows, "012-1104", aliases)
        self.assertEqual(1, len(values))
        (key, amount_cents), = values.items()
        self.assertEqual("0000", key[0])
        self.assertEqual("0000", key[1])
        self.assertEqual("Unknown / other", key[2])
        self.assertEqual("", key[3])
        self.assertEqual(0, amount_cents)

    def test_usgs_reused_0002_identities_remain_distinct(self):
        aliases = alias_map(self.accounts["014-0804"])
        values = parse_file_b_snapshot([
            {
                "federal_account_symbol": "014-0804",
                "program_activity_code": "0002",
                "program_activity_name": "CLIMATE AND LAND USE CHANGE",
                "obligations_incurred": "1.00",
            },
            {
                "federal_account_symbol": "014-0804",
                "program_activity_code": "0002",
                "program_activity_name": "LAND RESOURCES",
                "obligations_incurred": "2.00",
            },
        ], "014-0804", aliases)
        self.assertEqual({
            "0002:climate-and-land-use-change",
            "0002:land-resources",
        }, {key[0] for key in values})
        events = combine_file_b_file_c(
            file_b_period_events({"FY2025P12": values}, "014-0804"),
            [], "014-0804",
        )
        self.assertEqual(2, len({row["id"] for row in events}))
        self.assertEqual(300, sum(row["amountCents"] for row in events))

    def test_epa_mission_parks_do_not_alias_legacy_activities(self):
        account = self.accounts["068-0107"]
        aliases = alias_map(account)
        mission_parks = {
            "PRE2018", "61URFU83VLC", "61URFU83VL5", "61URFU83VL6",
            "61URFU83VL7", "61URFU83VL9", "EX202500311501", "61URFU83VL3",
        }
        self.assertEqual(
            mission_parks,
            {
                token for activity in account["programActivities"]
                for token in [activity.get("park"), *(activity.get("parkAliases") or [])]
                if token
            },
        )
        legacy = aliases[("code-name", "0045", "clean air allowance trading programs")]
        mission = aliases[("park", "61URFU83VL6")]
        self.assertNotEqual(legacy["slug"], mission["slug"])
        self.assertNotIn("park", legacy)

    def test_nifa_reused_codes_and_set_asides_remain_distinct(self):
        if not {"012-0502", "012-1500", "012-1502"} <= set(self.accounts):
            return
        extension = alias_map(self.accounts["012-0502"])
        farm_stress = extension[(
            "code-name", "0036", "farm stress assistance network"
        )]
        gus = extension[(
            "code-name", "0036", "the gus schamuer nutrition incentive program"
        )]
        self.assertNotEqual(farm_stress["_identityKey"], gus["_identityKey"])

        research = alias_map(self.accounts["012-1500"])
        integrated = alias_map(self.accounts["012-1502"])
        self.assertEqual(
            "set-aside-1500", research[("park", "EX202600312973")]["slug"]
        )
        self.assertEqual(
            "set-aside-1502", integrated[("park", "EX202600312979")]["slug"]
        )
        self.assertEqual(
            "set-aside", integrated[("code-name", "9901", "set aside")]["slug"]
        )
        self.assertNotEqual(
            integrated[("park", "EX202600312979")]["_identityKey"],
            integrated[("code-name", "9901", "set aside")]["_identityKey"],
        )

    def test_nifa_extension_fy2026_financial_adjustment_matches_raw_evidence(self):
        aliases = alias_map(self.accounts["012-0502"])
        values = parse_file_b_snapshot([{
            "federal_account_symbol": "012-0502",
            "program_activity_reporting_key": "EX202500290511",
            "program_activity_code": "",
            "program_activity_name": "",
            "obligations_incurred": "892236.09",
        }], "012-0502", aliases)
        self.assertEqual(1, len(values))
        (key, amount_cents), = values.items()
        self.assertEqual("EX202500290511", key[0])
        self.assertEqual("EX202500290511", key[1])
        self.assertEqual("FINANCIAL ADJUSTMENT: PROGRAM NOT SPECIFIED", key[2])
        self.assertEqual("EX202500290511", key[3])
        self.assertEqual(89_223_609, amount_cents)

    def test_nifa_integrated_fsdw_matches_raw_evidence(self):
        aliases = alias_map(self.accounts["012-1502"])
        cases = {
            "FY2019P09": ("4049.06", 404_906),
            "FY2022P02": ("24258.51", 2_425_851),
            "FY2023P06": ("1579.27", 157_927),
            "FY2024P05": ("5080.00", 508_000),
            "FY2025P02": ("1.87", 187),
        }
        for period, (raw_amount, expected_cents) in cases.items():
            with self.subTest(period=period):
                values = parse_file_b_snapshot([{
                    "federal_account_symbol": "012-1502",
                    "program_activity_reporting_key": "",
                    "program_activity_code": "FS09",
                    "program_activity_name":
                        "FSDW (FINANCIAL STATEMENT DATA WAREHOUSE)",
                    "obligations_incurred": raw_amount,
                }], "012-1502", aliases)
                self.assertEqual(1, len(values))
                (key, amount_cents), = values.items()
                self.assertEqual("FS09", key[0])
                self.assertEqual("FS09", key[1])
                self.assertEqual(
                    "FSDW (FINANCIAL STATEMENT DATA WAREHOUSE)", key[2])
                self.assertEqual("", key[3])
                self.assertEqual(expected_cents, amount_cents)

    def test_statistical_accounts_keep_exact_source_identities(self):
        ers = alias_map(self.accounts["012-1701"])
        nass = alias_map(self.accounts["012-1801"])
        self.assertEqual(
            "economic-research-service",
            ers[("park", "5ZBXPKUP513")]["slug"],
        )
        self.assertEqual(
            "economic-research-service-reimbursable",
            ers[("park", "5ZBXPKUP5ZL")]["slug"],
        )
        self.assertEqual(
            "financial-adjustment-program-not-specified",
            ers[("park", "EX202500290511")]["slug"],
        )
        self.assertEqual(
            "financial-adjustment-program-not-specified",
            nass[("park", "EX202500290511")]["slug"],
        )
        self.assertEqual(
            "unknown-other",
            nass[("code-name", "0000", "unknown/other")]["slug"],
        )
        self.assertEqual(
            "fsdw-financial-statement-data-warehouse",
            nass[(
                "code-name", "FS09",
                "fsdw (financial statement data warehouse)",
            )]["slug"],
        )

    def test_ers_fy2026_financial_adjustment_matches_raw_evidence(self):
        aliases = alias_map(self.accounts["012-1701"])
        values = parse_file_b_snapshot([{
            "federal_account_symbol": "012-1701",
            "program_activity_reporting_key": "EX202500290511",
            "program_activity_code": "",
            "program_activity_name": "",
            "obligations_incurred": "5143666.08",
        }], "012-1701", aliases)
        self.assertEqual(1, len(values))
        (key, amount_cents), = values.items()
        self.assertEqual("EX202500290511", key[0])
        self.assertEqual("EX202500290511", key[1])
        self.assertEqual("FINANCIAL ADJUSTMENT: PROGRAM NOT SPECIFIED", key[2])
        self.assertEqual("EX202500290511", key[3])
        self.assertEqual(514_366_608, amount_cents)

    def test_nass_fy2020_unknown_other_matches_raw_evidence(self):
        aliases = alias_map(self.accounts["012-1801"])
        values = parse_file_b_snapshot([{
            "federal_account_symbol": "012-1801",
            "program_activity_reporting_key": "",
            "program_activity_code": "0000",
            "program_activity_name": "UNKNOWN/OTHER",
            "obligations_incurred": "0.00",
        }], "012-1801", aliases)
        self.assertEqual(1, len(values))
        (key, amount_cents), = values.items()
        self.assertEqual("0000", key[0])
        self.assertEqual("0000", key[1])
        self.assertEqual("Unknown / other", key[2])
        self.assertEqual("0000", key[3])
        self.assertEqual(0, amount_cents)

    def test_stage_selectors_are_payload_ready(self):
        for selector, expected_count in STAGE_SELECTORS.items():
            jobs = plan(ROOT, mode="full", selectors=selector)["include"]
            self.assertEqual(expected_count, len(jobs), selector)
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

    def test_no_synthetic_ars_or_nifa_total_account(self):
        paths = {account["path"] for account in self.accounts.values()}
        self.assertNotIn("usda/ars-total", paths)
        self.assertNotIn("usda/nifa-total", paths)


if __name__ == "__main__":
    unittest.main()
