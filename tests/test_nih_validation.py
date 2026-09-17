import gzip
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from adapters.common import write_store
from adapters.nih_reporter import (CHANGES_HEADER, append_changes_ledger,
                                   changes_ledger_path, encode_trans_type)
from scripts.validate_nih import (_check_changes_ledger, in_data_book_scope,
                                  live_mechanism_partition,
                                  reconcile_live_total, read_store,
                                  within_relative)


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


if __name__ == "__main__":
    unittest.main()
