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
        self.assertEqual(2, ledger["schemaVersion"])
        self.assertEqual(31, len(records))
        self.assertEqual(31, len({record["id"] for record in records}))
        self.assertTrue(all(record["id"].startswith("nih:") for record in records))
        self.assertTrue(all(record["reporterAgency"] for record in records))
        self.assertTrue(all(record["month"] == record["awardDate"][:7]
                            for record in records))
        by_class = {}
        for record in records:
            classification = record["classification"]
            by_class.setdefault(classification, []).append(record)
        self.assertEqual({
            "reporter-record-retraction-or-supersession": 29,
            "confirmed-bilateral-termination": 2,
        }, {key: len(value) for key, value in by_class.items()})
        self.assertEqual(7904720,
                         sum(record["amount"] for record in records))
        self.assertEqual(120886, sum(
            record["amount"]
            for record in by_class["confirmed-bilateral-termination"]
        ))
        self.assertEqual({
            ("nih:11241477", "F30HL178229", "2026-08-27"),
            ("nih:11241491", "F32DK142455", "2026-08-29"),
        }, {
            (record["id"], record["awardNumber"], record["terminationDate"])
            for record in by_class["confirmed-bilateral-termination"]
            if record["terminationType"] == "Bilateral Termination"
        })

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
        returned_ids = {
            "nih:11462449", "nih:11461896", "nih:11555862",
            "nih:11437634",
        }
        active_ids = expected_ids - returned_ids
        self.assertEqual(active_ids, expected_ids & set(ledger_by_id))
        self.assertFalse(returned_ids & set(ledger_by_id))
        stores = {}
        for record in evidence["records"]:
            unit = record["unit"]
            if unit not in stores:
                stores[unit] = load_store(root / "data" / unit)
            if record["id"] in active_ids:
                self.assertNotIn(record["id"], stores[unit])
            else:
                self.assertIn(record["id"], stores[unit])

    def test_approved_20260908_source_exclusions_match_exact_evidence(self):
        root = Path(__file__).parents[1]
        ledger = json.loads(
            (root / "reference" / "nih_reporter_retractions.json").read_text()
        )
        evidence = json.loads(
            (root / "reference" /
             "nih_reporter_source_evidence_20260908.json").read_text()
        )
        missing_ids = {
            "nih:11043767", "nih:11088961", "nih:11176793",
            "nih:11234633", "nih:11241477", "nih:11241491",
            "nih:11266582", "nih:11313204", "nih:11380040",
            "nih:11384307", "nih:11398315", "nih:11415246",
            "nih:11416109", "nih:11418121", "nih:11458848",
        }
        returned_ids = {
            "nih:11294928", "nih:11437634", "nih:11461896",
            "nih:11462449", "nih:11555862",
        }
        terminated_ids = {"nih:11241477", "nih:11241491"}
        reporter_record_ids = missing_ids - terminated_ids
        self.assertTrue(evidence["reporter"]["control"]["returned"])
        self.assertEqual(
            returned_ids | {"nih:11126249"},
            set(evidence["reporter"]["exactQuery"]["returnedIds"]),
        )
        self.assertEqual(
            reporter_record_ids,
            set(evidence["classification"]
                ["reporterRecordRetractionsOrSupersessions"]),
        )
        self.assertEqual(
            terminated_ids,
            set(evidence["classification"]
                ["confirmedBilateralTerminations"]),
        )
        self.assertEqual({
            "missingRecordCount": 15,
            "missingRecordAmount": 5531355,
            "reporterRecordRetractionOrSupersessionCount": 13,
            "reporterRecordRetractionOrSupersessionAmount": 5410469,
            "confirmedBilateralTerminationCount": 2,
            "confirmedBilateralTerminationHistoricalRowAmount": 120886,
            "returnedPriorExclusionCount": 5,
            "returnedPriorExclusionCurrentReporterAmount": 517955,
            "returnedPriorExclusionRecordedLedgerAmount": 751955,
        }, evidence["totals"])

        evidence_by_id = {
            record["id"]: record
            for record in evidence["missingStoredRecords"]
        }
        ledger_by_id = {record["id"]: record for record in ledger["records"]}
        self.assertEqual(missing_ids, set(evidence_by_id))
        self.assertEqual(missing_ids, missing_ids & set(ledger_by_id))
        self.assertFalse(returned_ids & set(ledger_by_id))
        for record_id, evidence_record in evidence_by_id.items():
            ledger_record = ledger_by_id[record_id]
            stored = evidence_record["stored"]
            self.assertEqual(stored["date"], ledger_record["awardDate"])
            self.assertEqual(int(stored["estimatedTotalAmt"]),
                             ledger_record["amount"])
            self.assertEqual(stored["title"], ledger_record["title"])
            expected_class = (
                "confirmed-bilateral-termination"
                if record_id in terminated_ids
                else "reporter-record-retraction-or-supersession"
            )
            self.assertEqual(expected_class, ledger_record["classification"])
            store = load_store(root / "data" / evidence_record["unit"])
            if record_id in store:
                actual = store[record_id]
                self.assertEqual(stored["date"], actual["date"])
                self.assertEqual(int(stored["estimatedTotalAmt"]),
                                 actual["amount"])
                self.assertEqual(stored["transType"], actual["transType"])
                self.assertEqual(stored["title"], actual["title"])
                self.assertEqual(stored["awardeeName"], actual["awardee"])

        returned_by_id = {
            record["id"]: record
            for record in evidence["returnedPriorExclusions"]
        }
        self.assertEqual(returned_ids, set(returned_by_id))
        for record_id, returned in returned_by_id.items():
            store = load_store(
                root / "data" / returned["priorLedgerRecord"]["unit"]
            )
            self.assertIn(record_id, store)

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
