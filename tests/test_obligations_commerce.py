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
         449218951481, 494084647118, 628433143287, 725047451996,
         590995523920, 303405392819],
    ),
    "commerce/noaa-pac": (
        "013-1460", "Procurement, Acquisition and Construction", 12, 32,
        [218232731360, 229682681660, 194996240784, 161579703991,
         152521312472, 164623381900, 204331417055, 240475202079,
         263240345521, 134504769998],
    ),
    "commerce/nist-strs": (
        "013-0500", "Scientific and Technical Research and Services", 8, 12,
        [71211674371, 71411863464, 74683941480, 75042249476,
         80361787623, 83310214199, 99850616225, 129647944433,
         95760889645, 59469231377],
    ),
    "commerce/nist-its": (
        "013-0525", "Industrial Technology Services", 9, 14,
        [19088888306, 15767997657, 15896666508, 22295182247,
         26134557043, 23799236356, 21341065594, 44001741776,
         71946905729, 97300322794],
    ),
    "commerce/bea": (
        "013-1500", "Salaries and Expenses, Economic and Statistical Analysis",
        4, 5,
        [11687711023, 11037121955, 10440276818, None, 11769634040,
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
    "commerce/nist-strs": (5, 7),
    "commerce/nist-its": (7, 7),
    "commerce/bea": (4, 1),
    "commerce/census-current-surveys": (6, 3),
    "commerce/census-periodic-censuses": (13, 4),
}

NOAA_ORF_FY2025_P02_TRANSIENTS = (
    ("0100", "NATIONAL OCEAN SERVICE", 361884807, "0001"),
    ("0101", "NATIONAL OCEAN SERVICE", 1256497384, "0001"),
    ("0101", "NATIONAL OCEAN SERVICE - IIJA (P.L. 117-58)", 846277, "0001"),
    ("0102", "NATIONAL OCEAN SERVICE", 647560877, "0001"),
    ("0201", "NATIONAL MARINE FISHERIES SERVICE", 1551980677, "0002"),
    ("0202", "NATIONAL MARINE FISHERIES SERVICE", 1257917781, "0002"),
    ("0203", "NATIONAL MARINE FISHERIES SERVICE", 624970178, "0002"),
    ("0204", "NATIONAL MARINE FISHERIES SERVICE", 397635684, "0002"),
    ("0204", "NATIONAL MARINE FISHERIES SERVICE - IIJA (P.L. 117-58)", 2924101, "0002"),
    ("0210", "NATIONAL MARINE FISHERIES SERVICE - IIJA (P.L. 117-58)", 13375457, "0002"),
    ("0300", "OCEANIC AND ATMOPHERIC RESEARCH", 340058632, "0003"),
    ("0301", "OCEANIC AND ATMOPHERIC RESEARCH", 731432413, "0003"),
    ("0302", "OCEANIC AND ATMOPHERIC RESEARCH", 789373443, "0003"),
    ("0302", "OCEANIC AND ATMOSPHERIC RESEARCH - IIJA (P.L. 117-58)", 2680453, "0003"),
    ("0303", "OCEANIC AND ATMOPHERIC RESEARCH", 862793220, "0003"),
    ("0304", "OCEANIC AND ATMOPHERIC RESEARCH", 52667433, "0003"),
    ("0400", "NATIONAL WEATHER SERVICE", 404348903, "0004"),
    ("0401", "NATIONAL WEATHER SERVICE", 1698334256, "0004"),
    ("0402", "NATIONAL WEATHER SERVICE", 513834805, "0004"),
    ("0403", "NATIONAL WEATHER SERVICE", 6284552016, "0004"),
    ("0404", "NATIONAL WEATHER SERVICE", 330000600, "0004"),
    ("0405", "NATIONAL WEATHER SERVICE", 1169819181, "0004"),
    ("0405", "NATIONAL WEATHER SERVICE - IIJA (P.L. 117-58)", 4686699, "0004"),
    ("0500", "NATIONAL ENVIRONMENTAL SATELLITE DATA, AND INFO. S", 3563106, "0005"),
    ("0501", "NATIONAL ENVIRONMENTAL SATELLITE DATA, AND INFO. S", 1059915698, "0005"),
    ("0502", "NATIONAL ENVIRONMENTAL SATELLITE DATA, AND INFO. S", 600508081, "0005"),
    ("0601", "MISSION SUPPORT", 2232602531, "0006"),
    ("0601", "MISSION SUPPORT - IIJA (P.L. 117-58)", 30888699, "0006"),
    ("0700", "OFFICE OF MARINE AND AVIATION OPERATIONS", 99057482, "0010"),
    ("0701", "OFFICE OF MARINE AND AVIATION OPERATIONS", 1660104593, "0010"),
    ("0702", "OFFICE OF MARINE AND AVIATION OPERATIONS", 236131382, "0010"),
    ("0705", "OFFICE OF MARINE AND AVIATION OPERATIONS", 34779524, "0010"),
    ("0706", "OFFICE OF MARINE AND AVIATION OPERATIONS - IIJA (P.L. 117-58)", 900223232, "0010"),
    ("1210", "NOAA WIDE SUPPORT SERVICES", 671816022, "0015"),
)

NOAA_ORF_FY2025_P06_TRANSIENTS = (
    ("0420", "NATIONAL WEATHER SERVICE", 40646, "0004"),
    ("0520", "NESDIS", 225000000, "0005"),
    ("0620", "MISSION SUPPORT", 50000000, "0006"),
)

NOAA_ORF_FY2025_P07_TRANSIENTS = (
    ("0240", "NATIONAL MARINE FISHERIES SERVICE", 95600000, "0002"),
    ("0320", "OCEANIC AND ATMOPHERIC RESEARCH", 252100000, "0003"),
)

TRANSIENT_SOURCE_PAIRS = {
    ("commerce/noaa-orf", code, name)
    for code, name, _, _ in (
        NOAA_ORF_FY2025_P02_TRANSIENTS
        + NOAA_ORF_FY2025_P06_TRANSIENTS
        + NOAA_ORF_FY2025_P07_TRANSIENTS
    )
}

NOAA_PATHS = ("commerce/noaa-orf", "commerce/noaa-pac")
NIST_PATHS = ("commerce/nist-strs", "commerce/nist-its")

NIST_ITS_FY2026_P02_PARK_CENTS = {
    "0": (0,),
    "5ZC2FFLEV5S": (
        34757034, 73645516, 603766, -79896, 27126079, 5816,
        -24987776, 0, 0, 0, 18294,
    ),
    "5ZC2FFLEV5T": (
        0, 26170742, 0, 57806493, 2254073, 21677751, 880996,
        0, 0, 0, 0, 23654, 0, 0,
    ),
    "5ZC2FFLEV5U": (0,),
    "6081W4SGJNC": (0, 0, 0),
    "EX202600313426": (0,),
    "EX202600313654": (284332,),
}

NIST_STRS_FY2026_FILE_B_EVIDENCE = {
    "FY2026P02": (85, 7538666122, ()),
    "FY2026P03": (90, 12817408064, ()),
    "FY2026P04": (93, 20496206010, ()),
    "FY2026P05": (100, 25225091620, (0, 0, 0, 0)),
}

STAGE_PATHS = (NOAA_PATHS, NOAA_PATHS + NIST_PATHS)
POST_RESOLUTION_JOB_COUNTS = dict(zip(STAGE_PATHS, (20, 40)))
CURRENT_FY2026_PINS = {
    "commerce/noaa-orf": 303354666643,
    "commerce/noaa-pac": 105930342662,
    "commerce/nist-strs": 59469231377,
    "commerce/nist-its": 97300322794,
}


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
                    pac_pairs.extend(
                        (str(row["code"]).zfill(4), row["name"])
                        for row in activity.get("codeNameAliases", [])
                        if (path, str(row["code"]).zfill(4), row["name"])
                        not in TRANSIENT_SOURCE_PAIRS
                    )
                    parks.extend(filter(None, [
                        activity.get("park"),
                        *activity.get("parkAliases", []),
                    ]))

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

    def test_noaa_orf_fy2025_p02_transient_aliases_reconcile_exactly(self):
        account = self.accounts["commerce/noaa-orf"]
        aliases = alias_map(account)
        parsed_total = 0
        for code, name, amount_cents, canonical_code in NOAA_ORF_FY2025_P02_TRANSIENTS:
            with self.subTest(code=code, name=name):
                row = {
                    "federal_account_symbol": account["federalAccount"],
                    "program_activity_reporting_key": "",
                    "program_activity_code": code,
                    "program_activity_name": name,
                    "obligations_incurred": (
                        f"{amount_cents // 100}.{amount_cents % 100:02d}"
                    ),
                }
                parsed = parse_file_b_snapshot(
                    [row], account["federalAccount"], aliases
                )
                self.assertEqual(1, len(parsed))
                key, parsed_cents = next(iter(parsed.items()))
                self.assertEqual(canonical_code, key[1])
                self.assertEqual(amount_cents, parsed_cents)
                parsed_total += parsed_cents
        self.assertEqual(34, len(NOAA_ORF_FY2025_P02_TRANSIENTS))
        self.assertEqual(26829765627, parsed_total)

    def test_noaa_orf_fy2025_p06_transient_aliases_reconcile_exactly(self):
        account = self.accounts["commerce/noaa-orf"]
        aliases = alias_map(account)
        parsed_total = 0
        for code, name, amount_cents, canonical_code in NOAA_ORF_FY2025_P06_TRANSIENTS:
            with self.subTest(code=code, name=name):
                row = {
                    "federal_account_symbol": account["federalAccount"],
                    "program_activity_reporting_key": "",
                    "program_activity_code": code,
                    "program_activity_name": name,
                    "obligations_incurred": (
                        f"{amount_cents // 100}.{amount_cents % 100:02d}"
                    ),
                }
                parsed = parse_file_b_snapshot(
                    [row], account["federalAccount"], aliases
                )
                self.assertEqual(1, len(parsed))
                key, parsed_cents = next(iter(parsed.items()))
                self.assertEqual(canonical_code, key[1])
                self.assertEqual(amount_cents, parsed_cents)
                parsed_total += parsed_cents
        self.assertEqual(3, len(NOAA_ORF_FY2025_P06_TRANSIENTS))
        self.assertEqual(275040646, parsed_total)

    def test_noaa_orf_fy2025_p07_transient_alias_reconciles_exactly(self):
        account = self.accounts["commerce/noaa-orf"]
        aliases = alias_map(account)
        parsed_total = 0
        for code, name, amount_cents, canonical_code in (
            NOAA_ORF_FY2025_P07_TRANSIENTS
        ):
            with self.subTest(code=code, name=name):
                row = {
                    "federal_account_symbol": account["federalAccount"],
                    "program_activity_reporting_key": "",
                    "program_activity_code": code,
                    "program_activity_name": name,
                    "obligations_incurred": (
                        f"{amount_cents // 100}.{amount_cents % 100:02d}"
                    ),
                }
                parsed = parse_file_b_snapshot(
                    [row], account["federalAccount"], aliases
                )
                self.assertEqual(1, len(parsed))
                key, parsed_cents = next(iter(parsed.items()))
                self.assertEqual(canonical_code, key[1])
                self.assertEqual(amount_cents, parsed_cents)
                parsed_total += parsed_cents
        self.assertEqual(2, len(NOAA_ORF_FY2025_P07_TRANSIENTS))
        self.assertEqual(347700000, parsed_total)

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
                self.assertEqual("partial", years["2026"]["status"])
                self.assertEqual(9, years["2026"]["asOfPeriod"])
                self.assertEqual(
                    CURRENT_FY2026_PINS[path],
                    years["2026"]["obligationsCents"],
                )

    def test_noaa_pac_fy2025_preserves_exact_file_a_file_b_variance(self):
        account = self.accounts["commerce/noaa-pac"]
        baseline = json.loads((REPO / account["baseline"]).read_text())
        row = baseline["fiscalYears"]["2025"]
        self.assertEqual(263240345521, row["obligationsCents"])
        self.assertEqual(261595507473, row["fileBObligationsCents"])
        self.assertEqual(1644838048, row["fileAFileBVarianceCents"])
        self.assertEqual(
            row["obligationsCents"] - row["fileBObligationsCents"],
            row["fileAFileBVarianceCents"],
        )
        self.assertIn("official source totals", row["fileAFileBVarianceReason"])
        for fy, ordinary in baseline["fiscalYears"].items():
            if fy != "2025":
                self.assertNotIn("fileBObligationsCents", ordinary)
                self.assertNotIn("fileAFileBVarianceCents", ordinary)
                self.assertNotIn("fileAFileBVarianceReason", ordinary)

    def test_noaa_orf_fy2025_preserves_exact_file_a_file_b_variance(self):
        account = self.accounts["commerce/noaa-orf"]
        baseline = json.loads((REPO / account["baseline"]).read_text())
        row = baseline["fiscalYears"]["2025"]
        self.assertEqual(590995523920, row["obligationsCents"])
        self.assertEqual(749893110879, row["fileBObligationsCents"])
        self.assertEqual(-158897586959, row["fileAFileBVarianceCents"])
        self.assertEqual(
            row["obligationsCents"] - row["fileBObligationsCents"],
            row["fileAFileBVarianceCents"],
        )
        self.assertIn("official source totals", row["fileAFileBVarianceReason"])
        for fy, ordinary in baseline["fiscalYears"].items():
            if fy != "2025":
                self.assertNotIn("fileBObligationsCents", ordinary)
                self.assertNotIn("fileAFileBVarianceCents", ordinary)
                self.assertNotIn("fileAFileBVarianceReason", ordinary)

    def test_bea_fy2020_probe_or_final_gap_is_explicit(self):
        if "commerce/bea" not in self.accounts:
            return
        account = self.accounts["commerce/bea"]
        baseline = json.loads((REPO / account["baseline"]).read_text())
        row = baseline["fiscalYears"]["2020"]
        if row["status"] == "partial":
            self.assertEqual(
                {"status": "partial", "firstPeriod": 2, "asOfPeriod": 12},
                row,
            )
            self.assertNotIn("obligationsCents", row)
            probe = plan(
                REPO, mode="custom", selectors="commerce/bea",
                from_fy=2020, to_fy=2020, current_period=12,
            )["include"]
            self.assertEqual(
                [("commerce/bea", 2020, 12, "custom")],
                [(job["account"], job["fiscalYear"], job["period"],
                  job["purpose"]) for job in probe],
            )
            with self.assertRaisesRegex(AssertionError, "preflight-required"):
                self._require_all_planned_pins(
                    plan(REPO, mode="full", selectors="commerce/bea")["include"]
                )
        else:
            self.assertEqual("unavailable", row["status"])
            self.assertNotIn("obligationsCents", row)
            self.assertEqual(
                "PROVISIONAL UNTIL CI CONFIRMATION: official USAspending "
                "FY2020 federal-account snapshot and final Program Activity "
                "result are empty; do not synthesize zero",
                row["reason"],
            )
            with self.assertRaisesRegex(
                ValueError, "FY2020 is not source-available"
            ):
                plan(
                    REPO, mode="custom", selectors="commerce/bea",
                    from_fy=2020, to_fy=2020, current_period=12,
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
        if "commerce/bea" not in self.accounts:
            self.assertEqual(POST_RESOLUTION_JOB_COUNTS[self.stage_paths],
                             len(jobs))
            self._require_all_planned_pins(jobs)
            return
        baseline = json.loads(
            (REPO / self.accounts["commerce/bea"]["baseline"]).read_text()
        )
        probe_state = baseline["fiscalYears"]["2020"]["status"] == "partial"
        expected_count = (
            10 if probe_state
            else POST_RESOLUTION_JOB_COUNTS[self.stage_paths]
        )
        self.assertEqual(expected_count, len(jobs))
        by_account = {path: [] for path in self.stage_paths}
        for job in jobs:
            by_account[job["account"]].append(
                (job["fiscalYear"], job["period"])
            )
        for path, rows in by_account.items():
            expected = [(fy, 12) for fy in range(2017, 2026)] + [(2026, 9)]
            if path == "commerce/bea" and not probe_state:
                expected.remove((2020, 12))
            self.assertEqual(expected, rows)
        if probe_state:
            with self.assertRaisesRegex(AssertionError, "preflight-required"):
                self._require_all_planned_pins(jobs)
        else:
            self._require_all_planned_pins(jobs)

    def test_normal_stage_selector_counts_are_exact(self):
        batches = (
            (("commerce/noaa-orf", "commerce/noaa-pac"), 20),
            (("commerce/nist-strs", "commerce/nist-its"), 20),
            (("commerce/census-current-surveys",), 10),
            (("commerce/census-periodic-censuses",), 10),
        )
        for paths, expected_count in batches:
            if not set(paths) <= set(self.accounts):
                continue
            selectors = ",".join(paths)
            jobs = plan(REPO, mode="full", selectors=selectors)["include"]
            self.assertEqual(expected_count, len(jobs))
            self.assertEqual(set(paths), {job["account"] for job in jobs})
            self._require_all_planned_pins(jobs)

    def test_resolved_bea_full_selector_has_nine_pinned_jobs(self):
        if "commerce/bea" not in self.accounts:
            return
        baseline = json.loads(
            (REPO / self.accounts["commerce/bea"]["baseline"]).read_text()
        )
        if baseline["fiscalYears"]["2020"]["status"] == "partial":
            return
        jobs = plan(
            REPO, mode="full", selectors="commerce/bea"
        )["include"]
        self.assertEqual(9, len(jobs))
        self.assertEqual(
            [(fy, 12) for fy in range(2017, 2026) if fy != 2020]
            + [(2026, 9)],
            [(job["fiscalYear"], job["period"]) for job in jobs],
        )
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

    def test_noaa_orf_program_and_mission_support_intentionally_merge(self):
        if "commerce/noaa-orf" not in self.accounts:
            return
        account = self.accounts["commerce/noaa-orf"]
        rows = [
            {
                "federal_account_symbol": account["federalAccount"],
                "program_activity_code": "0006",
                "program_activity_name": name,
                "obligations_incurred": amount,
            }
            for name, amount in (
                ("OCEANIC AND ATMOSPHERIC RESEARCH", "1.00"),
                ("PROGRAM SUPPORT", "2.00"),
                ("MISSION SUPPORT", "3.00"),
            )
        ]
        values = parse_file_b_snapshot(
            rows, account["federalAccount"], alias_map(account)
        )
        self.assertEqual(
            {
                "0003:oceanic-atmospheric-research":
                    ("Oceanic and Atmospheric Research", 100),
                "0006:program-support": ("Program Support", 500),
            },
            {key[0]: (key[2], amount) for key, amount in values.items()},
        )
        flows = file_b_period_events(
            {"FY2024P02": values}, account["federalAccount"]
        )
        events = combine_file_b_file_c(
            flows, [], account["federalAccount"]
        )
        self.assertEqual(600, sum(row["amountCents"] for row in events))
        self.assertEqual(2, len({row["id"] for row in events}))
        self.assertEqual(
            {"0003:oceanic-atmospheric-research", "0006:program-support"},
            {row["_programActivityKey"] for row in events},
        )

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

    def test_nist_its_fy2026_p02_park_zero_is_distinct_and_exact(self):
        if "commerce/nist-its" not in self.accounts:
            return
        account = self.accounts["commerce/nist-its"]
        rows = []
        for park, amounts in NIST_ITS_FY2026_P02_PARK_CENTS.items():
            for amount_cents in amounts:
                rows.append({
                    "submission_period": "FY2026P02",
                    "federal_account_symbol": account["federalAccount"],
                    "program_activity_reporting_key": park,
                    "program_activity_code": "",
                    "program_activity_name": "",
                    "obligations_incurred": (
                        f"{'-' if amount_cents < 0 else ''}"
                        f"{abs(amount_cents) // 100}."
                        f"{abs(amount_cents) % 100:02d}"
                    ),
                })
        values = parse_file_b_snapshot(
            rows, account["federalAccount"], alias_map(account)
        )
        events = file_b_period_events(
            {"FY2026P02": values}, account["federalAccount"]
        )
        self.assertEqual(32, len(rows))
        self.assertEqual(7, len(events))
        self.assertEqual(220186874, sum(row["amountCents"] for row in events))
        by_park = {
            row["programActivityReportingKey"]: row for row in events
        }
        self.assertEqual(set(NIST_ITS_FY2026_P02_PARK_CENTS), set(by_park))
        self.assertEqual(0, by_park["0"]["amountCents"])
        self.assertEqual("PARK0", by_park["0"]["_programActivityKey"])
        self.assertEqual(
            "PROGRAM ACTIVITY NOT SPECIFIED (PARK 0)",
            by_park["0"]["programActivityName"],
        )

    def test_nist_strs_fy2026_p05_park_zero_is_distinct_and_exact(self):
        if "commerce/nist-strs" not in self.accounts:
            return
        account = self.accounts["commerce/nist-strs"]
        evidence = NIST_STRS_FY2026_FILE_B_EVIDENCE
        rows = [{
            "submission_period": "FY2026P05",
            "federal_account_symbol": account["federalAccount"],
            "program_activity_reporting_key": "0",
            "program_activity_code": "",
            "program_activity_name": "",
            "obligations_incurred": f"{amount_cents // 100}.{amount_cents % 100:02d}",
        } for amount_cents in evidence["FY2026P05"][2]]
        values = parse_file_b_snapshot(
            rows, account["federalAccount"], alias_map(account)
        )
        events = file_b_period_events(
            {"FY2026P05": values}, account["federalAccount"]
        )
        self.assertEqual(
            ("FY2026P02", "FY2026P03", "FY2026P04", "FY2026P05"),
            tuple(evidence),
        )
        self.assertEqual(368, sum(item[0] for item in evidence.values()))
        self.assertEqual(66077371816,
                         sum(item[1] for item in evidence.values()))
        self.assertEqual(4, len(rows))
        self.assertEqual(1, len(events))
        self.assertEqual(0, events[0]["amountCents"])
        self.assertEqual("0", events[0]["programActivityReportingKey"])
        self.assertEqual("PARK0", events[0]["_programActivityKey"])
        self.assertEqual(
            "PROGRAM ACTIVITY NOT SPECIFIED (PARK 0)",
            events[0]["programActivityName"],
        )

    def test_negative_file_c_and_ratio_over_100_percent_are_preserved(self):
        if "commerce/bea" not in self.accounts:
            return
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

    def test_stage_store_transition_is_atomic(self):
        stores = {
            path: REPO / "data" / "obligations" / path
            for path in self.stage_paths
        }
        self.assertTrue(all(stores[path].is_dir() for path in NOAA_PATHS))
        active_present = [stores[path].is_dir() for path in NIST_PATHS]
        self.assertIn(sum(active_present), {0, len(NIST_PATHS)})
        if not any(active_present):
            return
        expected = {"manifest.json"}
        for fy in range(2017, 2027):
            expected.add(f"FY{fy}.csv.gz")
            expected.add(f"FY{fy}.provenance.json")
        for path in NIST_PATHS:
            store = stores[path]
            events = store / "events"
            self.assertTrue(events.is_dir())
            self.assertEqual(expected, {
                path.name for path in events.iterdir() if path.is_file()
            })


if __name__ == "__main__":
    unittest.main()
