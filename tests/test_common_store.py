import gzip
import tempfile
import unittest
from pathlib import Path

from adapters.common import load_store, store_exists, write_store


def award(award_id, day, amount=1):
    return {
        "id": award_id,
        "date": day,
        "month": day[:7],
        "amount": amount,
        "type": "other",
        "transType": "Other award",
        "title": f"Award {award_id}",
        "awardee": "Example University",
    }


class ShardedStoreTests(unittest.TestCase):
    def test_gzip_shards_round_trip_and_are_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            leaf = Path(tmp) / "nih" / "nci" / "nci"
            store = leaf / "awards"
            awards = [award("nih:1", "2024-09-30"),
                      award("nih:2", "2024-10-01", 2)]
            write_store(store, awards)

            self.assertTrue(store_exists(leaf))
            self.assertEqual([p.name for p in sorted(store.glob("FY*.csv.gz"))],
                             ["FY2024.csv.gz", "FY2025.csv.gz"])
            before = {p.name: p.read_bytes() for p in store.iterdir()}
            write_store(store, list(reversed(awards)))
            after = {p.name: p.read_bytes() for p in store.iterdir()}
            self.assertEqual(before, after)
            self.assertEqual(set(load_store(leaf)), {"nih:1", "nih:2"})

    def test_corrected_date_does_not_leave_a_duplicate_in_old_shard(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp) / "awards"
            write_store(store, [award("nih:1", "2024-09-30")])
            write_store(store, [award("nih:1", "2024-10-01")])

            loaded = load_store(store)
            self.assertEqual(loaded["nih:1"]["date"], "2024-10-01")
            with gzip.open(store / "FY2024.csv.gz", "rt") as fh:
                self.assertEqual(len(fh.readlines()), 1)  # header only

    def test_empty_sharded_store_has_a_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp) / "awards"
            write_store(store, [])
            self.assertTrue(store_exists(store))
            self.assertEqual(load_store(store), {})
            self.assertTrue((store / "manifest.json").exists())


if __name__ == "__main__":
    unittest.main()
