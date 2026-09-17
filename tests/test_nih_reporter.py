import gzip
import io
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from adapters.common import load_store, write_store
from adapters.nih_reporter import (METHODOLOGY_NOTE, MOVE_RETURN_ABS_MIN,
                                   MOVE_RETURN_REL_FRACTION,
                                   NihReporterPull, _award_kind,
                                   changes_ledger_path, excluded_ids,
                                   load_changes_ledger, load_exclusion_ledger,
                                   parse_trans_type, pull_unit,
                                   retained_missing_count,
                                   save_exclusion_ledger)


def row(appl_id, agency="NIGMS", award_notice_date="2025-01-15T00:00:00",
        fiscal_year_value=2025):
    return {
        "appl_id": appl_id,
        "fiscal_year": fiscal_year_value,
        "project_num": f"5R01GM{appl_id:06d}-01",
        "award_notice_date": award_notice_date,
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


def write_exclusion_ledger(repo_root, records):
    (repo_root / "reference").mkdir(parents=True, exist_ok=True)
    (repo_root / "reference" / "nih_reporter_exclusions.json").write_text(
        json.dumps({"schemaVersion": 1, "records": records}))


def exclusion_record(award_id, unit="nih/nigms/nigms",
                     classification="reporter-record-retraction-or-supersession",
                     reason="RePORTER retracted or superseded this application record from its search results.",
                     decided_on="2026-09-09", status="excluded"):
    return {"id": award_id, "unit": unit, "classification": classification,
            "reason": reason, "decidedOn": decided_on, "status": status}


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
        normalized, fallback, fy_anomaly = puller.normalize(row(123))
        self.assertFalse(fallback)
        self.assertFalse(fy_anomaly)
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

    def test_normalize_uses_source_current_date_outside_own_fiscal_year(self):
        # FY2025 runs 2024-10-01..2025-09-30; this notice date is in FY2026.
        puller = NihReporterPull(
            "NIGMS", {"min_total": 0, "max_total": 1, "max_monthly": 1},
            Path("unused"),
        )
        anomalous = row(123, award_notice_date="2025-11-04T00:00:00")
        normalized, fallback, fy_anomaly = puller.normalize(anomalous)
        self.assertFalse(fallback)
        self.assertTrue(fy_anomaly)
        # Source-current: the raw notice date is retained, not clamped to
        # the fiscal-year start or substituted with budget_start.
        self.assertEqual(normalized["date"], "2025-11-04")

    def test_normalize_falls_back_only_when_notice_date_is_absent(self):
        puller = NihReporterPull(
            "NIGMS", {"min_total": 0, "max_total": 1, "max_monthly": 1},
            Path("unused"),
        )
        missing_notice = row(123, award_notice_date=None)
        normalized, fallback, fy_anomaly = puller.normalize(missing_notice)
        self.assertTrue(fallback)
        self.assertFalse(fy_anomaly)
        self.assertEqual(normalized["date"], "2025-02-01")  # budget_start


class ExclusionLedgerTests(unittest.TestCase):
    def test_missing_ledger_file_is_treated_as_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(excluded_ids(Path(tmp)), set())
            self.assertEqual(load_exclusion_ledger(Path(tmp)),
                             {"schemaVersion": 1, "records": []})

    def test_duplicate_id_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_exclusion_ledger(root, [exclusion_record("nih:1"),
                                          exclusion_record("nih:1")])
            with self.assertRaisesRegex(RuntimeError, "duplicate"):
                load_exclusion_ledger(root)

    def test_invalid_status_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bad = exclusion_record("nih:1")
            bad["status"] = "deleted"
            write_exclusion_ledger(root, [bad])
            with self.assertRaisesRegex(RuntimeError, "status"):
                load_exclusion_ledger(root)

    def test_invalid_classification_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bad = exclusion_record("nih:1")
            bad["classification"] = "vibes"
            write_exclusion_ledger(root, [bad])
            with self.assertRaisesRegex(RuntimeError, "classification"):
                load_exclusion_ledger(root)

    def test_excluded_ids_returns_only_excluded_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_exclusion_ledger(root, [
                exclusion_record("nih:1", status="excluded"),
                exclusion_record("nih:2", status="returned"),
            ])
            self.assertEqual(excluded_ids(root), {"nih:1"})

    def test_save_sorts_records_deterministically(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            save_exclusion_ledger(root, {"schemaVersion": 1, "records": [
                exclusion_record("nih:2"), exclusion_record("nih:1"),
            ]})
            ledger = load_exclusion_ledger(root)
            self.assertEqual([r["id"] for r in ledger["records"]],
                             ["nih:1", "nih:2"])


class SoftDeleteAndReturnTests(unittest.TestCase):
    def test_excluded_id_is_never_popped_from_the_store(self):
        """Soft delete: the store retains an id even while its ledger
        status is 'excluded' and a full pull no longer returns it."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store_path = root / "data" / "nih" / "nigms" / "nigms" / "awards"
            write_exclusion_ledger(root, [exclusion_record("nih:2")])
            write_store(store_path, [
                NihReporterPull("NIGMS", {}, store_path).normalize(row(1))[0],
                NihReporterPull("NIGMS", {}, store_path).normalize(row(2))[0],
            ])
            puller = NihReporterPull(
                "NIGMS", {"min_total": 0, "max_total": 1000, "max_monthly": 1000},
                store_path,
            )
            with patch.object(puller, "fetch_year",
                              side_effect=lambda fy: {1: row(1)} if fy == 2025 else {}):
                awards, warnings, notes = puller.pull(
                    full=True, today=date(2026, 8, 17), repo_root=root)
            self.assertEqual({"nih:1", "nih:2"}, {a["id"] for a in awards})
            self.assertEqual([], warnings)
            # nih:2 is still "excluded" (not returned), so it is a
            # data-quality note, not a warning, and it is not popped.
            self.assertEqual(excluded_ids(root), {"nih:2"})

    def test_missing_uncovered_id_is_a_data_quality_note_not_a_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store_path = root / "data" / "nih" / "nigms" / "nigms" / "awards"
            write_store(store_path, [
                NihReporterPull("NIGMS", {}, store_path).normalize(row(2))[0],
            ])
            puller = NihReporterPull(
                "NIGMS", {"min_total": 0, "max_total": 1000, "max_monthly": 1000},
                store_path,
            )
            with patch.object(puller, "fetch_year", return_value={}):
                awards, warnings, notes = puller.pull(
                    full=True, today=date(2026, 8, 17), repo_root=root)
            self.assertEqual(["nih:2"], [a["id"] for a in awards])
            self.assertEqual([], warnings)
            self.assertEqual(1, len(notes))
            self.assertIn("1 stored award record(s) were not returned", notes[0])
            self.assertIn("retained", notes[0])

    def test_return_flips_ledger_status_and_prints_notice(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store_path = root / "data" / "nih" / "nigms" / "nigms" / "awards"
            write_exclusion_ledger(root, [exclusion_record("nih:2")])
            write_store(store_path, [
                NihReporterPull("NIGMS", {}, store_path).normalize(row(1))[0],
                NihReporterPull("NIGMS", {}, store_path).normalize(row(2))[0],
            ])
            puller = NihReporterPull(
                "NIGMS", {"min_total": 0, "max_total": 1000, "max_monthly": 1000},
                store_path,
            )
            with patch.object(
                puller, "fetch_year",
                side_effect=lambda fy: {1: row(1), 2: row(2)} if fy == 2025 else {},
            ):
                buf = io.StringIO()
                with patch("sys.stdout", buf):
                    awards, warnings, notes = puller.pull(
                        full=True, today=date(2026, 8, 17), repo_root=root)
            self.assertEqual([], warnings)
            self.assertIn("NOTICE", buf.getvalue())
            self.assertIn("returned to the live source", buf.getvalue())
            ledger = load_exclusion_ledger(root)
            by_id = {r["id"]: r for r in ledger["records"]}
            self.assertEqual("returned", by_id["nih:2"]["status"])
            self.assertEqual(excluded_ids(root), set())

    def test_returning_a_second_time_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store_path = root / "data" / "nih" / "nigms" / "nigms" / "awards"
            write_exclusion_ledger(root, [
                exclusion_record("nih:2", status="returned"),
            ])
            write_store(store_path, [
                NihReporterPull("NIGMS", {}, store_path).normalize(row(2))[0],
            ])
            puller = NihReporterPull(
                "NIGMS", {"min_total": 0, "max_total": 1000, "max_monthly": 1000},
                store_path,
            )
            with patch.object(puller, "fetch_year",
                              side_effect=lambda fy: {2: row(2)} if fy == 2025 else {}):
                awards, warnings, notes = puller.pull(
                    full=True, today=date(2026, 8, 17), repo_root=root)
        self.assertEqual([], warnings)


class MoveLedgerTests(unittest.TestCase):
    def test_field_changes_are_appended_and_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store_path = root / "data" / "nih" / "nigms" / "nigms" / "awards"
            write_store(store_path, [
                NihReporterPull("NIGMS", {}, store_path).normalize(row(1))[0],
            ])
            puller = NihReporterPull(
                "NIGMS", {"min_total": 0, "max_total": 1000, "max_monthly": 1000},
                store_path,
            )
            re_dated = row(1, award_notice_date="2025-03-01T00:00:00")
            with patch.object(puller, "fetch_year",
                              side_effect=lambda fy: {1: re_dated} if fy == 2025 else {}):
                awards, warnings, notes = puller.pull(
                    full=True, today=date(2026, 8, 17), repo_root=root)
            self.assertEqual([], warnings)
            rows = load_changes_ledger(store_path)
            self.assertEqual(1, len(rows))
            self.assertEqual(rows[0]["id"], "nih:1")
            self.assertEqual(rows[0]["field"], "date")
            self.assertEqual(rows[0]["old"], "2025-01-15")
            self.assertEqual(rows[0]["new"], "2025-03-01")
            self.assertEqual(rows[0]["pullDate"], "2026-08-17")

            path = changes_ledger_path(store_path)
            bytes_first = path.read_bytes()
            # Re-appending the same content produces byte-identical output
            # (fixed gzip mtime + deterministic sort).
            from adapters.nih_reporter import append_changes_ledger
            append_changes_ledger(store_path, [])
            self.assertEqual(bytes_first, path.read_bytes())

    def test_changes_accumulate_append_only_across_pulls(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store_path = root / "data" / "nih" / "nigms" / "nigms" / "awards"
            write_store(store_path, [
                NihReporterPull("NIGMS", {}, store_path).normalize(row(1))[0],
            ])
            puller = NihReporterPull(
                "NIGMS", {"min_total": 0, "max_total": 1000, "max_monthly": 1000},
                store_path,
            )
            first_change = row(1, award_notice_date="2025-03-01T00:00:00")
            with patch.object(puller, "fetch_year",
                              side_effect=lambda fy: {1: first_change} if fy == 2025 else {}):
                first_awards, _, _ = puller.pull(
                    full=True, today=date(2026, 8, 17), repo_root=root)
            # Simulate scripts/pull_unit.py writing the store back between
            # pulls, so the second pull diffs against the updated date.
            write_store(store_path, first_awards)
            second_change = row(1, award_notice_date="2025-04-01T00:00:00")
            with patch.object(puller, "fetch_year",
                              side_effect=lambda fy: {1: second_change} if fy == 2025 else {}):
                puller.pull(full=True, today=date(2026, 8, 24), repo_root=root)
            rows = load_changes_ledger(store_path)
            self.assertEqual(2, len(rows))
            self.assertEqual(["2026-08-17", "2026-08-24"], [r["pullDate"] for r in rows])
            # Original row untouched (append-only).
            self.assertEqual(rows[0]["old"], "2025-01-15")
            self.assertEqual(rows[0]["new"], "2025-03-01")
            self.assertEqual(rows[1]["old"], "2025-03-01")
            self.assertEqual(rows[1]["new"], "2025-04-01")


class ChurnThresholdTests(unittest.TestCase):
    def _store_of_size(self, store_path, n):
        write_store(store_path, [
            NihReporterPull("NIGMS", {}, store_path).normalize(row(i))[0]
            for i in range(1, n + 1)
        ])

    def test_threshold_passes_at_exactly_the_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store_path = root / "data" / "nih" / "nigms" / "nigms" / "awards"
            n = 1000  # max(20, 0.1% of 1000) == 20
            self._store_of_size(store_path, n)
            limit = int(max(MOVE_RETURN_ABS_MIN, MOVE_RETURN_REL_FRACTION * n))
            self.assertEqual(limit, 20)
            changed_rows = {
                i: row(i, award_notice_date="2025-03-01T00:00:00")
                for i in range(1, limit + 1)
            }
            puller = NihReporterPull(
                "NIGMS", {"min_total": 0, "max_total": 10000, "max_monthly": 10000},
                store_path,
            )
            all_rows = {i: row(i) for i in range(1, n + 1)}
            all_rows.update(changed_rows)
            with patch.object(puller, "fetch_year",
                              side_effect=lambda fy: all_rows if fy == 2025 else {}):
                awards, warnings, notes = puller.pull(
                    full=True, today=date(2026, 8, 17), repo_root=root)
            self.assertEqual([], warnings)

    def test_threshold_fails_closed_one_above_the_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store_path = root / "data" / "nih" / "nigms" / "nigms" / "awards"
            n = 1000
            self._store_of_size(store_path, n)
            limit = int(max(MOVE_RETURN_ABS_MIN, MOVE_RETURN_REL_FRACTION * n))
            over_limit = limit + 1
            changed_rows = {
                i: row(i, award_notice_date="2025-03-01T00:00:00")
                for i in range(1, over_limit + 1)
            }
            puller = NihReporterPull(
                "NIGMS", {"min_total": 0, "max_total": 10000, "max_monthly": 10000},
                store_path,
            )
            all_rows = {i: row(i) for i in range(1, n + 1)}
            all_rows.update(changed_rows)
            with patch.object(puller, "fetch_year",
                              side_effect=lambda fy: all_rows if fy == 2025 else {}):
                with self.assertRaisesRegex(SystemExit, "pagination"):
                    puller.pull(full=True, today=date(2026, 8, 17), repo_root=root)


class MethodologyAndDataQualityTests(unittest.TestCase):
    def test_pull_unit_emits_verbatim_methodology_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store_path = root / "data" / "nih" / "nigms" / "nigms" / "awards"
            unit_cfg = {"params": {"reporter_agency": "NIGMS"},
                       "checks": {"min_total": 0, "max_total": 10,
                                  "max_monthly": 10}}
            puller_row = row(1)

            def fake_fetch_year(self, fy, attempts=3):
                return {1: puller_row} if fy == 2025 else {}

            with patch.object(NihReporterPull, "fetch_year", fake_fetch_year):
                awards, warnings, source, metadata = pull_unit(
                    unit_cfg, store_path, full=True, today=date(2026, 8, 17),
                    repo_root=root)
        self.assertEqual(
            metadata["methodologyNote"],
            "counts as of the pull date; NIH revises award notice dates.")
        self.assertEqual(metadata["methodologyNote"], METHODOLOGY_NOTE)
        self.assertIn("dataQualityNotes", metadata)

    def test_retained_missing_count_parses_notes(self):
        notes = [
            "2 stored award record(s) were not returned by the 2026-09-18 "
            "full pull and are retained; NIH revises and withdraws notices.",
            "1 award record(s) carry a NIH-reported award notice date "
            "outside their own declared fiscal year; retained and dated by "
            "the source's current notice date.",
        ]
        self.assertEqual(2, retained_missing_count(notes))
        self.assertEqual(0, retained_missing_count(None))
        self.assertEqual(0, retained_missing_count([]))


class ConfigSanityTests(unittest.TestCase):
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
