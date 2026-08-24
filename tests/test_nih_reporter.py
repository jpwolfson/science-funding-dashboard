import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from adapters.common import load_store, write_store
from adapters.nih_reporter import (NihReporterPull, _award_kind,
                                   parse_trans_type)


def row(appl_id, agency="NIGMS"):
    return {
        "appl_id": appl_id,
        "fiscal_year": 2025,
        "project_num": f"5R01GM{appl_id:06d}-01",
        "award_notice_date": "2025-01-15T00:00:00",
        "budget_start": "2025-02-01T00:00:00",
        "project_start_date": "2025-02-01T00:00:00",
        "award_amount": 123456,
        "award_type": "5",
        "activity_code": "R01",
        "project_title": "Example project",
        "organization": {"org_name": "Example University"},
        "agency_ic_admin": {"abbreviation": agency},
        "funding_mechanism": "Non-SBIR/STTR",
    }


class NihReporterTests(unittest.TestCase):
    def test_application_and_activity_codes_map_to_dashboard_bins(self):
        self.assertEqual(_award_kind("F32", "5"), "Fellowship")
        self.assertEqual(_award_kind("R01", "5"), "Continuing award")
        self.assertEqual(_award_kind("R01", "1"), "Standard/new award")
        self.assertEqual(_award_kind("ZIA", ""), "Other award")

    def test_two_ordered_pagination_passes_must_match(self):
        rows = [row(i) for i in range(1, 502)]

        def fake_post(payload, retries=5):
            del retries
            ordered = rows if payload["sort_order"] == "asc" else list(reversed(rows))
            offset = payload["offset"]
            limit = payload["limit"]
            return {"meta": {"total": len(rows)},
                    "results": ordered[offset:offset + limit]}

        puller = NihReporterPull(
            "NIGMS", {"min_total": 0, "max_total": 1000, "max_monthly": 1000},
            Path("unused"),
        )
        with patch("adapters.nih_reporter.api_post", side_effect=fake_post):
            fetched = puller.fetch_year(2025)
        self.assertEqual(set(fetched), set(range(1, 502)))

    def test_duplicate_displacement_is_rejected(self):
        rows = [row(i) for i in range(1, 502)]

        def fake_post(payload, retries=5):
            del retries
            offset = payload["offset"]
            if offset == 0:
                page = rows[:500]
            else:
                # Reproduce the NSF defect class: a record from page one is
                # repeated and silently displaces the final unique record.
                page = [rows[499]]
            return {"meta": {"total": len(rows)}, "results": page}

        puller = NihReporterPull(
            "NIGMS", {"min_total": 0, "max_total": 1000,
                       "max_monthly": 1000}, Path("unused"),
        )
        with patch("adapters.nih_reporter.api_post", side_effect=fake_post):
            with self.assertRaisesRegex(RuntimeError, "unique applications"):
                puller.fetch_pass(2025, "asc")

    def test_total_changing_between_pages_is_rejected(self):
        rows = [row(i) for i in range(1, 502)]

        def fake_post(payload, retries=5):
            del retries
            offset = payload["offset"]
            total = len(rows) if offset == 0 else len(rows) + 1
            return {"meta": {"total": total},
                    "results": rows[offset:offset + payload["limit"]]}

        puller = NihReporterPull(
            "NIGMS", {"min_total": 0, "max_total": 1000,
                       "max_monthly": 1000}, Path("unused"),
        )
        with patch("adapters.nih_reporter.api_post", side_effect=fake_post):
            with self.assertRaisesRegex(RuntimeError, "total changed"):
                puller.fetch_pass(2025, "asc")

    def test_opposite_order_id_sets_must_match(self):
        asc = [row(1), row(2)]
        desc = [row(3), row(2)]

        def fake_post(payload, retries=5):
            del retries
            rows = asc if payload["sort_order"] == "asc" else desc
            return {"meta": {"total": 2}, "results": rows}

        puller = NihReporterPull(
            "NIGMS", {"min_total": 0, "max_total": 1000,
                       "max_monthly": 1000}, Path("unused"),
        )
        with patch("adapters.nih_reporter.api_post", side_effect=fake_post), \
             patch("adapters.nih_reporter.time.sleep"):
            with self.assertRaisesRegex(RuntimeError, "ordered passes disagree"):
                puller.fetch_year(2025)

    def test_row_level_filter_mismatches_are_rejected(self):
        cases = [
            ({"fiscal_year": 2024}, "fiscal-year filter mismatch"),
            ({"agency_ic_admin": {"abbreviation": "NCI"}},
             "agency filter mismatch"),
            ({"subproject_id": 123}, "subproject filter mismatch"),
            ({"funding_mechanism": "Intramural"},
             "funding-mechanism filter mismatch"),
            ({"funding_mechanism": None}, "missing funding_mechanism"),
        ]
        puller = NihReporterPull(
            "NIGMS", {"min_total": 0, "max_total": 1000,
                       "max_monthly": 1000}, Path("unused"),
        )
        for changes, message in cases:
            bad = row(1)
            bad.update(changes)
            with self.subTest(changes=changes):
                with patch("adapters.nih_reporter.api_post", return_value={
                    "meta": {"total": 1}, "results": [bad],
                }):
                    with self.assertRaisesRegex(RuntimeError, message):
                        puller.fetch_pass(2025, "asc")

    def test_normalize_namespaces_ids_and_uses_award_notice_date(self):
        puller = NihReporterPull(
            "NIGMS", {"min_total": 0, "max_total": 1, "max_monthly": 1},
            Path("unused"),
        )
        normalized, fallback = puller.normalize(row(123))
        self.assertFalse(fallback)
        self.assertEqual(normalized["id"], "nih:123")
        self.assertEqual(normalized["date"], "2025-01-15")
        self.assertEqual(normalized["amount"], 123456)
        self.assertEqual(normalized["type"], "cont")
        self.assertEqual(parse_trans_type(normalized["transType"]), {
            "kind": "Continuing award",
            "award_type": "5",
            "activity": "R01",
            "mechanism": "Non-SBIR/STTR",
        })

    def test_full_pull_removes_only_reviewed_reporter_retractions(self):
        with tempfile.TemporaryDirectory() as tmp:
            store_path = Path(tmp) / "awards"
            puller = NihReporterPull(
                "NIGMS",
                {"min_total": 0, "max_total": 1000, "max_monthly": 1000},
                store_path,
                retracted_ids={"nih:2"},
                retracted_months={"nih:2": "2025-01"},
            )
            write_store(
                store_path,
                [puller.normalize(row(1))[0], puller.normalize(row(2))[0]],
            )
            with patch.object(
                puller,
                "fetch_year",
                side_effect=lambda fy: {1: row(1)} if fy == 2025 else {},
            ):
                awards, warnings = puller.pull(
                    full=True, today=date(2026, 8, 17)
                )
        self.assertEqual(["nih:1"], [award["id"] for award in awards])
        self.assertEqual([], warnings)
        self.assertEqual({"2025-01": 1}, puller.allowed_monthly_shrink)

    def test_unreviewed_missing_award_is_still_retained_and_warned(self):
        with tempfile.TemporaryDirectory() as tmp:
            store_path = Path(tmp) / "awards"
            puller = NihReporterPull(
                "NIGMS",
                {"min_total": 0, "max_total": 1000, "max_monthly": 1000},
                store_path,
            )
            write_store(store_path, [puller.normalize(row(2))[0]])
            with patch.object(puller, "fetch_year", return_value={}):
                awards, warnings = puller.pull(
                    full=True, today=date(2026, 8, 17)
                )
        self.assertEqual(["nih:2"], [award["id"] for award in awards])
        self.assertEqual(1, len(warnings))
        self.assertIn("retained from the store", warnings[0])

    def test_retraction_ledger_has_unique_namespaced_ids(self):
        ledger = json.loads(
            (Path(__file__).parents[1] / "reference" /
             "nih_reporter_retractions.json").read_text()
        )
        records = ledger["records"]
        self.assertEqual(21, len(records))
        self.assertEqual(21, len({record["id"] for record in records}))
        self.assertTrue(all(record["id"].startswith("nih:") for record in records))
        self.assertTrue(all(record["reporterAgency"] for record in records))
        self.assertTrue(all(record["month"] == record["awardDate"][:7]
                            for record in records))

    def test_approved_20260824_retractions_match_exact_evidence(self):
        root = Path(__file__).parents[1]
        ledger = json.loads(
            (root / "reference" / "nih_reporter_retractions.json").read_text()
        )
        evidence = json.loads(
            (root / "reference" /
             "nih_reporter_retraction_evidence_20260824.json").read_text()
        )
        expected_ids = {
            "nih:11161340", "nih:11327923", "nih:11462449",
            "nih:11380142", "nih:11461896", "nih:11286738",
            "nih:11290350", "nih:11555862", "nih:11437634",
        }
        self.assertTrue(evidence["control"]["returned"])
        self.assertEqual([], evidence["candidateIdsReturned"])
        self.assertEqual(expected_ids,
                         {record["id"] for record in evidence["records"]})
        self.assertEqual(1288767,
                         sum(record["amount"] for record in evidence["records"]))
        ledger_by_id = {record["id"]: record for record in ledger["records"]}
        self.assertEqual(evidence["records"],
                         [ledger_by_id[record["id"]]
                          for record in evidence["records"]])
        stores = {}
        for record in evidence["records"]:
            unit = record["unit"]
            if unit not in stores:
                stores[unit] = load_store(root / "data" / unit)
            stored = stores[unit][record["id"]]
            self.assertEqual(record["awardDate"], stored["date"])
            self.assertEqual(record["month"], stored["month"])
            self.assertEqual(record["amount"], stored["amount"])
            self.assertEqual(record["title"], stored["title"])

    def test_config_has_all_current_reporter_nih_admin_components(self):
        cfg = json.loads((Path(__file__).parents[1] / "config" / "orgs.json").read_text())
        nih = next(agency for agency in cfg["agencies"] if agency["slug"] == "nih")
        values = {division["params"]["reporter_agency"]
                  for directorate in nih["directorates"]
                  for division in directorate["divisions"]}
        self.assertEqual(values, {
            "CLC", "CSR", "CIT", "FIC", "NCATS", "NCCIH", "NCI", "NEI",
            "NHGRI", "NHLBI", "NIA", "NIAAA", "NIAID", "NIAMS", "NIBIB",
            "NICHD", "NIDA", "NIDCD", "NIDCR", "NIDDK", "NIEHS", "NIGMS",
            "NIMH", "NIMHD", "NINDS", "NINR", "NLM", "OD",
        })

    def test_every_nih_component_has_a_volume_range_containing_baseline(self):
        baseline = {
            "CLC": 0, "CSR": 0, "CIT": 0, "FIC": 4427,
            "NCATS": 4447, "NCCIH": 3547, "NCI": 91300, "NEI": 19371,
            "NHGRI": 6859, "NHLBI": 67357, "NIA": 46246,
            "NIAAA": 12939, "NIAID": 73334, "NIAMS": 16988,
            "NIBIB": 10741, "NICHD": 32351, "NIDA": 26835,
            "NIDCD": 13408, "NIDCR": 10764, "NIDDK": 49914,
            "NIEHS": 12632, "NIGMS": 80147, "NIMH": 38390,
            "NIMHD": 6235, "NINDS": 52058, "NINR": 4055,
            "NLM": 2275, "OD": 7823,
        }
        cfg = json.loads(
            (Path(__file__).parents[1] / "config" / "orgs.json").read_text())
        nih = next(agency for agency in cfg["agencies"] if agency["slug"] == "nih")
        divisions = [division for directorate in nih["directorates"]
                     for division in directorate["divisions"]]
        for division in divisions:
            code = division["params"]["reporter_agency"]
            checks = division.get("checks") or {}
            with self.subTest(code=code):
                self.assertIn("min_total", checks)
                self.assertIn("max_total", checks)
                self.assertLessEqual(checks["min_total"], baseline[code])
                self.assertGreaterEqual(checks["max_total"], baseline[code])


if __name__ == "__main__":
    unittest.main()
