"""Phase 3.2d DOE account-onboarding contracts."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from adapters.obligation_common import load_store
from adapters.usaspending_obligations import (
    alias_map, combine_file_b_file_c, file_b_period_events,
    parse_file_b_snapshot,
)
from scripts.plan_obligation_refresh import plan
from scripts.pull_obligation_account import pull


REPO = Path(__file__).resolve().parent.parent

EXPECTED = {
    "doe/arpa-e": ("089-0337", "Advanced Research Projects Agency-Energy", 4),
    "doe/eere": ("089-0321", "Energy Efficiency and Renewable Energy", 25),
    "doe/oced": ("089-2297", "Clean Energy Demonstrations", 21),
    "doe/fossil-energy": ("089-0213", "Fossil Energy", 30),
    "doe/electricity": ("089-0318", "Electricity", 19),
    "doe/ceser": (
        "089-2250", "Cybersecurity, Energy Security, and Emergency Response", 11,
    ),
    "doe/nuclear-energy": ("089-0319", "Nuclear Energy", 26),
    "doe/nnsa-weapons-activities": ("089-0240", "Weapons Activities", 23),
    "doe/nnsa-defense-nuclear-nonproliferation": (
        "089-0309", "Defense Nuclear Nonproliferation", 17,
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
        ("0018", "Energy Delivery Grid Operations Technology"):
            "energy-delivery-grid-operations-technology",
        ("0204", "Energy Delivery Grid Operations Technology"):
            "energy-delivery-grid-operations-technology",
        ("0204", "Federal Energy Management Program"):
            "federal-energy-management-program",
        ("0401", "Infrastructure Investment and Job Act"):
            "infrastructure-investment-and-jobs-act",
    },
    "doe/oced": {
        ("0008", "Energy Justice and Equity"):
            "energy-justice-and-equity",
        ("0009", "Chief Financial Officer"):
            "chief-financial-officer",
        ("0010", "Clean Energy Demonstrations"):
            "clean-energy-demonstrations-base-program",
        ("0011", "Program Direction"): "program-direction-base",
        ("0033", "Program Direction-IIJA"): "program-direction-iija",
    },
    "doe/fossil-energy": {
        ("0023", "Cross Cutting Research"): "cross-cutting-research",
        ("0006", "Carbon Utilization"): "carbon-utilization",
        ("0006", "Carbon Transport and Storage"):
            "carbon-transport-and-storage",
        ("0012", "Program Direction - Management"): "program-direction",
        ("0012", "Program Direction"): "program-direction",
        ("0020", "Natural Gas Technologies"): "natural-gas-technologies",
        ("0020", "Legacy Management"): "legacy-management",
        ("0020", "Inflation Reduction Act"): "inflation-reduction-act",
        ("0301", "Program Direction & Support"):
            "program-direction-and-support-transient",
        ("0030", "Program Direction"): "program-direction-transient-0030",
        ("0033", "Program Direction-IIJA"):
            "program-direction-iija-transient",
        ("0001", "Other Defense Activities (Direct)"):
            "other-defense-activities-direct-transient",
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
        ("0033", "Program Direction-IIJA"):
            "program-direction-iija",
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

CESER_PARK_EXPECTATIONS = {
    "0000": "unknown-other",
    "5Q0QFJ08DGM": "cybersecurity-for-energy-delivery-systems",
    "5UWQ6UKQ7PC": "risk-management-technology-and-tools",
    "5Q0QFJ08DGW": "infrastructure-security-and-energy-restoration",
    "5UWQ6UKQ7PN": "response-and-restoration",
    "5UWQ6UKQ7PZ": "information-sharing-partnerships-and-exercises",
    "5WKQ40G9H6B": "ceser-infrastructure-investment-and-jobs-act",
}

EERE_PARK_EXPECTATIONS = {
    "0000": "unknown-other",
    "5ZCQYAUD7YP": "vehicle-technologies",
    "5ZCQYAUD7YQ": "bioenergy-technologies",
    "5ZCQYAUD7YR": "hydrogen-and-fuel-cell-technologies",
    "5ZCQYAUD7LN": "solar-energy",
    "5ZCQYAUD7LZ": "wind-energy",
    "5ZCQYAUD7LP": "water-power",
    "5ZCQYAUD7LQ": "geothermal-technologies",
    "5WKQ3U7VKZX": "renewable-energy-integration",
    "5ZCQYAUD7ZL": "advanced-manufacturing",
    "5ZCQYAUD7ZM": "building-technologies",
    "5ZCQYAUD7ZN": "weatherization-and-intergovernmental-activities",
    "61UPW3WW5MC": "energy-delivery-grid-operations-technology",
    "608Q103EU85": "advanced-materials-and-manufacturing-technologies",
    "608Q103EU86": "industrial-efficiency-and-decarbonization",
    "5ZCQYAUD7RJ": "program-direction-and-support",
    "5ZCQYAUD7RK": "strategic-programs",
    "5ZCQYAUD7RL": "facilities-and-infrastructure",
    "5WKQ3U7VKXN": "infrastructure-investment-and-jobs-act",
    "608Q103EUFC": "inflation-reduction-act",
    "608Q103EUFD": "manufacturing-and-energy-supply-chains",
    "5ZCQYAUD7ZZ": "federal-energy-management-program",
    "608Q103EUFF": "state-and-community-energy-programs",
    "5ZCQYAUD88Y": "energy-efficiency-and-renewable-energy-reimbursable",
    "63YPT7SFFAZ": "energy-efficiency-and-renewable-energy",
}

ELECTRICITY_PARK_EXPECTATIONS = {
    "5ZCQYAU5K1G": "research-and-development",
    "5ZCQYAU5K1H": "transmission-reliability-and-resiliency",
    "5Q0QFEPMTFQ": "resilient-distribution-systems",
    "5TAQ9MGNEAC": "dcei-energy-mission-assurance",
    "5ZCQYAU5K1K": "energy-storage",
    "5ZCQYAU5K1L": "transformer-resilience-and-advanced-components",
    "5ZCQYAU5K1J": "cybersecurity-for-energy-delivery-systems",
    "5WKQ3U7NX4T":
        "cyber-resilient-and-security-utility-communication-network",
    "5WKQ3U7NX4U": "energy-delivery-grid-operations-technology",
    "5WKQ3U7NX4V": "applied-grid-transformation-solutions",
    "5ZCQYAU5K1Q": "infrastructure-security-and-energy-restoration",
    "5ZCQYAU5K22": "transmission-permitting-and-technical-assistance",
    "5ZCQYAU5K2C": "program-direction",
    "5WKQ3U7NX5J":
        "electricity-infrastructure-investment-and-jobs-act",
    "608Q10378JS": "disaster-relief-supplemental",
    "608Q10378K2": "inflation-reduction-act",
    "5ZCQYAU5KZP": "reimbursable-work",
}

NNSA_NONPROLIFERATION_PARK_EXPECTATIONS = {
    "5UWPV26R8KX": "defense-nuclear-nonproliferation-direct",
    "5Q0Q5ZK9EDZ": "fissile-materials-disposition",
    "5RMQ2SFQNSN": "nuclear-counterterrorism-and-incident-response",
    "5ZCQ8KZQ505": "nonproliferation-and-arms-control",
    "5ZCQ8KZQ507": "nuclear-counterterrorism-and-incident-response",
    "5ZCQ8KZQ506": "nonproliferation-construction",
    "5ZCQ8KZQ504": "material-management-and-minimization",
    "5ZCQ8KZQ50H": "legacy-contractor-pensions",
    "608PP9VRRFG": "ukraine-supplemental",
    "5ZCQ8KZQ5LK": "gtri-international-contribution",
    "5ZCQ8KZQ503": "global-material-security",
    "5ZCQ8KZQ5LJ": "global-material-security-reimbursable",
    "5ZCQ8KZQ4WA":
        "defense-nuclear-nonproliferation-research-and-development",
    "5ZCQ8KZQ4X6": "international-materials-protection-and-cooperation",
    "5TAPXWB9X8W": "national-technical-nuclear-forensics",
    "5ZCQ8KZQ50C": "global-threat-reduction-initiative",
}

OCED_ADDITIONAL_PARK_EXPECTATIONS = {
    "5UWQ6UZ9RGM": "clean-energy-demonstrations-base-program",
    "63YPTC6AV5B": "clean-energy-demonstrations-base-program",
    "5UWQ6UZ9RGN": "program-direction-base",
    "63YPTC6AV6S": "chief-financial-officer",
    "63YPTC6AV5D": "clean-energy-demonstrations-iija",
    "63YPTC6AV5F": "clean-energy-demonstrations-ira",
    "63YPTC6AV5G": "program-direction-ira",
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

    def test_reviewed_ceser_park_transitions_resolve_exactly(self):
        aliases = alias_map(self.accounts["doe/ceser"])
        for park, expected_slug in CESER_PARK_EXPECTATIONS.items():
            with self.subTest(park=park):
                self.assertEqual(
                    expected_slug, aliases[("park", park)]["slug"]
                )

    def test_eere_fy2026_blank_name_parks_resolve_from_official_mapping(self):
        aliases = alias_map(self.accounts["doe/eere"])
        for park, expected_slug in EERE_PARK_EXPECTATIONS.items():
            with self.subTest(park=park):
                self.assertEqual(
                    expected_slug, aliases[("park", park)]["slug"]
                )

        # The accepted FY2026 P02 File B projection contains five identical
        # zero-dollar rows for this PARK and omits object-class columns. The
        # blank source name therefore must not create or infer an identity;
        # the official PARK mapping supplies the reviewed canonical identity.
        blank_rows = [{
            "submission_period": "FY2026P02",
            "federal_account_symbol": "089-0321",
            "program_activity_reporting_key": "5WKQ3U7VKZX",
            "program_activity_code": "",
            "program_activity_name": "",
            "obligations_incurred": "0.00",
        } for _ in range(5)]
        self.assertEqual(5, len(blank_rows))
        self.assertTrue(all("object_class_code" not in row for row in blank_rows))
        snapshot = parse_file_b_snapshot(blank_rows, "089-0321", aliases)
        self.assertEqual(
            {("0105", "Renewable Energy Integration", "5WKQ3U7VKZX"): 0},
            {
                (key[1], key[2], key[3]): amount
                for key, amount in snapshot.items()
            },
        )

        # Current PARK keys disambiguate the reused historical 0204 code:
        # grid operations and Federal Energy Management remain separate.
        collision_rows = [{
            "federal_account_symbol": "089-0321",
            "program_activity_reporting_key": "61UPW3WW5MC",
            "program_activity_code": "",
            "program_activity_name": "",
            "obligations_incurred": "1.25",
        }, {
            "federal_account_symbol": "089-0321",
            "program_activity_reporting_key": "5ZCQYAUD7ZZ",
            "program_activity_code": "",
            "program_activity_name": "",
            "obligations_incurred": "2.50",
        }]
        collision = parse_file_b_snapshot(
            collision_rows, "089-0321", aliases
        )
        self.assertEqual(
            {
                ("0204", "Energy Delivery Grid Operations Technology",
                 "61UPW3WW5MC"): 125,
                ("0452", "Federal Energy Management Program",
                 "5ZCQYAUD7ZZ"): 250,
            },
            {
                (key[1], key[2], key[3]): amount
                for key, amount in collision.items()
            },
        )

    def test_electricity_fy2026_blank_name_parks_resolve_officially(self):
        aliases = alias_map(self.accounts["doe/electricity"])
        for park, expected_slug in ELECTRICITY_PARK_EXPECTATIONS.items():
            with self.subTest(park=park):
                self.assertEqual(
                    expected_slug, aliases[("park", park)]["slug"]
                )

        # The exact accepted FY2026 P02 failure row is blank for both legacy
        # fields. The official PARK reference maps it to legacy PAC 0012.
        rows = [{
            "submission_period": "FY2026P02",
            "federal_account_symbol": "089-0318",
            "program_activity_reporting_key": "5Q0QFEPMTFQ",
            "program_activity_code": "",
            "program_activity_name": "",
            "obligations_incurred": "23000.00",
        }]
        snapshot = parse_file_b_snapshot(rows, "089-0318", aliases)
        self.assertEqual(
            {("0012", "Resilient Distribution Systems",
              "5Q0QFEPMTFQ"): 2_300_000},
            {
                (key[1], key[2], key[3]): amount
                for key, amount in snapshot.items()
            },
        )

    def test_remaining_doe_current_parks_resolve_from_official_mapping(self):
        for path, expected in (
            ("doe/nnsa-defense-nuclear-nonproliferation",
             NNSA_NONPROLIFERATION_PARK_EXPECTATIONS),
            ("doe/oced", OCED_ADDITIONAL_PARK_EXPECTATIONS),
        ):
            aliases = alias_map(self.accounts[path])
            for park, expected_slug in expected.items():
                with self.subTest(path=path, park=park):
                    self.assertEqual(
                        expected_slug, aliases[("park", park)]["slug"]
                    )
            rows = [{
                "submission_period": "FY2026P02",
                "federal_account_symbol":
                    self.accounts[path]["federalAccount"],
                "program_activity_reporting_key": park,
                "program_activity_code": "",
                "program_activity_name": "",
                "obligations_incurred": "0.00",
            } for park in expected]
            snapshot = parse_file_b_snapshot(
                rows, self.accounts[path]["federalAccount"], aliases
            )
            self.assertEqual(len(set(expected.values())), len(snapshot))

    def test_reused_source_codes_cannot_fall_back_to_code_only(self):
        for path, codes in AMBIGUOUS_SOURCE_CODES.items():
            aliases = alias_map(self.accounts[path])
            for code in codes:
                with self.subTest(path=path, code=code):
                    self.assertNotIn(("code", code), aliases)

    def test_fossil_fy2021_legacy_management_collision_is_distinct(self):
        aliases = alias_map(self.accounts["doe/fossil-energy"])
        rows = [
            {
                "submission_period": "FY2021P11",
                "federal_account_symbol": "089-0213",
                "program_activity_reporting_key": "",
                "program_activity_code": "0020",
                "program_activity_name": "NATURAL GAS TECHNOLOGIES",
                "obligations_incurred": "71151132.91",
            },
            {
                "submission_period": "FY2021P11",
                "federal_account_symbol": "089-0213",
                "program_activity_reporting_key": "",
                "program_activity_code": "0020",
                "program_activity_name": "LEGACY MANAGEMENT",
                "obligations_incurred": "0.00",
            },
            {
                "submission_period": "FY2024P12",
                "federal_account_symbol": "089-0213",
                "program_activity_reporting_key": "",
                "program_activity_code": "0020",
                "program_activity_name": "INFLATION REDUCTION ACT",
                "obligations_incurred": "1.00",
            },
        ]
        snapshot = parse_file_b_snapshot(rows, "089-0213", aliases)
        actual = {
            (key[0], key[1], key[2], key[3]): amount
            for key, amount in snapshot.items()
        }
        self.assertEqual(
            {
                (
                    "5ZCQYAMAF08:natural-gas-technologies",
                    "5ZCQYAMAF08",
                    "Natural Gas Technologies",
                    "5ZCQYAMAF08",
                ): 7_115_113_291,
                (
                    "00U3:legacy-management",
                    "00U3",
                    "Legacy Management",
                    "",
                ): 0,
                (
                    "0020:inflation-reduction-act",
                    "0020",
                    "Inflation Reduction Act",
                    "608Q0XTC3YY",
                ): 100,
            },
            actual,
        )
        self.assertNotIn(("code", "0020"), aliases)

    def test_fossil_interim_transient_rows_remain_exact_and_distinct(self):
        aliases = alias_map(self.accounts["doe/fossil-energy"])
        rows = [
            {
                "submission_period": "FY2022P02",
                "federal_account_symbol": "089-0213",
                "program_activity_reporting_key": "",
                "program_activity_code": "0012",
                "program_activity_name": "PROGRAM DIRECTION - MANAGEMENT",
                "obligations_incurred": "8495418.52",
            },
            {
                "submission_period": "FY2022P02",
                "federal_account_symbol": "089-0213",
                "program_activity_reporting_key": "",
                "program_activity_code": "0301",
                "program_activity_name": "PROGRAM DIRECTION & SUPPORT",
                "obligations_incurred": "-2120.80",
            },
            {
                "submission_period": "FY2023P02",
                "federal_account_symbol": "089-0213",
                "program_activity_reporting_key": "",
                "program_activity_code": "0030",
                "program_activity_name": "PROGRAM DIRECTION",
                "obligations_incurred": "-20.00",
            },
            {
                "submission_period": "FY2024P09",
                "federal_account_symbol": "089-0213",
                "program_activity_reporting_key": "",
                "program_activity_code": "0001",
                "program_activity_name": "OTHER DEFENSE ACTIVITIES (DIRECT)",
                "obligations_incurred": "0.00",
            },
            {
                "submission_period": "FY2023P04",
                "federal_account_symbol": "089-0213",
                "program_activity_reporting_key": "",
                "program_activity_code": "0033",
                "program_activity_name": "PROGRAM DIRECTION-IIJA",
                "obligations_incurred": "6516.62",
            },
            {
                "submission_period": "FY2023P04",
                "federal_account_symbol": "089-0213",
                "program_activity_reporting_key": "",
                "program_activity_code": "0033",
                "program_activity_name": "PROGRAM DIRECTION-IIJA",
                "obligations_incurred": "2346.23",
            },
            {
                "submission_period": "FY2023P04",
                "federal_account_symbol": "089-0213",
                "program_activity_reporting_key": "",
                "program_activity_code": "0033",
                "program_activity_name": "PROGRAM DIRECTION-IIJA",
                "obligations_incurred": "13000.00",
            },
            *[
                {
                    "submission_period": "FY2024P11",
                    "federal_account_symbol": "089-0213",
                    "program_activity_reporting_key": "",
                    "program_activity_code": "0023",
                    "program_activity_name": "CROSS CUTTING RESEARCH",
                    "obligations_incurred": amount,
                }
                for amount in (
                    "2925.54", "2492.13", "641551.44", "19033.00",
                    "5000.00", "7155882.68", "6493.45", "50369.18",
                    "98624.30", "19648.83",
                )
            ],
        ]
        snapshot = parse_file_b_snapshot(rows, "089-0213", aliases)
        self.assertEqual(
            {
                ("0018", "Program Direction", "5ZCQYAMAEXT"):
                    849_541_852,
                ("00U4", "Program Direction & Support", ""):
                    -212_080,
                ("00U5", "Program Direction", ""):
                    -2_000,
                ("00U6", "Other Defense Activities (Direct)", ""):
                    0,
                ("00U7", "Program Direction - IIJA", ""):
                    2_186_285,
                ("0005", "Cross-Cutting Research", "5ZCQYAMAEXR"):
                    800_202_055,
            },
            {
                (key[1], key[2], key[3]): amount
                for key, amount in snapshot.items()
            },
        )
        self.assertNotIn(("park", "5ZCQYAUD7RJ"), aliases)
        self.assertNotIn(("park", "5WKPVDWW473"), aliases)

    def test_fossil_fy2026_blank_name_park_is_authoritative(self):
        aliases = alias_map(self.accounts["doe/fossil-energy"])
        rows = [{
            "submission_period": "FY2026P02",
            "federal_account_symbol": "089-0213",
            "program_activity_reporting_key": "61UPW3ZTCVT",
            "program_activity_code": "",
            "program_activity_name": "",
            "obligations_incurred": amount,
        } for amount in (
            "1000000.00", "200000.00", "100000.00", "50000.00",
            "40000.00", "20000.00", "10000.00", "5000.00",
            "2000.00", "500.00", "255.93",
        )]
        snapshot = parse_file_b_snapshot(rows, "089-0213", aliases)
        self.assertEqual(142_775_593, sum(snapshot.values()))
        self.assertEqual(
            {(
                "0019",
                "Infrastructure Investment and Jobs Act/"
                "Bipartisan Infrastructure Law",
                "61UPW3ZTCVT",
            )},
            {(key[1], key[2], key[3]) for key in snapshot},
        )

    def test_eere_grid_operations_fy2023_p08_code_transition_is_exact(self):
        account = self.accounts["doe/eere"]
        aliases = alias_map(account)
        federal_management = [{
            "submission_period": "FY2023P07",
            "federal_account_symbol": "089-0321",
            "program_activity_reporting_key": "",
            "program_activity_code": "0204",
            "program_activity_name": "FEDERAL ENERGY MANAGEMENT PROGRAM",
            "obligations_incurred": "3180066.66",
        }]
        grid_operations = [{
            "submission_period": "FY2023P08",
            "federal_account_symbol": "089-0321",
            "program_activity_reporting_key": "",
            "program_activity_code": "0018",
            "program_activity_name": "ENERGY DELIVERY GRID OPERATIONS TECHNOLOGY",
            "obligations_incurred": amount,
        } for amount in (
            "547681.44", "9513.60", "-250.00", "190439.21",
            "3010.04", "84000.00", "2405.00",
        )]
        p07 = parse_file_b_snapshot(
            federal_management, "089-0321", aliases
        )
        p08 = parse_file_b_snapshot(
            [*federal_management, *grid_operations], "089-0321", aliases
        )
        flows = file_b_period_events({
            "FY2023P07": p07,
            "FY2023P08": p08,
        }, "089-0321")
        p08_nonzero = [
            row for row in flows
            if row["submissionPeriod"] == "FY2023P08"
            and row["amountCents"]
        ]
        self.assertEqual(1, len(p08_nonzero))
        self.assertEqual(83_679_929, p08_nonzero[0]["amountCents"])
        self.assertEqual("0204", p08_nonzero[0]["programActivityCode"])
        self.assertEqual(
            "Energy Delivery Grid Operations Technology",
            p08_nonzero[0]["programActivityName"],
        )
        self.assertEqual(
            "0204:energy-delivery-grid-operations-technology",
            p08_nonzero[0]["_programActivityKey"],
        )
        self.assertNotEqual(
            aliases[("code-name", "0204", "federal energy management program")][
                "_identityKey"
            ],
            p08_nonzero[0]["_programActivityKey"],
        )

    def test_nuclear_energy_iija_direction_is_distinct_from_base_direction(self):
        account = self.accounts["doe/nuclear-energy"]
        aliases = alias_map(account)
        rows = [
            {
                "federal_account_symbol": "089-0319",
                "program_activity_code": "0033",
                "program_activity_name": "PROGRAM DIRECTION-IIJA",
                "obligations_incurred": "23457.92",
            },
            {
                "federal_account_symbol": "089-0319",
                "program_activity_code": "0551",
                "program_activity_name": "PROGRAM DIRECTION",
                "obligations_incurred": "1.00",
            },
        ]
        snapshot = parse_file_b_snapshot(rows, "089-0319", aliases)
        self.assertEqual(
            {
                ("0033", "Program Direction - IIJA", ""): 2_345_792,
                ("0551", "Program Direction", "5ZCQYAU850J"): 100,
            },
            {
                (key[0], key[2], key[3]): amount
                for key, amount in snapshot.items()
            },
        )
        flows = file_b_period_events({"FY2024P10": snapshot}, "089-0319")
        events = combine_file_b_file_c(flows, [], "089-0319")
        self.assertEqual(2_345_892, sum(row["amountCents"] for row in events))
        self.assertEqual(2, len({row["id"] for row in events}))
        self.assertEqual(
            {"0033", "0551"},
            {row["_programActivityKey"] for row in events},
        )

    def test_oced_transient_administrative_identities_remain_distinct(self):
        account = self.accounts["doe/oced"]
        aliases = alias_map(account)
        rows = [
            {
                "federal_account_symbol": "089-2297",
                "program_activity_code": "0008",
                "program_activity_name": "ENERGY JUSTICE AND EQUITY",
                "obligations_incurred": "121801.44",
            },
            {
                "federal_account_symbol": "089-2297",
                "program_activity_code": "0009",
                "program_activity_name": "CHIEF FINANCIAL OFFICER",
                "obligations_incurred": "599152.00",
            },
        ]
        snapshot = parse_file_b_snapshot(rows, "089-2297", aliases)
        self.assertEqual(
            {
                ("0008", "Energy Justice and Equity", ""): 12_180_144,
                ("0009", "Chief Financial Officer", "63YPTC6AV6S"):
                    59_915_200,
            },
            {
                (key[0], key[2], key[3]): amount
                for key, amount in snapshot.items()
            },
        )
        flows = file_b_period_events({"FY2025P02": snapshot}, "089-2297")
        events = combine_file_b_file_c(flows, [], "089-2297")
        self.assertEqual(72_095_344, sum(row["amountCents"] for row in events))
        self.assertEqual(2, len({row["id"] for row in events}))
        self.assertEqual(
            {"0008", "0009"},
            {row["_programActivityKey"] for row in events},
        )

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
        expected_material_first_period = {
            "doe/oced": 4,
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
                    self.accounts[path]["availability"]["firstFiscalYearPeriod"],
                )
                self.assertEqual(
                    12, baseline["fiscalYears"][str(first_fy)]["asOfPeriod"]
                )
                self.assertEqual("partial", baseline["fiscalYears"]["2026"]["status"])
                self.assertEqual(9, baseline["fiscalYears"]["2026"]["asOfPeriod"])

                store = REPO / "data" / "obligations" / path / "events"
                if store.exists():
                    first_events = [
                        event for event in load_store(store)
                        if event["fiscalYear"] == first_fy
                    ]
                    self.assertTrue(first_events)
                    self.assertEqual(
                        "partial",
                        baseline["fiscalYears"][str(first_fy)]["status"],
                    )
                    self.assertEqual(
                        min(event["fiscalPeriod"] for event in first_events),
                        baseline["fiscalYears"][str(first_fy)]["firstPeriod"],
                    )
                    for fiscal_year in range(first_fy, 2027):
                        self.assertIn(
                            "obligationsCents",
                            baseline["fiscalYears"][str(fiscal_year)],
                            f"{path} FY{fiscal_year} retained an unfilled scaffold",
                        )
                else:
                    material_first_period = expected_material_first_period.get(
                        path, 6 if first_fy == 2017 else 2
                    )
                    self.assertEqual(
                        material_first_period,
                        baseline["fiscalYears"][str(first_fy)]["firstPeriod"],
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
