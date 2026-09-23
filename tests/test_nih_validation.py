import gzip
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from adapters.award_refresh import unit_stale_reason, write_refresh_status
from adapters.common import write_dashboard, write_store
from adapters.nih_reporter import (CHANGES_HEADER, METHODOLOGY_NOTE,
                                   append_changes_ledger,
                                   changes_ledger_path, encode_trans_type)
from scripts.validate_nih import (_check_changes_ledger, in_data_book_scope,
                                  live_mechanism_partition,
                                  reconcile_live_total, read_store,
                                  validate, within_relative)


def award(award_id="nih:1", day="2024-09-30", activity="R01",
          mechanism="Non-SBIR/STTR", amount=123):
    return {
        "id": award_id,
        "date": day,
        "month": day[:7],
        "amount": amount,
        "type": "std",
        "transType": encode_trans_type(
            "Standard/new award", "1", activity, mechanism),
        "title": "Example",
        "awardee": "Example University",
    }


class NihValidationTests(unittest.TestCase):
    def test_mechanism_partition_reconciles_whitelist_plus_intramural(self):
        totals = iter([8858, 8087, 771])

        def fake_post(payload):
            self.assertEqual(payload["criteria"]["agencies"], ["NCI"])
            return {"meta": {"total": next(totals)}}

        with patch("scripts.validate_nih.api_post", side_effect=fake_post):
            result = live_mechanism_partition("NCI", 2025)
        self.assertEqual(result, {
            "unfiltered": 8858, "extramural": 8087, "intramural": 771,
        })

    def test_clean_sharded_store_reconciles_to_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            leaf = Path(tmp) / "nih" / "nci" / "nci"
            write_store(leaf / "awards", [award()])
            rows, errors = read_store(leaf)
            self.assertEqual(len(rows), 1)
            self.assertEqual(errors, [])

    def test_manifest_count_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            leaf = Path(tmp) / "nih" / "nci" / "nci"
            write_store(leaf / "awards", [award()])
            manifest_path = leaf / "awards" / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["recordCount"] = 2
            manifest_path.write_text(json.dumps(manifest))
            _, errors = read_store(leaf)
            self.assertTrue(any("recordCount=2 but read 1" in e for e in errors))

    def test_relative_benchmark_tolerance_is_inclusive(self):
        self.assertTrue(within_relative(98, 100, 0.02))
        self.assertTrue(within_relative(102, 100, 0.02))
        self.assertFalse(within_relative(97, 100, 0.02))

    def test_data_book_scope_is_like_for_like_without_narrowing_store(self):
        cases = [
            (award(), True),
            (award(activity="OT2", mechanism="Other"), True),
            (award(mechanism="R and D Contracts"), False),
            (award(mechanism="Interagency Agreements"), False),
            (award(activity="L30"), False),
            (award(amount=0), False),
        ]
        for row, expected in cases:
            stored_row = {
                **row,
                "estimatedTotalAmt": row.pop("amount"),
            }
            with self.subTest(transType=stored_row["transType"]):
                self.assertEqual(in_data_book_scope(stored_row), expected)

    def test_legacy_rows_require_full_repull_before_benchmarking(self):
        row = award()
        row["estimatedTotalAmt"] = row.pop("amount")
        row["transType"] = "Standard/new award (1, R01)"
        with self.assertRaisesRegex(ValueError, "full re-pull required"):
            in_data_book_scope(row)

    def test_live_gap_within_tolerance_math(self):
        # store=10000, excluded=3, retainedMissing=2 -> expected=9995.
        # tolerance = max(3, 0.01% of 10000) = max(3, 1) = 3.
        result = reconcile_live_total(10000, 3, 2, 9995)
        self.assertEqual(result["expected"], 9995)
        self.assertEqual(result["tolerance"], 3)
        self.assertEqual(result["gap"], 0)
        self.assertTrue(result["withinTolerance"])

        result = reconcile_live_total(10000, 3, 2, 9998)
        self.assertEqual(result["gap"], 3)
        self.assertTrue(result["withinTolerance"])  # exactly at tolerance

        result = reconcile_live_total(10000, 3, 2, 9999)
        self.assertEqual(result["gap"], 4)
        self.assertFalse(result["withinTolerance"])

    def test_live_gap_tolerance_uses_absolute_floor_for_small_stores(self):
        # 0.01% of 100 is 0.01, so the floor of 3 applies.
        result = reconcile_live_total(100, 0, 0, 97)
        self.assertEqual(result["tolerance"], 3)
        self.assertTrue(result["withinTolerance"])

    def test_changes_ledger_check_accepts_absence(self):
        with tempfile.TemporaryDirectory() as tmp:
            leaf = Path(tmp) / "nih" / "nci" / "nci"
            self.assertEqual([], _check_changes_ledger(leaf))

    def test_changes_ledger_check_validates_columns_and_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            leaf = Path(tmp) / "nih" / "nci" / "nci"
            store_path = leaf / "awards"
            append_changes_ledger(store_path, [
                {"pullDate": "2026-09-14", "id": "nih:1", "field": "date",
                 "old": "2025-01-01", "new": "2025-02-01"},
            ])
            self.assertEqual([], _check_changes_ledger(leaf))

    def test_changes_ledger_check_rejects_unsorted_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            leaf = Path(tmp) / "nih" / "nci" / "nci"
            path = changes_ledger_path(leaf / "awards")
            path.parent.mkdir(parents=True, exist_ok=True)
            with gzip.open(path, "wt", newline="") as fh:
                import csv
                writer = csv.DictWriter(fh, fieldnames=CHANGES_HEADER)
                writer.writeheader()
                writer.writerow({"pullDate": "2026-09-14", "id": "nih:2",
                                 "field": "date", "old": "a", "new": "b"})
                writer.writerow({"pullDate": "2026-09-14", "id": "nih:1",
                                 "field": "date", "old": "a", "new": "b"})
            errors = _check_changes_ledger(leaf)
            self.assertEqual(1, len(errors))
            self.assertIn("not sorted", errors[0])

    def test_changes_ledger_check_rejects_wrong_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            leaf = Path(tmp) / "nih" / "nci" / "nci"
            path = changes_ledger_path(leaf / "awards")
            path.parent.mkdir(parents=True, exist_ok=True)
            with gzip.open(path, "wt", newline="") as fh:
                fh.write("pullDate,id,field,old\n2026-09-14,nih:1,date,a\n")
            errors = _check_changes_ledger(leaf)
            self.assertEqual(1, len(errors))
            self.assertIn("unexpected columns", errors[0])


