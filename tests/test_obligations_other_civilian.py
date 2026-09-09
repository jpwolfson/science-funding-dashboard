import json
import unittest
from pathlib import Path

from adapters.usaspending_obligations import (
    alias_map, combine_file_b_file_c, file_b_period_events,
    parse_file_b_snapshot, parse_file_c,
)
from scripts.plan_obligation_refresh import plan


REPO = Path(__file__).resolve().parent.parent
ASPR_PATH = "hhs/aspr-rd-procurement"
ASPR_EVIDENCE = (
    REPO / "reference" / "hhs_aspr_rd_procurement_probe_evidence.json"
)

ACCOUNT_META = {
    "va/medical-prosthetic-research": (
        "036-0161", "Medical and Prosthetic Research",
        "Department of Veterans Affairs", 15, 14, 7,
        [72059060435, 73441493028, 82205074686, 84897709754,
         93679357008, 98664584822, 102409481598, 103621061988,
         96999597865, 62148621292],
    ),
    "dhs/science-technology-rd": (
        "070-0803", "Research and Development, Science and Technology Directorate",
        "Department of Homeland Security", 4, 5, 3,
        [36824645268, 53704594842, 49497919865, 55374300397,
         47771031511, 55202808476, 55657115658, 46545944473,
         27208933343, 11473061577],
    ),
    "dhs/cisa-rd": (
        "070-0805",
        "Research and Development, Cybersecurity and Infrastructure Security Agency",
        "Department of Homeland Security", 5, 7, 3,
        [645282569, 681997473, 1634350473, 1105175034, 1252978085,
         679807214, 984707477, 331268308, 9826, 4822],
    ),
    "dhs/cwmd-rd": (
        "070-0860", "Research and Development, Countering Weapons of Mass Destruction Office",
        "Department of Homeland Security", 14, 15, 5,
        [17605832081, 10010791277, 10949230982, 8622406989,
         5901650583, 6920298386, 6846038672, 5270214468,
         2411547147, 2380850844],
    ),
    "dot/ost-research-technology": (
        "069-1730", "Research and Technology, Office of the Secretary",
        "Department of Transportation", 17, 17, 10,
        [1922122897, 2732465563, 2493949479, 3740353690, 2649410694,
         3865268634, 6050409337, 7360729545, 9006554583, 3661176477],
    ),
    "dot/faa-research-engineering-development": (
        "069-8108", "Research, Engineering and Development, Airport and Airway Trust Fund",
        "Department of Transportation", 9, 7, 7,
        [17471975334, 15566864937, 15656401208, 20976799953,
         23032973832, 21619338757, 25936966552, 24620250191,
         19126448441, 12558757397],
    ),
    "dot/fra-rd": (
        "069-0745", "Railroad Research and Development",
        "Department of Transportation", 9, 9, 8,
        [4046788382, 4332649658, 3942736881, 4647395888, 4368766048,
         3545925546, 4838187477, 4479251034, 3094429173, 2117922206],
    ),
    "ed/ies": (
        "091-1100", "Institute of Education Sciences",
        "Department of Education", 14, 13, 9,
        [61936565830, 62092141499, 59184361852, 59755153973,
         61697598760, 76174259406, 78143351275, 82090747685,
         51698482472, 32353725549],
    ),
    "hhs/ahrq": (
        "075-1700", "Healthcare Research and Quality",
        "Department of Health and Human Services", 7, 8, 5,
        [34186503619, 35960661070, 37085850193, 36577101376,
         35760240268, 37040853365, 39800243636, 39737950229,
         29887857911, 15512385011],
    ),
    "hhs/aspr-rd-procurement": (
        "075-1000",
        "Research, Development, and Procurement, Administration for Strategic Preparedness and Response",
        "Department of Health and Human Services", 1, 1, 1, None,
    ),
    "dol/bls": (
        "016-0200", "Salaries and Expenses, Bureau of Labor Statistics",
        "Department of Labor", 10, 13, 7,
        [63925846257, 64357597642, 64776448779, 66281618319,
         68190065221, 75067753809, 76026243320, 74098588934,
         74215786476, 53798376315],
    ),
    "doj/ojp-research-evaluation-statistics": (
        "015-0401", "Research, Evaluation, and Statistics, Office of Justice Programs",
        "Department of Justice", 31, 31, 24,
        [38761103279, 43907394239, 44832043071, 42533860704,
         38288230737, 52133102208, 51684387097, 53623056361,
         42780201323, 15831632937],
    ),
}

UNKNOWN_DISPLAY_PATHS = {
    path for path in ACCOUNT_META
    if path not in {
        "dot/faa-research-engineering-development",
        "hhs/aspr-rd-procurement",
    }
}

