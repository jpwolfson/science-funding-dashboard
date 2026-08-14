import json
import unittest
from pathlib import Path

from adapters.obligation_common import aggregate
from adapters.usaspending_obligations import (
    alias_map, combine_file_b_file_c, file_b_period_events,
    parse_file_b_snapshot, parse_file_c,
)
from scripts.plan_obligation_refresh import plan


REPO = Path(__file__).resolve().parent.parent

ACCOUNT_META = {
    "commerce/noaa-orf": (
        "013-1450", "Operations, Research and Facilities", 16, 67,
        [387492057258, 401113134274, 414053240951, 446269141709,
         449218951481, 494084647118, 628433143287, 731822420137,
         590995523920, 303405392819],
    ),
    "commerce/noaa-pac": (
        "013-1460", "Procurement, Acquisition and Construction", 12, 32,
        [218232731360, 229682681660, 194996240784, 161579703991,
         152521312472, 164623381900, 204331417055, 250246323778,
         205265406319, 134504769998],
    ),
    "commerce/nist-strs": (
        "013-0500", "Scientific and Technical Research and Services", 7, 11,
        [71211674371, 71411863464, 74683941480, 75042249476,
         80361787623, 83310214199, 99850616225, 129647944433,
         95760889645, 59469231377],
    ),
    "commerce/nist-its": (
        "013-0525", "Industrial Technology Services", 8, 13,
        [19088888306, 15767997657, 15896666508, 22295182247,
         26134557043, 23799236356, 21341065594, 44001741776,
         71946905729, 97300322794],
    ),
    "commerce/bea": (
        "013-1500", "Salaries and Expenses, Economic and Statistical Analysis",
        4, 5,
        [11687711023, 11037121955, 10440276818, 0, 11769634040,
         11996322841, 13080326230, 13157627614, 12876519316, 8352144116],
    ),
    "commerce/census-current-surveys": (
        "013-0401", "Current Surveys and Programs", 6, 9,
        [27593670279, 29213906053, 28888071095, 29214324563,
         30609204710, 31975648211, 34626118161, 34820902232,
         34371943923, 26361342910],
    ),
    "commerce/census-periodic-censuses": (
        "013-0450", "Periodic Censuses and Programs", 12, 17,
        [124608213991, 152216377156, 343510920269, 658360397941,
         208540540023, 119117937899, 113692592505, 110423499944,
         105107725694, 87727386199],
    ),
}

# These readable canonical labels are stable dashboard identities, while the
# official PAC/PAN inventory exposes only their exact source alias. Keeping the
# distinction explicit prevents a display label from inflating source coverage.
DISPLAY_ONLY_CANONICALS = {
    *( (path, "unknown-other") for path in ACCOUNT_META ),
    ("commerce/nist-strs", "chips"),
    ("commerce/nist-its", "chips"),
    ("commerce/census-periodic-censuses", "decennial-census-legacy-0008"),
}

OFFICIAL_SOURCE_COUNTS = {
    "commerce/noaa-orf": (49, 18),
    "commerce/noaa-pac": (23, 9),
    "commerce/nist-strs": (5, 6),
    "commerce/nist-its": (7, 6),
    "commerce/bea": (4, 1),
    "commerce/census-current-surveys": (6, 3),
    "commerce/census-periodic-censuses": (13, 4),
}

# USAspending's FY2026 P05 custom File B emitted PARK ``0`` twice with blank
# legacy fields and zero dollars. It is not present in the official five-row
# BEA PA inventory, so keep this exact parser alias outside the inventory count.
SOURCE_DEFECT_PARK_ALIASES = {
    ("commerce/bea", "unknown-other", "0"),
}

STAGE_PATHS = (
    ("commerce/bea",),
    ("commerce/bea", "commerce/noaa-orf", "commerce/noaa-pac"),
    ("commerce/bea", "commerce/noaa-orf", "commerce/noaa-pac",
     "commerce/nist-strs", "commerce/nist-its"),
    ("commerce/bea", "commerce/noaa-orf", "commerce/noaa-pac",
     "commerce/nist-strs", "commerce/nist-its",
     "commerce/census-current-surveys"),
    ("commerce/bea", "commerce/noaa-orf", "commerce/noaa-pac",
     "commerce/nist-strs", "commerce/nist-its",
     "commerce/census-current-surveys",
     "commerce/census-periodic-censuses"),
)
STAGE_JOB_COUNTS = dict(zip(STAGE_PATHS, (10, 30, 50, 60, 70)))


class CommerceObligationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        registry = json.loads(
            (REPO / "config" / "obligation_accounts.json").read_text()
        )
        cls.accounts = {
            row["path"]: row for row in registry["accounts"]
            if row["path"].startswith("commerce/")
        }
        cls.stage_paths = tuple(cls.accounts)

    def test_registry_has_exact_commerce_account_contract(self):
        self.assertIn(self.stage_paths, STAGE_PATHS)
        self.assertEqual(
            sum(ACCOUNT_META[path][2] for path in self.stage_paths),
            sum(len(row["programActivities"])
                for row in self.accounts.values()),
        )
        for path in self.stage_paths:
            symbol, title, path_count, _, _ = ACCOUNT_META[path]
            with self.subTest(path=path):
                account = self.accounts[path]
                self.assertEqual(symbol, account["federalAccount"])
                self.assertEqual(title, account["name"])
                self.assertEqual("Department of Commerce", account["agency"])
                self.assertEqual("013", account["agencyIdentifier"])
                self.assertEqual("usaspending_obligations", account["adapter"])
                self.assertEqual({
                    "firstFiscalYear": 2017,
                    "firstFiscalYearPeriod": 6,
                    "regularFirstPeriod": 2,
                }, account["availability"])
                self.assertEqual(path_count, len(account["programActivities"]))
                alias_map(account)

    def test_official_pa_inventory_is_complete_and_exactly_resolvable(self):
        grand_total = 0
        source_defects = set()
        for path, account in self.accounts.items():
            with self.subTest(path=path):
                aliases = alias_map(account)
                pac_pairs = []
                parks = []
                for activity in account["programActivities"]:
                    # FY2026 PARK-only rows use the PARK as their display code;
                    # they are one official PARK identity, not an extra PAC/PAN.
                    if (len(str(activity["code"])) <= 4
                            and (path, activity["slug"])
                            not in DISPLAY_ONLY_CANONICALS):
                        pac_pairs.append((
                            str(activity["code"]).zfill(4), activity["name"]
                        ))
                    pac_pairs.extend((str(row["code"]).zfill(4), row["name"])
                                     for row in activity.get("codeNameAliases", []))
                    for park in filter(None, [
                            activity.get("park"),
                            *activity.get("parkAliases", []),
                    ]):
                        defect = (path, activity["slug"], park)
                        if defect in SOURCE_DEFECT_PARK_ALIASES:
                            source_defects.add(defect)
                            self.assertIn(("park", park), aliases)
                        else:
                            parks.append(park)

                normalized_pairs = [(code, name.strip().lower())
                                    for code, name in pac_pairs]
                self.assertEqual(len(normalized_pairs), len(set(normalized_pairs)))
                self.assertEqual(len(parks), len(set(parks)))
                for code, name in normalized_pairs:
                    self.assertIn(("code-name", code, name), aliases)
                for park in parks:
                    self.assertIn(("park", park), aliases)

                expected = ACCOUNT_META[path][3]
                self.assertEqual(OFFICIAL_SOURCE_COUNTS[path],
                                 (len(pac_pairs), len(parks)))
                self.assertEqual(expected, len(pac_pairs) + len(parks))
                grand_total += len(pac_pairs) + len(parks)
        self.assertEqual(
            sum(ACCOUNT_META[path][3] for path in self.stage_paths),
            grand_total,
        )
        self.assertEqual(
            {row for row in SOURCE_DEFECT_PARK_ALIASES
             if row[0] in self.stage_paths},
            source_defects,
        )

    def test_baselines_preserve_exact_pins_and_boundaries(self):
        for path in self.stage_paths:
            symbol, _, _, _, pins = ACCOUNT_META[path]
            with self.subTest(path=path):
                baseline = json.loads(
                    (REPO / self.accounts[path]["baseline"]).read_text()
                )
                self.assertEqual(2, baseline["schemaVersion"])
                self.assertEqual(symbol, baseline["federalAccount"])
                self.assertIn("retrieved 2026-08-12", baseline["source"])
                years = baseline["fiscalYears"]
                self.assertEqual({str(fy) for fy in range(2015, 2027)}, set(years))
                self.assertEqual("unavailable", years["2015"]["status"])
                self.assertEqual("unavailable", years["2016"]["status"])
                self.assertEqual(
                    {"status": "partial", "firstPeriod": 6, "asOfPeriod": 12,
                     "obligationsCents": pins[0]},
                    years["2017"],
                )
                for offset, fy in enumerate(range(2018, 2026), start=1):
                    if path == "commerce/bea" and fy == 2020:
                        continue
                    self.assertEqual("complete", years[str(fy)]["status"])
                    self.assertEqual(pins[offset], years[str(fy)]["obligationsCents"])
                self.assertEqual(
                    {"status": "partial", "asOfPeriod": 9,
                     "obligationsCents": pins[-1]},
                    years["2026"],
                )

    def test_bea_fy2020_probe_proves_complete_zero_net_year(self):
        account = self.accounts["commerce/bea"]
        baseline = json.loads((REPO / account["baseline"]).read_text())
        row = baseline["fiscalYears"]["2020"]
        self.assertEqual(
            {"status": "complete", "firstPeriod": 3, "asOfPeriod": 12,
             "obligationsCents": 0},
            row,
        )
        evidence = json.loads(
            (REPO / "reference" / "commerce_bea_fy2020_probe_evidence.json")
            .read_text()
        )
        self.assertEqual("013-1500", evidence["federalAccount"])
        self.assertEqual("3693", evidence["accountId"])
        self.assertEqual(3, evidence["firstMaterialPeriod"])
        self.assertEqual(166, evidence["normalized"]["recordCount"])
        self.assertEqual(0, evidence["normalized"]["netObligationsCents"])
        self.assertEqual(10506144613,
                         evidence["normalized"]["grossPositiveCents"])
        self.assertEqual(-10506144613,
                         evidence["normalized"]["grossNegativeCents"])
        self.assertEqual(12, len(evidence["downloads"]))
        self.assertTrue(all(item["status"] == "finished"
                            for item in evidence["downloads"]))
        probe = plan(
            REPO, mode="custom", selectors="commerce/bea",
            from_fy=2020, to_fy=2020, current_period=12,
        )["include"]
        self.assertEqual(
            [("commerce/bea", 2020, 12, "custom")],
            [(job["account"], job["fiscalYear"], job["period"],
              job["purpose"]) for job in probe],
        )
        self._require_all_planned_pins(
            plan(REPO, mode="full", selectors="commerce/bea")["include"]
        )

    def _require_all_planned_pins(self, jobs):
        for job in jobs:
            baseline = json.loads((REPO / job["baseline"]).read_text())
            pin = baseline["fiscalYears"][str(job["fiscalYear"])]
            if "obligationsCents" not in pin:
                raise AssertionError(
                    f"{job['account']} FY{job['fiscalYear']} is "
                    "preflight-required"
                )

    def test_staged_planner_count_is_exact(self):
        jobs = plan(REPO, mode="full", selectors="commerce")["include"]
        self.assertEqual(STAGE_JOB_COUNTS[self.stage_paths], len(jobs))
        by_account = {path: [] for path in self.stage_paths}
        for job in jobs:
            by_account[job["account"]].append(
                (job["fiscalYear"], job["period"])
            )
        for path, rows in by_account.items():
            expected = [(fy, 12) for fy in range(2017, 2026)] + [(2026, 9)]
            self.assertEqual(expected, rows)
        self._require_all_planned_pins(jobs)

    def _assert_collision(self, path, source_pairs, expected):
        account = self.accounts[path]
        rows = [{
            "federal_account_symbol": account["federalAccount"],
            "program_activity_code": code,
            "program_activity_name": name,
            "obligations_incurred": f"{index}.00",
        } for index, (code, name) in enumerate(source_pairs, start=1)]
        values = parse_file_b_snapshot(
            rows, account["federalAccount"], alias_map(account)
        )
        observed = {key[0]: (key[2], amount) for key, amount in values.items()}
        self.assertEqual(expected, observed)
        flows = file_b_period_events(
            {"FY2024P02": values}, account["federalAccount"]
        )
        events = combine_file_b_file_c(flows, [], account["federalAccount"])
        self.assertEqual(sum(range(1, len(source_pairs) + 1)) * 100,
                         sum(row["amountCents"] for row in events))
        self.assertEqual(len(events), len({row["id"] for row in events}))
        self.assertEqual(set(expected), {
            row["_programActivityKey"] for row in events
        })

    def test_reused_pac_codes_remain_collision_safe_through_pipeline(self):
        cases = [
            ("commerce/noaa-orf",
             [("0010", "Office of Marine and Aviation Operations"),
              ("0010", "Spectrum Relocation Fund")],
             {"0010:office-marine-aviation-operations":
                  ("Office of Marine and Aviation Operations", 100),
              "0010:spectrum-relocation-fund":
                  ("Spectrum Relocation Fund", 200)}),
            ("commerce/noaa-orf",
             [("0066", "NATIONAL MARINE FISHERIES SERVICE"),
              ("0066", "SPECTRUM RELOCATION PROGRAM")],
             {"0002:national-marine-fisheries-service":
                  ("National Marine Fisheries Service", 100),
              "0010:spectrum-relocation-fund":
                  ("Spectrum Relocation Fund", 200)}),
            ("commerce/noaa-orf",
             [("0006", "OCEANIC AND ATMOSPHERIC RESEARCH"),
              ("0006", "MISSION SUPPORT")],
             {"0003:oceanic-atmospheric-research":
                  ("Oceanic and Atmospheric Research", 100),
              "0006:program-support": ("Program Support", 200)}),
            ("commerce/noaa-orf",
             [("0007", "MISSION SUPPORT"),
              ("0007", "OFFICE OF MARINE AND AVIATION OPERATIONS")],
             {"0006:program-support": ("Program Support", 100),
              "0010:office-marine-aviation-operations":
                  ("Office of Marine and Aviation Operations", 200)}),
            ("commerce/noaa-orf",
             [("0004", "National Weather Service"),
              ("0004", "NATIONAL ENVIRONMENTAL SATELLITE, DATA AND INFORMATION SERVICE")],
             {"0004:national-weather-service": ("National Weather Service", 100),
              "0005:national-environmental-satellite-service":
                  ("National Environmental Satellite Service", 200)}),
            ("commerce/noaa-pac",
             [("0015", "OCEANIC AND ATMOSPHERIC RESEARCH"),
              ("0015", "NOAA Wide Support Services")],
             {"0003:oceanic-atmospheric-research":
                  ("Oceanic and Atmospheric Research", 100),
              "0015:noaa-wide-support-services":
                  ("NOAA Wide Support Services", 200)}),
            ("commerce/nist-its",
             [("0000", "TECHNOLOGY INNOVATION PROGRAM"),
              ("0000", "UNKNOWN/OTHER")],
             {"0001:technology-innovation-program":
                  ("Technology Innovation Program", 100),
              "0000": ("Unknown / other", 200)}),
        ]
        for path, source_pairs, expected in cases:
            if path not in self.accounts:
                continue
            with self.subTest(path=path, source_pairs=source_pairs):
                self._assert_collision(path, source_pairs, expected)

    def _park_events(self, path, parks):
        account = self.accounts[path]
        rows = [{
            "federal_account_symbol": account["federalAccount"],
            "program_activity_reporting_key": park,
            "program_activity_code": "",
            "program_activity_name": "source label may drift",
            "obligations_incurred": f"{index}.00",
        } for index, park in enumerate(parks, start=1)]
        values = parse_file_b_snapshot(
            rows, account["federalAccount"], alias_map(account)
        )
        flows = file_b_period_events(
            {"FY2026P09": values}, account["federalAccount"]
        )
        return combine_file_b_file_c(flows, [], account["federalAccount"])

    def test_nist_special_parks_and_account_scoped_carryover_stay_separate(self):
        if not {"commerce/nist-strs", "commerce/nist-its"} <= set(self.accounts):
            return
        strs = self._park_events(
            "commerce/nist-strs", ["5ZC2FFJJAYD", "EX202600313650"]
        )
        self.assertEqual(
            {("0001", "Laboratory Programs"),
             ("EX202600313650", "STRS Laboratory Programs")},
            {(row["_programActivityKey"], row["programActivityName"])
             for row in strs},
        )
        its = self._park_events(
            "commerce/nist-its", ["5ZC2FFLEV5S", "EX202600313654"]
        )
        self.assertEqual(
            {("0002", "Hollings Manufacturing Extension Partnership"),
             ("EX202600313654",
              "ITS: Hollings Manufacturing Extension Partnership")},
            {(row["_programActivityKey"], row["programActivityName"])
             for row in its},
        )

        strs_carryover = self._park_events(
            "commerce/nist-strs", ["EX202600313426"]
        )[0]
        its_carryover = self._park_events(
            "commerce/nist-its", ["EX202600313426"]
        )[0]
        self.assertEqual(strs_carryover["_programActivityKey"],
                         its_carryover["_programActivityKey"])
        self.assertNotEqual(strs_carryover["id"], its_carryover["id"])

    def test_bea_fy2026_zero_park_sentinel_is_exact_and_fail_closed(self):
        account = self.accounts["commerce/bea"]
        aliases = alias_map(account)
        amounts = [
            "0.00", "25213792.66", "46642.26", "119725.79",
            "926899.64", "9222180.44", "21949.29", "25000.00",
            "14684.66", "1538.12", "0.00", "357404.92", "15276.84",
            "324000.00", "1979640.89", "28808.45", "2120223.49",
            "1955568.78", "9526.48", "-198608.36", "4207.88",
        ]
        rows = [{
            "submission_period": "FY2026P05",
            "federal_account_symbol": account["federalAccount"],
            "program_activity_reporting_key": "0",
            "program_activity_code": "",
            "program_activity_name": "",
            "obligations_incurred": "0.00",
        } for _ in range(2)]
        rows.extend({
            "submission_period": "FY2026P05",
            "federal_account_symbol": account["federalAccount"],
            "program_activity_reporting_key": "5ZC1J3BKY9N",
            "program_activity_code": "",
            "program_activity_name": "",
            "obligations_incurred": amount,
        } for amount in amounts)
        values = parse_file_b_snapshot(
            rows, account["federalAccount"], aliases
        )
        self.assertEqual(2, len(values))
        self.assertEqual(4218846223, sum(values.values()))
        by_identity = {key[0]: amount for key, amount in values.items()}
        self.assertEqual({"0000": 0, "0001": 4218846223}, by_identity)
        with self.assertRaisesRegex(ValueError, "PARK='not-a-real-park'"):
            parse_file_b_snapshot([{
                "federal_account_symbol": account["federalAccount"],
                "program_activity_reporting_key": "not-a-real-park",
                "program_activity_code": "",
                "program_activity_name": "",
                "obligations_incurred": "0.00",
            }], account["federalAccount"], aliases)

    def test_negative_file_c_and_ratio_over_100_percent_are_preserved(self):
        account = self.accounts["commerce/bea"]
        aliases = alias_map(account)
        base = {
            "submission_period": "FY2024P02",
            "federal_account_symbol": account["federalAccount"],
            "program_activity_code": "0001",
            "program_activity_name": "Bureau of Economic Analysis",
            "award_unique_key": "A",
        }
        parts = {
            "Assistance.csv": [
                {**base, "transaction_obligated_amount": "2.00"},
                {**base, "transaction_obligated_amount": "-0.25"},
            ],
            "Contracts.csv": [],
            "Unlinked.csv": [],
        }
        file_c = parse_file_c(parts, account["federalAccount"], aliases)
        file_b_values = parse_file_b_snapshot([{
            "federal_account_symbol": account["federalAccount"],
            "program_activity_code": "0001",
            "program_activity_name": "Bureau of Economic Analysis",
            "obligations_incurred": "1.00",
        }], account["federalAccount"], aliases)
        file_b = file_b_period_events(
            {"FY2024P02": file_b_values}, account["federalAccount"]
        )
        events = combine_file_b_file_c(file_b, file_c, account["federalAccount"])
        metrics = aggregate(
            events, current_fy=2024, covered_periods={"FY2024P02"}
        )
        self.assertEqual(100, metrics["netObligationsCents"])
        self.assertEqual(175, metrics["awardLinkedObligationsCents"])
        self.assertEqual(-75, metrics["residualObligationsCents"])
        self.assertEqual(-100, metrics["deobligationsCents"])
        self.assertEqual(1.75, metrics["fileCToNetRatio"])
        self.assertEqual(-25, file_c[0]["grossNegativeCents"])

    def test_scaffold_does_not_claim_materialized_store(self):
        for path in self.stage_paths:
            self.assertFalse((REPO / "data" / "obligations" / path).exists())


if __name__ == "__main__":
    unittest.main()