class NihValidationLiveStalenessTests(unittest.TestCase):
    """Phase 3.2d remediation W17: a unit disclosed as stale in
    data/refresh_status.json gets a live-gap WARNING instead of an ERROR;
    the identical non-stale unit still errors. All non-live checks stay
    unaffected either way."""

    def _build_repo(self, root):
        """Two NIH units ("aaa", "bbb"), each with 100 awards on the same
        day so every offline check passes cleanly and only the live-gap
        behavior differs between them."""
        (root / "config").mkdir(parents=True)
        (root / "reference").mkdir(parents=True)
        cfg = {
            "defaults": {"min_total": 0, "max_total": 100000, "max_monthly": 100000},
            "agencies": [{
                "slug": "nih",
                "directorates": [
                    {"slug": "aaa", "divisions": [
                        {"slug": "aaa", "params": {"reporter_agency": "AAA"}},
                    ]},
                    {"slug": "bbb", "divisions": [
                        {"slug": "bbb", "params": {"reporter_agency": "BBB"}},
                    ]},
                ],
            }],
        }
        (root / "config" / "orgs.json").write_text(json.dumps(cfg))
        (root / "reference" / "nih_databook_baseline.json").write_text(json.dumps({
            "comparison": {"countRelativeTolerance": 0.02, "dollarRelativeTolerance": 0.02},
            "fiscalYears": {},
        }))

        all_awards = []
        for unit_slug in ("aaa", "bbb"):
            leaf = root / "data" / "nih" / unit_slug / unit_slug
            awards = [award(f"nih:{unit_slug}:{i}") for i in range(100)]
            write_store(leaf / "awards", awards)
            write_dashboard(
                leaf, {"name": unit_slug, "abbrev": unit_slug.upper(),
                       "path": f"nih/{unit_slug}/{unit_slug}", "level": "leaf"},
                "test source", awards, [], date(2026, 9, 21),
                metadata={"methodologyNote": METHODOLOGY_NOTE, "dataComplete": True})
            all_awards.extend(awards)

        write_dashboard(
            root / "data" / "nih", {"name": "NIH", "path": "nih", "level": "agency"},
            "test source", all_awards, [], date(2026, 9, 21),
            metadata={"methodologyNote": METHODOLOGY_NOTE, "dataComplete": True})
        write_dashboard(
            root / "data", {"name": "Federal science funding", "path": "", "level": "root"},
            "test source", all_awards, [], date(2026, 9, 21),
            metadata={"methodologyNote": METHODOLOGY_NOTE})

    def test_stale_unit_out_of_tolerance_warns_identical_fresh_unit_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._build_repo(root)
            write_refresh_status(root, {
                "nih/aaa/aaa": {
                    "status": "stale", "staleSince": "2026-09-01",
                    "lastAcceptedAt": None,
                    "reason": unit_stale_reason("2026-09-01"),
                },
            }, "2026-09-21T09:13:00Z")

            # Both units store 100 awards -> tolerance = max(3, 0.01%) = 3.
            # A live total of 89 leaves a gap of 11, above tolerance, for
            # BOTH units -- only the disclosed-stale one is spared an error.
            def fake_live_total(agency, first_fy, last_fy):
                return 89

            with patch("scripts.validate_nih.live_reporter_total",
                       side_effect=fake_live_total), \
                    patch("scripts.validate_nih.live_mechanism_partition",
                         return_value={"unfiltered": 0, "extramural": 0, "intramural": 0}):
                summary = validate(repo_root=root, live=True)

            self.assertTrue(any(
                "nih/bbb/bbb" in e and "live RePORTER total" in e
                for e in summary["errors"]
            ), summary["errors"])
            self.assertFalse(any(
                "nih/aaa/aaa" in e and "live RePORTER total" in e
                for e in summary["errors"]
            ), summary["errors"])
            self.assertTrue(any(
                w.startswith("WARNING: nih/aaa/aaa: stale since 2026-09-01")
                and "not enforced" in w
                for w in summary["warnings"]
            ), summary["warnings"])
            self.assertEqual(["nih/aaa/aaa"], summary["staleUnits"])

    def test_stale_unit_within_tolerance_still_gets_a_stale_notice(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._build_repo(root)
            write_refresh_status(root, {
                "nih/aaa/aaa": {
                    "status": "stale", "staleSince": "2026-09-01",
                    "lastAcceptedAt": None,
                    "reason": unit_stale_reason("2026-09-01"),
                },
            }, "2026-09-21T09:13:00Z")

            def fake_live_total(agency, first_fy, last_fy):
                return 100  # gap = 0, well within tolerance for either unit

            with patch("scripts.validate_nih.live_reporter_total",
                       side_effect=fake_live_total), \
                    patch("scripts.validate_nih.live_mechanism_partition",
                         return_value={"unfiltered": 0, "extramural": 0, "intramural": 0}):
                summary = validate(repo_root=root, live=True)

            self.assertEqual([], summary["errors"])
            self.assertEqual([], summary["warnings"])
            self.assertEqual(["nih/aaa/aaa"], summary["staleUnits"])
            # The normal decomposition note is still present, plus a
            # distinct stale notice.
            self.assertTrue(any(
                n.startswith("nih/aaa/aaa: live decomposition")
                for n in summary["notes"]
            ), summary["notes"])
            self.assertTrue(any(
                "nih/aaa/aaa: stale since 2026-09-01" in n
                for n in summary["notes"]
            ), summary["notes"])


if __name__ == "__main__":
    unittest.main()