CWMD_FY2026_FILE_B_CENTS = 2_502_737_329
CWMD_FY2026_VARIANCE_CENTS = -121_886_485
CWMD_FY2026_VARIANCE_REASON = (
    "Official FY2026 P09 GTAS/File A is 2380850844 cents while the accepted "
    "P09 File B Program Activity total is 2502737329 cents; preserve the exact "
    "-121886485-cent official source variance with File B canonical and no "
    "synthetic residual or tolerance."
)

STAGES = [
    {"hhs/aspr-rd-procurement"},
    {"va/medical-prosthetic-research"},
    {"dhs/science-technology-rd", "dhs/cisa-rd", "dhs/cwmd-rd"},
    {"dot/ost-research-technology",
     "dot/faa-research-engineering-development", "dot/fra-rd"},
    {"ed/ies"},
    {"hhs/ahrq"},
    {"dol/bls", "doj/ojp-research-evaluation-statistics"},
]


class OtherCivilianObligationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        registry = json.loads(
            (REPO / "config" / "obligation_accounts.json").read_text()
        )
        cls.accounts = {
            row["path"]: row for row in registry["accounts"]
            if row["path"] in ACCOUNT_META
        }

    def test_registry_has_exact_account_contracts(self):
        valid_stage_sets = []
        cumulative = set()
        for stage in STAGES:
            cumulative = cumulative | stage
            valid_stage_sets.append(cumulative.copy())
        self.assertIn(set(self.accounts), valid_stage_sets)
        self.assertEqual(sum(ACCOUNT_META[path][3] for path in self.accounts), sum(
            len(row["programActivities"]) for row in self.accounts.values()
        ))
        for path, account in self.accounts.items():
            with self.subTest(path=path):
                symbol, title, agency, stable_count, _, _, _ = ACCOUNT_META[path]
                self.assertEqual(symbol, account["federalAccount"])
                self.assertEqual(title, account["name"])
                self.assertEqual(agency, account["agency"])
                self.assertEqual(symbol[:3], account["agencyIdentifier"])
                self.assertEqual("usaspending_obligations", account["adapter"])
                self.assertEqual(stable_count, len(account["programActivities"]))
                if symbol == "075-1000":
                    availability = account["availability"]
                    self.assertEqual(2024, availability["firstFiscalYear"])
                    self.assertIn(
                        availability["firstFiscalYearPeriod"], range(2, 13)
                    )
                    self.assertEqual(2, availability["regularFirstPeriod"])
                else:
                    self.assertEqual({
                        "firstFiscalYear": 2017,
                        "firstFiscalYearPeriod": 6,
                        "regularFirstPeriod": 2,
                    }, account["availability"])
                alias_map(account)

    def test_all_223_official_pa_identities_are_exactly_resolvable(self):
        totals = [0, 0]
        for path, account in self.accounts.items():
            with self.subTest(path=path):
                aliases = alias_map(account)
                pac_pairs = []
                parks = []
                for activity in account["programActivities"]:
                    is_display_unknown = (
                        path in UNKNOWN_DISPLAY_PATHS
                        and activity["slug"] == "unknown-other"
                    )
                    if len(str(activity["code"])) <= 4 and not is_display_unknown:
                        pac_pairs.append((
                            str(activity["code"]).zfill(4), activity["name"]
                        ))
                    pac_pairs.extend((str(row["code"]).zfill(4), row["name"])
                                     for row in activity.get("codeNameAliases", []))
                    parks.extend(filter(None, [
                        activity.get("park"),
                        *activity.get("parkAliases", []),
                    ]))

                normalized = [(code, name.strip().lower())
                              for code, name in pac_pairs]
                self.assertEqual(len(normalized), len(set(normalized)))
                self.assertEqual(len(parks), len(set(parks)))
                for code, name in normalized:
                    self.assertIn(("code-name", code, name), aliases)
                for park in parks:
                    self.assertIn(("park", park), aliases)

                expected_pac, expected_park = ACCOUNT_META[path][4:6]
                self.assertEqual((expected_pac, expected_park),
                                 (len(pac_pairs), len(parks)))
                totals[0] += len(pac_pairs)
                totals[1] += len(parks)
        self.assertEqual(
            [sum(ACCOUNT_META[path][4] for path in self.accounts),
             sum(ACCOUNT_META[path][5] for path in self.accounts)],
            totals,
        )

    def test_normal_baselines_preserve_all_exact_cent_pins(self):
        for path, account in self.accounts.items():
            if path == "hhs/aspr-rd-procurement": continue
            with self.subTest(path=path):
                symbol, _, _, _, _, _, pins = ACCOUNT_META[path]
                baseline = json.loads(
                    (REPO / account["baseline"]).read_text()
                )
                self.assertEqual(2, baseline["schemaVersion"])
                self.assertEqual(symbol, baseline["federalAccount"])
                self.assertEqual(
                    "USAspending federal account fiscal-year snapshots (GTAS/File A), "
                    "retrieved 2026-08-12",
                    baseline["source"],
                )
                years = baseline["fiscalYears"]
                self.assertEqual({str(fy) for fy in range(2015, 2027)}, set(years))
                for fy in (2015, 2016):
                    self.assertEqual(
                        {"status": "unavailable",
                         "reason": "Files A/B/C begin in FY2017 Q2"},
                        years[str(fy)],
                    )
                self.assertEqual(
                    {"status": "partial", "asOfPeriod": 12,
                     "obligationsCents": pins[0], "firstPeriod": 6},
                    years["2017"],
                )
                for offset, fy in enumerate(range(2018, 2026), start=1):
                    self.assertEqual(
                        {"status": "complete", "obligationsCents": pins[offset]},
                        years[str(fy)],
                    )
                expected_2026 = {
                    "status": "partial", "asOfPeriod": 9,
                    "obligationsCents": pins[-1],
                }
                if path == "dhs/cwmd-rd":
                    expected_2026.update({
                        "fileBObligationsCents": CWMD_FY2026_FILE_B_CENTS,
                        "fileAFileBVarianceCents":
                            CWMD_FY2026_VARIANCE_CENTS,
                        "fileAFileBVarianceReason":
                            CWMD_FY2026_VARIANCE_REASON,
                    })
                self.assertEqual(expected_2026, years["2026"])
                self.assertEqual(2, len(baseline["notes"]))

    def _aspr_baseline(self):
        account = self.accounts[ASPR_PATH]
        return account, json.loads((REPO / account["baseline"]).read_text())

    def _aspr_result_evidence(self, account, baseline):
        self.assertTrue(
            ASPR_EVIDENCE.exists(),
            "ASPR result commit R must add official probe evidence",
        )
        evidence = json.loads(ASPR_EVIDENCE.read_text())
        self.assertEqual(1, evidence.get("schemaVersion"))
        self.assertEqual("075-1000", evidence.get("federalAccount"))
        self.assertEqual("7008", str(evidence.get("accountId")))
        self.assertEqual(2024, evidence.get("fiscalYear"))
        first_period = evidence.get("firstAcceptedPeriod")
        self.assertIn(first_period, range(2, 13))
        self.assertEqual(
            first_period, account["availability"]["firstFiscalYearPeriod"]
        )
        self.assertTrue(evidence.get("acceptedAt"))

        downloads = evidence.get("downloads") or []
        self.assertEqual(
            {"object_class_program_activity", "award_financial"},
            {row.get("submissionType") for row in downloads},
        )
        for row in downloads:
            self.assertEqual("finished", row.get("status"))
            self.assertRegex(row.get("archiveSha256", ""), r"^[0-9a-f]{64}$")
            self.assertIsInstance(row.get("statusRowCount"), int)
            self.assertGreaterEqual(row["statusRowCount"], 0)
            filters = (row.get("acceptedRequestScope") or {}).get("filters") or {}
            self.assertEqual("7008", str(filters.get("federal_account")))
            self.assertEqual(2024, filters.get("fy"))
            self.assertEqual(first_period, filters.get("period"))

        snapshots = evidence.get("accountSnapshots") or []
        self.assertEqual({2024, 2025, 2026}, {
            row.get("fiscalYear") for row in snapshots
        })
        by_fy = {row["fiscalYear"]: row for row in snapshots}
        years = baseline["fiscalYears"]
        for fiscal_year in (2024, 2025, 2026):
            snapshot = by_fy[fiscal_year]
            self.assertTrue(snapshot.get("retrievedAt"))
            self.assertTrue(str(snapshot.get("url", "")).startswith(
                "https://api.usaspending.gov/api/v2/federal_accounts/075-1000/"
            ))
            self.assertEqual(
                years[str(fiscal_year)]["obligationsCents"],
                snapshot.get("obligationsCents"),
            )
        return evidence

    def _aspr_result_ready(self):
        account, baseline = self._aspr_baseline()
        years = baseline["fiscalYears"]
        if not all(
                isinstance(years[str(fy)].get("obligationsCents"), int)
                for fy in (2024, 2025, 2026)):
            return False
        self._aspr_result_evidence(account, baseline)
        first_period = account["availability"]["firstFiscalYearPeriod"]
        self.assertEqual(first_period, years["2024"].get("firstPeriod"))
        self.assertEqual("complete" if first_period == 2 else "partial",
                         years["2024"]["status"])
        self.assertEqual("complete", years["2025"]["status"])
        self.assertEqual("partial", years["2026"]["status"])
        self.assertEqual(9, years["2026"]["asOfPeriod"])
        self.assertNotIn("pending", baseline["source"].lower())
        self.assertIn(ASPR_EVIDENCE.name, baseline["source"])
        return True

    def test_aspr_is_probe_commit_p_or_evidence_backed_result_commit_r(self):
        account, baseline = self._aspr_baseline()
        baseline = json.loads((REPO / account["baseline"]).read_text())
        self.assertEqual(2, baseline["schemaVersion"])
        self.assertEqual("075-1000", baseline["federalAccount"])
        years = baseline["fiscalYears"]
        self.assertEqual({str(fy) for fy in range(2015, 2027)}, set(years))
        for fy in range(2017, 2024):
            self.assertEqual(
                {"status": "unavailable",
                 "reason": "USAspending federal-account snapshot has no balance "
                           "or child TAS for this fiscal year"},
                years[str(fy)],
            )
        if "obligationsCents" not in years["2024"]:
            self.assertEqual(
                "USAspending federal account fiscal-year snapshots (GTAS/File A); "
                "FY2024 P2 calibration pending",
                baseline["source"],
            )
            self.assertFalse(ASPR_EVIDENCE.exists())
            self.assertEqual(
                {"status": "partial", "asOfPeriod": 2, "firstPeriod": 2},
                years["2024"],
            )
            for fy in (2025, 2026):
                self.assertEqual("unavailable", years[str(fy)]["status"])
                self.assertIn(
                    "multi-year release is blocked", years[str(fy)]["reason"]
                )
            probe = plan(
                REPO, mode="custom", selectors=account["path"],
                from_fy=2024, to_fy=2024, current_period=2,
            )["include"]
            self.assertEqual([(2024, 2)], [
                (row["fiscalYear"], row["period"]) for row in probe
            ])
            self.assertEqual(1, len(plan(
                REPO, mode="full", selectors=account["path"]
            )["include"]))
            with self.assertRaisesRegex(
                    ValueError, "FY2025 is not source-available"):
                plan(
                    REPO, mode="custom", selectors=account["path"],
                    from_fy=2024, to_fy=2026, current_period=9,
                )
        else:
            self.assertTrue(self._aspr_result_ready())
            jobs = plan(
                REPO, mode="custom", selectors=account["path"],
                from_fy=2024, to_fy=2026, current_period=9,
            )["include"]
            self.assertEqual([(2024, 12), (2025, 12), (2026, 9)], [
                (row["fiscalYear"], row["period"]) for row in jobs
            ])

    def _require_all_planned_pins(self, jobs):
        for job in jobs:
            baseline = json.loads((REPO / job["baseline"]).read_text())
            pin = baseline["fiscalYears"][str(job["fiscalYear"])]
            if "obligationsCents" not in pin:
                raise AssertionError(
                    f"{job['account']} FY{job['fiscalYear']} is preflight-required"
                )

    def test_full_planner_has_exact_jobs_for_current_stage(self):
        selectors = ",".join(self.accounts)
        jobs = plan(REPO, mode="full", selectors=selectors)["include"]
        aspr_job_count = 3 if self._aspr_result_ready() else 1
        self.assertEqual(
            aspr_job_count + 10 * (len(self.accounts) - 1), len(jobs)
        )
        by_account = {path: [] for path in self.accounts}
        for job in jobs:
            by_account[job["account"]].append(
                (job["fiscalYear"], job["period"])
            )
        for path, rows in by_account.items():
            if path == ASPR_PATH:
                expected = (
                    [(2024, 12), (2025, 12), (2026, 9)]
                    if aspr_job_count == 3 else [(2024, 2)]
                )
                self.assertEqual(expected, rows)
            else:
                self.assertEqual(
                    [(fy, 12) for fy in range(2017, 2026)] + [(2026, 9)],
                    rows,
                )
                self._require_all_planned_pins(
                    [job for job in jobs if job["account"] == path]
                )

    def _events(self, path, rows, period="FY2024P02"):
        account = self.accounts[path]
        scoped = []
        for index, row in enumerate(rows, start=1):
            scoped.append({
                "federal_account_symbol": account["federalAccount"],
                "obligations_incurred": f"{index}.00",
                **row,
            })
        values = parse_file_b_snapshot(
            scoped, account["federalAccount"], alias_map(account)
        )
        flows = file_b_period_events(
            {period: values}, account["federalAccount"]
        )
        events = combine_file_b_file_c(flows, [], account["federalAccount"])
        self.assertEqual(sum(range(1, len(rows) + 1)) * 100,
                         sum(row["amountCents"] for row in events))
        self.assertEqual(len(events), len({row["id"] for row in events}))
        return events

    def _require_paths(self, *paths):
        missing = [path for path in paths if path not in self.accounts]
        if missing:
            self.skipTest(f"later staged batch is not registered: {missing}")

    def test_va_legacy_clinical_science_and_current_csp_stay_distinct(self):
        self._require_paths("va/medical-prosthetic-research")
        events = self._events("va/medical-prosthetic-research", [
            {"program_activity_code": "0004",
             "program_activity_name": "CLINICAL SCIENCE RESEARCH"},
            {"program_activity_code": "0004",
             "program_activity_name": "CLINICAL SCIENCE RESEARCH (829)"},
            {"program_activity_reporting_key": "61VAU6S6K8K"},
        ])
        self.assertEqual({
            "CLINICAL SCIENCE RESEARCH",
            "CLINICAL SCIENCE RESEARCH (829)",
            "CLINICAL SCIENCE R&D AND CSP (829)",
        }, {row["programActivityName"] for row in events})
        self.assertEqual(3, len({row["_programActivityKey"] for row in events}))

    def test_dhs_legacy_and_current_organization_labels_stay_distinct(self):
        self._require_paths("dhs/cisa-rd", "dhs/cwmd-rd")
        cisa = self._events("dhs/cisa-rd", [
            {"program_activity_code": "0001",
             "program_activity_name": "CAS - CYBERSECURITY"},
            {"program_activity_code": "0003",
             "program_activity_name": "CAS - CYBERSECURITY"},
            {"program_activity_code": "0002",
             "program_activity_name": "CAS - INFRASTRUCTURE PROTECTION"},
            {"program_activity_reporting_key": "5ZD2V505R8T"},
            {"program_activity_reporting_key": "5TB2MGKNLHN"},
            {"program_activity_reporting_key": "5TB2MGKNLHM"},
        ])
        self.assertEqual({
            "CAS - CYBERSECURITY", "CAS - INFRASTRUCTURE PROTECTION",
            "CAS - INFRASTRUCTURE SECURITY R&D", "CAS - RISK MANAGEMENT R&D",
        }, {row["programActivityName"] for row in cisa})
        self.assertEqual(4, len({row["_programActivityKey"] for row in cisa}))

        pairs = [
            ("0001", "RESEARCH, DEVELOPMENT, AND OPERATIONS"),
            ("0001", "CAS - RESEARCH AND DEVELOPMENT"),
            ("0002", "CAS - ARCHITECTURE PLANNING AND ANALYSIS"),
            ("0002", "ARCHITECTURE PLANNING AND ANALYSIS"),
            ("0003", "TRANSFORMATIONAL RESEARCH AND DEVELOPMENT"),
            ("0003", "CAS - TRANSFORMATIONAL RESEARCH AND DEVELOPMENT"),
            ("0004", "DETECTION CAPABILITY DEVELOPMENT"),
            ("0004", "CAS - DETECTION CAPABILITY DEVELOPMENT"),
            ("0005", "CAS - DETECTION CAPABILITY ASSESSMENTS"),
            ("0005", "DETECTION CAPABILITY ASSESSMENTS"),
            ("0006", "CAS - NUCLEAR FORENSICS"),
            ("0006", "NUCLEAR FORENSICS"),
        ]
        cwmd = self._events("dhs/cwmd-rd", [
            {"program_activity_code": code, "program_activity_name": name}
            for code, name in pairs
        ])
        self.assertEqual({name for _, name in pairs},
                         {row["programActivityName"] for row in cwmd})
        self.assertEqual(12, len({row["_programActivityKey"] for row in cwmd}))

    def test_cisa_fy2020_optional_program_activity_matches_raw_evidence(self):
        self._require_paths("dhs/cisa-rd")
        account = self.accounts["dhs/cisa-rd"]
        amounts = ["-28831.98", "-698.55", "1398848.20", "605844.00",
                   "469224.00", "1200000.00"]
        rows = [{
            "submission_period": f"FY2020P{period:02}",
            "federal_account_symbol": "070-0805",
            "program_activity_code": "OPTN",
            "program_activity_name": "FIELD IS OPTIONAL PRIOR TO FY21",
            "transaction_obligated_amount": amount,
            "award_unique_key": f"CISA-FY2020-RAW-{index}",
        } for index, (period, amount) in enumerate(
            zip([11, 12, 8, 3, 10, 10], amounts), start=1
        )]
        events = parse_file_c({
            "assistance.csv": [],
            "contracts.csv": rows,
            "unlinked.csv": [],
        }, "070-0805", alias_map(account))
        self.assertEqual(364438567, sum(row["amountCents"] for row in events))
        self.assertEqual({"Unknown / other"}, {
            row["programActivityName"] for row in events
        })
        self.assertEqual(1, len({row["_programActivityKey"] for row in events}))

    def test_science_technology_fy2020_optional_pa_matches_raw_evidence(self):
        self._require_paths("dhs/science-technology-rd")
        account = self.accounts["dhs/science-technology-rd"]
        member_shapes = {
            "assistance.csv": (21, "31221080.56"),
            "contracts.csv": (332, "255127010.71"),
            "unlinked.csv": (2, "2652857.20"),
        }
        members = {}
        for member, (count, subtotal) in member_shapes.items():
            amounts = [subtotal, *(["0.00"] * (count - 1))]
            members[member] = [{
                "submission_period": "FY2020P12",
                "federal_account_symbol": "070-0803",
                "program_activity_code": "OPTN",
                "program_activity_name": "FIELD IS OPTIONAL PRIOR TO FY21",
                "transaction_obligated_amount": amount,
                "award_unique_key": f"ST-FY2020-{member}-{index}",
            } for index, amount in enumerate(amounts, start=1)]

        events = parse_file_c(
            members, "070-0803", alias_map(account)
        )
        self.assertEqual(355, sum(len(rows) for rows in members.values()))
        self.assertEqual(3, len(events))
        self.assertEqual(28900094847, sum(
            row["amountCents"] for row in events
        ))
        self.assertEqual({"Unknown / other"}, {
            row["programActivityName"] for row in events
        })
        self.assertEqual(1, len({
            row["_programActivityKey"] for row in events
        }))

    def test_cisa_fy2026_park_matches_raw_and_official_mapping_evidence(self):
        self._require_paths("dhs/cisa-rd")
        account = self.accounts["dhs/cisa-rd"]
        parks = (
            ["5TB2MGKNLHM"] * 3
            + ["5TB2MGKNLHN"] * 4
            + ["5ZD2V505R8T"] * 2
        )
        rows = [{
            "submission_period": "FY2026P02",
            "federal_account_symbol": "070-0805",
            "program_activity_reporting_key": park,
            "program_activity_code": "",
            "program_activity_name": "",
            "obligations_incurred": "0.00",
        } for park in parks]
        snapshot = parse_file_b_snapshot(
            rows, "070-0805", alias_map(account)
        )
        events = file_b_period_events(
            {"FY2026P02": snapshot}, "070-0805"
        )
        self.assertEqual(3, len(events))
        self.assertEqual(0, sum(row["amountCents"] for row in events))
        cyber = [
            row for row in events
            if row["programActivityReportingKey"] == "5ZD2V505R8T"
        ]
        self.assertEqual(1, len(cyber))
        self.assertEqual("CAS - CYBERSECURITY", cyber[0]["programActivityName"])

    def test_cwmd_fy2020_optional_program_activity_matches_raw_evidence(self):
        self._require_paths("dhs/cwmd-rd")
        account = self.accounts["dhs/cwmd-rd"]
        member_shapes = {
            "assistance.csv": (5, "-753666.02"),
            "contracts.csv": (92, "47514746.48"),
            "unlinked.csv": (5, "3806367.91"),
        }
        members = {}
        for member, (count, subtotal) in member_shapes.items():
            amounts = [subtotal, *(["0.00"] * (count - 1))]
            members[member] = [{
                "submission_period": "FY2020P12",
                "federal_account_symbol": "070-0860",
                "program_activity_code": "OPTN",
                "program_activity_name": "FIELD IS OPTIONAL PRIOR TO FY21",
                "transaction_obligated_amount": amount,
                "award_unique_key": f"CWMD-FY2020-{member}-{index}",
            } for index, amount in enumerate(amounts, start=1)]

        events = parse_file_c(
            members, "070-0860", alias_map(account)
        )
        self.assertEqual(102, sum(len(rows) for rows in members.values()))
        self.assertEqual(3, len(events))
        self.assertEqual(5056744837, sum(
            row["amountCents"] for row in events
        ))
        self.assertEqual({"Unknown / other"}, {
            row["programActivityName"] for row in events
        })
        self.assertEqual(1, len({
            row["_programActivityKey"] for row in events
        }))


    def test_dot_reused_codes_and_rolling_stock_are_collision_safe(self):
        self._require_paths(
            "dot/ost-research-technology",
            "dot/faa-research-engineering-development", "dot/fra-rd",
        )
        ost = self._events("dot/ost-research-technology", [
            {"program_activity_code": "0002",
             "program_activity_name": "ALTERNATIVE FUELS RESEARCH & DEVELOPMENT"},
            {"program_activity_code": "0002",
             "program_activity_name": "HIGHLY AUTOMATED SYSTEMS SAFETY CENTER OF EXCELLENCE"},
            {"program_activity_code": "0004",
             "program_activity_name": "ADVANCED RESEARCH PROJECTS - INFRASTRUCTURE"},
            {"program_activity_code": "0004",
             "program_activity_name": "ADVANCES RESEARCH PROJECTS - INFRASTRUCTURE"},
            {"program_activity_code": "0004",
             "program_activity_name": "NATIONWIDE DIFFERENTIAL GLOBAL POSITIONING SYSTEM"},
        ])
        self.assertEqual(4, len({row["_programActivityKey"] for row in ost}))
        self.assertIn(
            "ADVANCED RESEARCH PROJECTS - INFRASTRUCTURE",
            {row["programActivityName"] for row in ost},
        )
        self.assertNotIn(
            "ADVANCES RESEARCH PROJECTS - INFRASTRUCTURE",
            {row["programActivityName"] for row in ost},
        )
        self.assertEqual(
            "Research and Technology, Office of the Secretary",
            self.accounts["dot/ost-research-technology"]["name"],
        )
        self.assertNotIn(
            self.accounts["dot/ost-research-technology"]["name"],
            {row["programActivityName"] for row in ost},
        )

        faa = self._events("dot/faa-research-engineering-development", [
            {"program_activity_code": "0012",
             "program_activity_name": "ECONOMIC COMPETITIVENESS"},
            {"program_activity_code": "0012",
             "program_activity_name": "IMPROVE EFFICIENCY"},
        ])
        self.assertEqual(2, len({row["_programActivityKey"] for row in faa}))

        fra = self._events("dot/fra-rd", [
            {"program_activity_code": "0013",
             "program_activity_name": "ROLLING STOCK PROGRAM"},
            {"program_activity_code": "0003",
             "program_activity_name": "ROLLING STOCK AND COMPONENTS"},
        ])
        self.assertEqual(2, len({row["_programActivityKey"] for row in fra}))

    def test_ies_pac_park_transition_and_admin_identity(self):
        self._require_paths("ed/ies")
        account = self.accounts["ed/ies"]
        aliases = alias_map(account)
        pac = parse_file_b_snapshot([{
            "federal_account_symbol": "091-1100",
            "program_activity_code": "0001",
            "program_activity_name": "RESEARCH, DEVELOPMENT, AND DISSEMINATION",
            "obligations_incurred": "1.00",
        }], "091-1100", aliases)
        park = parse_file_b_snapshot([{
            "federal_account_symbol": "091-1100",
            "program_activity_reporting_key": "5ZCP71WLXTR",
            "obligations_incurred": "1.00",
        }], "091-1100", aliases)
        self.assertEqual(next(iter(pac))[0], next(iter(park))[0])
        self.assertEqual(next(iter(pac))[2], next(iter(park))[2])

        admin = self._events("ed/ies", [
            {"program_activity_reporting_key": "EX202500309838"},
            {"program_activity_reporting_key": "5ZCP71WLXTR"},
        ], period="FY2026P09")
        self.assertEqual({"IES PROGRAM ADMIN", "RESEARCH, DEVELOPMENT, AND DISSEMINATION"},
                         {row["programActivityName"] for row in admin})
        self.assertEqual("Institute of Education Sciences", account["name"])

    def test_ahrq_bls_and_ojp_boundaries_remain_visible(self):
        self._require_paths(
            "hhs/ahrq", "dol/bls", "doj/ojp-research-evaluation-statistics",
        )
        ahrq = self._events("hhs/ahrq", [
            {"program_activity_code": "0000", "program_activity_name": "UNKNOWN/OTHER"},
            {"program_activity_code": "0000", "program_activity_name": "ZERO OBLIGATION"},
            {"program_activity_reporting_key": "5ZC7PGQTUHX"},
            {"program_activity_code": "0804",
             "program_activity_name": "MEDICAL EXPENDITURE PANEL SURVEY (REIMBURSABLE)"},
            {"program_activity_code": "0805",
             "program_activity_name": "AHRQ PROGRAM SUPPORT (REIMBURSABLE)"},
        ])
        self.assertEqual(4, len({row["_programActivityKey"] for row in ahrq}))

        bls = self._events("dol/bls", [
            {"program_activity_code": "0000", "program_activity_name": "UNKNOWN"},
            {"program_activity_code": "0000", "program_activity_name": "UNKNOWN/OTHER"},
            {"program_activity_code": "0000", "program_activity_name": "UNKNOWN/OTHERS"},
            {"program_activity_code": "9999", "program_activity_name": "EMERGENCY PAID LEAVE"},
            {"program_activity_code": "EPL1", "program_activity_name": "EMERGENCY PAID LEAVE"},
        ])
        self.assertEqual(3, len({row["_programActivityKey"] for row in bls}))
        self.assertNotIn("Research", self.accounts["dol/bls"]["name"])

        ojp = self._events("doj/ojp-research-evaluation-statistics", [
            {"program_activity_reporting_key": "PRE2018"},
            {"program_activity_reporting_key": "5ZCBB3MT1CU"},
            {"program_activity_reporting_key": "5ZCBB3MT1CT"},
        ])
        self.assertEqual({
            "ACTIVITY FROM OBLIGATION BEFORE FY 2018: PROGRAM ACTIVITY NOT SPECIFIED",
            "BUREAU OF JUSTICE STATISTICS", "NATIONAL INSTITUTE OF JUSTICE",
        }, {row["programActivityName"] for row in ojp})
        self.assertEqual(
            "Research, Evaluation, and Statistics, Office of Justice Programs",
            self.accounts["doj/ojp-research-evaluation-statistics"]["name"],
        )

    def test_aspr_is_not_barda_or_project_bioshield(self):
        account = self.accounts[ASPR_PATH]
        joined = " ".join(
            [account["name"]]
            + [row["name"] for row in account["programActivities"]]
        ).lower()
        self.assertNotIn("barda", joined)
        self.assertNotIn("bioshield", joined)
        rows = json.loads(
            (REPO / "reference" / "aaas_federal_account_crosswalk.json").read_text()
        )["rows"]
        bioshield = next(row for row in rows
                         if row.get("aaas_row_key") == "OtherHHS::Project BioShield")
        self.assertEqual("provisional", bioshield["status"])

    def test_later_scaffolds_require_result_and_atomic_aspr_store(self):
        later = set(self.accounts) - {ASPR_PATH}
        if not later:
            return
        self.assertTrue(
            self._aspr_result_ready(),
            "commit R must precede every VA-or-later scaffold commit",
        )
        account, baseline = self._aspr_baseline()
        years = baseline["fiscalYears"]
        store = REPO / "data" / "obligations" / ASPR_PATH
        manifest_path = store / "events" / "manifest.json"
        self.assertTrue(
            manifest_path.exists(),
            "the atomic FY2024-FY2026 ASPR data commit must precede later scaffolds",
        )
        manifest = json.loads(manifest_path.read_text())
        self.assertEqual("075-1000", manifest.get("federalAccount"))
        self.assertEqual([2024, 2025, 2026], manifest.get("fiscalYears"))
        partitions = {
            row.get("fiscalYear"): row for row in manifest.get("partitions") or []
        }
        self.assertEqual({2024, 2025, 2026}, set(partitions))
        for fiscal_year, partition in partitions.items():
            self.assertEqual("accepted", partition.get("collectionStatus"))
            self.assertRegex(partition.get("sha256", ""), r"^[0-9a-f]{64}$")
            event_path = store / "events" / partition["file"]
            provenance_path = store / "events" / partition["provenance"]
            self.assertTrue(event_path.exists())
            self.assertTrue(provenance_path.exists())
            provenance = json.loads(provenance_path.read_text())
            self.assertEqual(2, provenance.get("schemaVersion"))
            self.assertEqual("accepted", provenance.get("collectionStatus"))
            self.assertEqual(ASPR_PATH, provenance.get("accountPath"))
            self.assertEqual("075-1000", provenance.get("federalAccount"))
            self.assertEqual(fiscal_year, provenance.get("fiscalYear"))
            pin = years[str(fiscal_year)]
            self.assertEqual(
                pin["obligationsCents"],
                (provenance.get("normalized") or {}).get("netObligationsCents"),
            )
            self.assertEqual(
                pin["obligationsCents"],
                (provenance.get("baselinePin") or {}).get("obligationsCents"),
            )
            downloads = provenance.get("downloads") or []
            self.assertEqual(
                {"object_class_program_activity", "award_financial"},
                {row.get("submissionType") for row in downloads},
            )
            for row in downloads:
                self.assertEqual("finished", row.get("status"))
                filters = (
                    (row.get("acceptedRequestScope") or {}).get("filters") or {}
                )
                self.assertEqual("7008", str(filters.get("federal_account")))
                self.assertEqual(fiscal_year, filters.get("fy"))

        dashboard = json.loads((store / "dashboard.json").read_text())
        self.assertEqual([], dashboard.get("warnings"))
        self.assertTrue(dashboard.get("dataComplete"))
        self.assertEqual(2026, dashboard.get("currentFY"))
        self.assertEqual("FY2026P09", dashboard.get("asOfPeriod"))

    def test_scaffold_does_not_claim_unmaterialized_later_stores(self):
        for path in set(ACCOUNT_META) - set(self.accounts):
            self.assertFalse((REPO / "data" / "obligations" / path).exists())


if __name__ == "__main__":
    unittest.main()
