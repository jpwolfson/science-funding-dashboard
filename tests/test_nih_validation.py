import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from adapters.common import write_store
from scripts.validate_nih import (live_mechanism_partition, read_store,
                                  within_relative)


def award(award_id="nih:1", day="2024-09-30"):
    return {
        "id": award_id,
        "date": day,
        "month": day[:7],
        "amount": 123,
        "type": "std",
        "transType": "Standard/new award (1, R01)",
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


if __name__ == "__main__":
    unittest.main()
