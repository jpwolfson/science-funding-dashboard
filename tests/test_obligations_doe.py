"""Phase 3.2d DOE account-onboarding contracts."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from adapters.usaspending_obligations import alias_map
from scripts.plan_obligation_refresh import plan
from scripts.pull_obligation_account import pull


REPO = Path(__file__).resolve().parent.parent

EXPECTED = {
    "doe/arpa-e": ("089-0337", "Advanced Research Projects Agency-Energy", 4),
    "doe/eere": ("089-0321", "Energy Efficiency and Renewable Energy", 25),
    "doe/oced": ("089-2297", "Clean Energy Demonstrations", 16),
    "doe/fossil-energy": ("089-0213", "Fossil Energy", 25),
    "doe/electricity": ("089-0318", "Electricity", 19),
    "doe/ceser": (
        "089-2250", "Cybersecurity, Energy Security, and Emergency Response", 11,
    ),
    "doe/nuclear-energy": ("089-0319", "Nuclear Energy", 25),
    "doe/nnsa-weapons-activities": ("089-0240", "Weapons Activities", 23),
    "doe/nnsa-defense-nuclear-nonproliferation": (
        "089-0309", "Defense Nuclear Nonproliferation", 14,
    ),
    "doe/eia": ("089-0216", "Energy Information Administration", 4),
}

PARK_ONLY_IDENTITIES = {
    "doe/eere": {"63YPT7SFFAZ"},
    "doe/fossil-energy": {"5UWQ6Q4BYMT"},
    "doe/electricity": {"63YPT7S7RDC"},
    "doe/ceser": {"63YPTC2RBEP"},
    "doe/nuclear-energy": {"63YPT7SACCH"},
    "doe/nnsa-defense-nuclear-nonproliferation": {"608PP9VRRFG"},
}

AMBIGUOUS_SOURCE_CODES = {
    "doe/eere": {"0204"},
    "doe/fossil-energy": {"0006", "0020"},
    "doe/electricity": {"0013", "0016"},
    "doe/ceser": {"0010"},
    "doe/nuclear-energy": {"0301"},
    "doe/eia": {"0001"},
}

# Official File B pairs that either collide or record a reviewed code/name
# transition. Exact pairs are intentional: the adapter must never choose a
# canonical identity from a reused code alone.
SOURCE_PAIR_EXPECTATIONS = {
    "doe/eere": {
        ("0204", "Energy Delivery Grid Operations Technology"):
            "energy-delivery-grid-operations-technology",
        ("0204", "Federal Energy Management Program"):
            "federal-energy-management-program",
        ("0401", "Infrastructure Investment and Job Act"):
            "infrastructure-investment-and-jobs-act",
    },
    "doe/oced": {
        ("0010", "Clean Energy Demonstrations"):
            "clean-energy-demonstrations-base-program",
        ("0011", "Program Direction"): "program-direction-base",
        ("0033", "Program Direction-IIJA"): "program-direction-iija",
    },
    "doe/fossil-energy": {
        ("0006", "Carbon Utilization"): "carbon-utilization",
        ("0006", "Carbon Transport and Storage"):
            "carbon-transport-and-storage",
        ("0012", "Program Direction - Management"): "program-direction",
        ("0012", "Program Direction"): "program-direction",
        ("0020", "Natural Gas Technologies"): "natural-gas-technologies",
        ("0020", "Inflation Reduction Act"): "inflation-reduction-act",
        ("0022", "Supercritical Transformational Electric Power Generation"):
            "step-supercritical-co2",
        ("0040", "Energy Asset Transformation"):
            "energy-asset-transformation",
        ("0050", "Inflation Reduction Act"): "inflation-reduction-act",
        ("0801", "Fossil Energy Research and Development (Reimbursable)"):
            "reimbursable",
        ("0801", "Unavailable"): "reimbursable",
    },
    "doe/electricity": {
        ("0011", "Clean Energy Transmission and Reliability"):
            "transmission-reliability-and-resiliency",
        ("0012", "Smart Grid R&D"): "resilient-distribution-systems",
        ("0013", "Cybersecurity for Energy Delivery Systems"):
            "cybersecurity-for-energy-delivery-systems",
        ("0013", "DCEI Energy Mission Assurance"):
            "dcei-energy-mission-assurance",
        ("0016", "Cybersecurity for Energy Delivery Systems"):
            "cybersecurity-for-energy-delivery-systems",
        ("0016", "DCEI Energy Mission Assurance"):
            "dcei-energy-mission-assurance",
        ("0030", "National Electricity Delivery"):
            "transmission-permitting-and-technical-assistance",
        ("0041", "Electricity, Infrastructure  Investment and Jobs Act"):
            "electricity-infrastructure-investment-and-jobs-act",
    },
    "doe/ceser": {
        ("0010", "Cybersecurity for Energy Delivery Systems"):
            "cybersecurity-for-energy-delivery-systems",
        ("0010", "Risk Management Technology and Tools (CEDS)"):
            "risk-management-technology-and-tools",
        ("0013", "DCEI Energy Mission Assurance"):
            "dcei-energy-mission-assurance",
    },
    "doe/nuclear-energy": {
        ("0010", "Naval Reactors Development"):
            "naval-reactors-development",
        ("0032", "Reactor Concepts RD&D"): "reactor-concepts-rd-and-d",
        ("0032", "Reactor Concepts RD&D (RC RD&D)"):
            "reactor-concepts-rd-and-d",
        ("0034", "Advanced Reactors Demonstration Program"):
            "advanced-reactors-demonstration-program-ardp",
        ("0041", "Fuel Cycle R&D"): "fuel-cycle-r-and-d",
        ("0041", "Fuel Cycle R&D (FC R&D)"): "fuel-cycle-r-and-d",
        ("0042", "Integrated University Program"):
            "nuclear-leadership-development-program",
        ("0042", "University Nuclear Leadership Program"):
            "nuclear-leadership-development-program",
        ("0042", "Nuclear Leadership Development Program"):
            "nuclear-leadership-development-program",
        ("0043", "Nuclear Energy Enabling Technologies R&D"):
            "nuclear-energy-enabling-technologies-neet",
        ("0043", "Nuclear Energy Enabling Technologies (NEET)"):
            "nuclear-energy-enabling-technologies-neet",
        ("0301", "Radiological Facilities Management"):
            "radiological-facilities-management",
        ("0301", "ORNL Infrastructure Facilities O&M"):
            "ornl-infrastructure-facilities-o-and-m",
    },
    "doe/nnsa-weapons-activities": {
        ("0075", "Nuclear Counterterrorism Incident Response"):
            "nuclear-counterterrorism-and-incident-response",
        ("0150", "Nuclear Counterterrorism Incident Response"):
            "nuclear-counterterrorism-and-incident-response",
        ("0170", "Site Stewardship"): "site-stewardship",
        ("0179", "Information Technology and Cybersecurity"):
            "information-technology-and-cybersecurity",
        ("0180", "Defense Nuclear Security"): "defense-nuclear-security",
        ("0183", "Legacy Contractor Pensions"):
            "legacy-contractor-pensions",
        ("0240", "Weapons Activities"): "weapons-activities-direct",
    },
    "doe/nnsa-defense-nuclear-nonproliferation": {
        ("0050", "U.S. Surplus Fissile Materials Disposition"):
            "fissile-materials-disposition",
        ("0075", "Nuclear Counterterrorism Incident Response"):
            "nuclear-counterterrorism-and-incident-response",
        ("0150", "Nuclear Counterterrorism Incident Response"):
            "nuclear-counterterrorism-and-incident-response",
        ("0309", "Defense Nuclear Nonproliferation"):
            "defense-nuclear-nonproliferation-direct",
    },
    "doe/eia": {
        ("0001", "National Energy Information System"):
            "national-energy-information-system",
        ("0001", "Obligations by Program Activity"):
            "obligations-by-program-activity",
        ("0801", "Reimbursable Work"): "reimbursable-program-activity",
    },
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
                slugs = [row["slug"] for row in activities]
                canonical_pairs = {
                    (str(row["code"]).zfill(4), row["name"].strip().lower())
                    for row in activities
                }
                source_pairs = [
                    (str(pair["code"]).zfill(4), pair["name"].strip().lower())
                    for row in activities
                    for pair in [
                        {"code": row["code"], "name": row["name"]},
                        *(row.get("codeNameAliases") or []),
                    ]
                ]
                parks = [
                    park
                    for row in activities
                    for park in [row.get("park"), *(row.get("parkAliases") or [])]
                    if park
                ]
                self.assertEqual(len(activities), len(canonical_pairs))
                self.assertEqual(len(slugs), len(set(slugs)))
                self.assertEqual(len(parks), len(set(parks)))
                self.assertEqual(len(source_pairs), len(set(source_pairs)))
                self.assertIn("0000", {row["code"] for row in activities})
                aliases = alias_map(account)
                for activity in activities:
                    pair = (
                        "code-name",
                        str(activity["code"]).zfill(4),
                        activity["name"].strip().lower(),
                    )
                    self.assertEqual(activity["slug"], aliases[pair]["slug"])
                    if activity["park"]:
                        self.assertEqual(
                            activity["slug"],
                            aliases[("park", activity["park"])]["slug"],
                        )

    def test_park_only_identities_are_not_silently_forced_into_legacy_codes(self):
        for path, expected in PARK_ONLY_IDENTITIES.items():
            with self.subTest(path=path):
                activities = self.accounts[path]["programActivities"]
                actual = {
                    row["code"] for row in activities
                    if len(row["code"]) > 4
                    and row["code"] == row["park"]
                    and not any(
                        len(str(alias["code"])) == 4
                        for alias in row.get("codeNameAliases", [])
                    )
                }
                self.assertEqual(expected, actual)

    def test_reviewed_code_name_pairs_resolve_to_the_intended_identity(self):
        for path, pairs in SOURCE_PAIR_EXPECTATIONS.items():
            aliases = alias_map(self.accounts[path])
            for (code, name), expected_slug in pairs.items():
                with self.subTest(path=path, code=code, name=name):
                    identity = aliases[("code-name", code, name.strip().lower())]
                    self.assertEqual(expected_slug, identity["slug"])

    def test_reused_source_codes_cannot_fall_back_to_code_only(self):
        for path, codes in AMBIGUOUS_SOURCE_CODES.items():
            aliases = alias_map(self.accounts[path])
            for code in codes:
                with self.subTest(path=path, code=code):
                    self.assertNotIn(("code", code), aliases)

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
        weapons_aliases = alias_map(self.accounts["doe/nnsa-weapons-activities"])
        nonproliferation_aliases = alias_map(
            self.accounts["doe/nnsa-defense-nuclear-nonproliferation"]
        )
        self.assertEqual(
            "weapons-activities-direct",
            weapons_aliases[("code-name", "0240", "weapons activities")]["slug"],
        )
        self.assertEqual(
            "defense-nuclear-nonproliferation-direct",
            nonproliferation_aliases[
                ("code-name", "0309", "defense nuclear nonproliferation")
            ]["slug"],
        )

    def test_full_backfill_plan_replaces_every_partial_scaffold(self):
        expected_first_fy = {
            "doe/oced": 2022,
            "doe/ceser": 2019,
        }
        for path in EXPECTED:
            with self.subTest(path=path):
                jobs = plan(REPO, mode="full", selectors=path)["include"]
                first_fy = expected_first_fy.get(path, 2017)
                self.assertEqual(list(range(first_fy, 2027)), [
                    row["fiscalYear"] for row in jobs
                ])
                self.assertEqual(12, jobs[0]["period"])
                self.assertEqual(9, jobs[-1]["period"])

                baseline = json.loads((REPO / self.accounts[path]["baseline"]).read_text())
                self.assertEqual("unavailable", baseline["fiscalYears"]["2015"]["status"])
                self.assertEqual("unavailable", baseline["fiscalYears"]["2016"]["status"])
                for fiscal_year in range(2017, first_fy):
                    self.assertEqual(
                        "unavailable",
                        baseline["fiscalYears"][str(fiscal_year)]["status"],
                    )
                self.assertEqual(
                    6 if first_fy == 2017 else 2,
                    baseline["fiscalYears"][str(first_fy)]["firstPeriod"],
                )
                self.assertEqual(
                    12, baseline["fiscalYears"][str(first_fy)]["asOfPeriod"]
                )
                self.assertEqual("partial", baseline["fiscalYears"]["2026"]["status"])
                self.assertEqual(9, baseline["fiscalYears"]["2026"]["asOfPeriod"])

                store = REPO / "data" / "obligations" / path / "events"
                if store.exists():
                    for fiscal_year in range(first_fy, 2027):
                        self.assertIn(
                            "obligationsCents",
                            baseline["fiscalYears"][str(fiscal_year)],
                            f"{path} FY{fiscal_year} retained an unfilled scaffold",
                        )

        # The DOE prefix also includes the existing Office of Science
        # regression account; the ten Phase 3.2d accounts themselves plan 93.
        self.assertEqual(
            103, len(plan(REPO, mode="full", selectors="doe")["include"])
        )

    def test_frozen_matrix_unavailable_year_is_explicit_noop(self):
        account = self.accounts["doe/ceser"]
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "partition"
            with patch("scripts.pull_obligation_account.resolve_account") as resolve:
                pull(account, [2017], repo=REPO, rollup=False,
                     partition_output=output)
            resolve.assert_not_called()
            descriptor = json.loads((output / "partition.json").read_text())
            self.assertEqual([], descriptor["fiscalYears"])
            self.assertEqual([2017], descriptor["skippedFiscalYears"])
            self.assertEqual([], descriptor["files"])


if __name__ == "__main__":
    unittest.main()
