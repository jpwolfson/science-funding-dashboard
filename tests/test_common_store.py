import gzip
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from adapters.common import (load_store, store_exists, write_dashboard,
                             write_store)


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

    def test_id_count_warning_fires_when_the_store_itself_shrinks(self):
        """Source-agnostic invariant (adapters.common.write_dashboard):
        a drop in the physical store id count below the previously
        published totalAwards is a genuine data-loss signal and warns."""
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp) / "nsf" / "mps" / "dms"
            node = {"name": "DMS", "abbrev": "DMS",
                    "path": "nsf/mps/dms", "level": "division"}
            today = date(2026, 8, 17)
            awards = [award("nsf:1", "2025-01-15"),
                      award("nsf:2", "2025-01-16")]
            write_dashboard(data_dir, node, "test", awards, [], today)

            warnings = write_dashboard(
                data_dir, node, "test", awards[:1], [], today)
            self.assertEqual(
                ["invariant violated: award id count shrank from 2 to 1"],
                warnings,
            )

    def test_id_count_warning_does_not_fire_when_only_aggregation_shrinks(self):
        """A source-level soft-delete (e.g. NIH's exclusions ledger) can
        legitimately make totalAwards smaller than the physical store
        without the store itself losing a row. Passing the true physical
        store_id_count must not trip the warning in that case."""
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp) / "nih" / "nigms" / "nigms"
            node = {"name": "NIGMS", "abbrev": "NIGMS",
                    "path": "nih/nigms/nigms", "level": "division"}
            today = date(2026, 8, 17)
            awards = [award("nih:1", "2025-01-15"),
                      award("nih:2", "2025-01-16")]
            write_dashboard(data_dir, node, "test", awards, [], today,
                            store_id_count=2)

            # nih:2 becomes a soft-deleted exclusion: aggregation drops to
            # 1 award, but the physical store (store_id_count) still has 2.
            warnings = write_dashboard(
                data_dir, node, "test", awards[:1], [], today,
                store_id_count=2)
            self.assertEqual([], warnings)
            dashboard = json.loads((data_dir / "dashboard.json").read_text())
            self.assertEqual(1, dashboard["totalAwards"])

    def test_store_id_count_defaults_to_len_awards(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp) / "nsf" / "mps" / "dms"
            node = {"name": "DMS", "abbrev": "DMS",
                    "path": "nsf/mps/dms", "level": "division"}
            today = date(2026, 8, 17)
            write_dashboard(data_dir, node, "test",
                            [award("nsf:1", "2025-01-15")], [], today)
            warnings = write_dashboard(data_dir, node, "test", [], [], today)
            self.assertEqual(
                ["invariant violated: award id count shrank from 1 to 0"],
                warnings,
            )


if __name__ == "__main__":
    unittest.main()
