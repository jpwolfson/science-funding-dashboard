import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from adapters.common import write_store
from adapters.nih_reporter import encode_trans_type
from scripts.validate_nih import (in_data_book_scope,
                                  live_mechanism_partition, read_store,
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


if __name__ == "__main__":
    unittest.main()
