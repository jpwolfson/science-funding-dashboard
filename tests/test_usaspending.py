import unittest
from pathlib import Path
from unittest.mock import patch

from adapters.common import load_store, write_store
from adapters.usaspending import USAspendingPull


def row(index, fy=2025, amount=1000, group="grants"):
    description_field = ("Contract Award Type" if group == "contracts"
                         else "Award Type")
    return {
        "internal_id": index,
        "generated_internal_id": f"AWARD_{index}",
        "Award ID": f"DISPLAY-{index}",
        "Recipient Name": "Example University",
        "Base Obligation Date": f"{fy - 1}-10-15",
        "Award Amount": amount,
        "Description": "Example science award",
        description_field: "PROJECT GRANT" if group == "grants" else "CONTRACT",
    }


def puller():
    return USAspendingPull(
        {
            "awarding_agency": {"tier": "toptier", "name": "Department of Energy"},
            "federal_account": "089-0222",
        },
        {"min_total": 0, "max_total": 1000, "max_monthly": 1000},
        Path("unused"),
    )


class USAspendingTests(unittest.TestCase):
    def test_filters_pin_base_award_semantics_and_account(self):
        filters = puller().filters(2025, "grants")
        self.assertEqual(filters["time_period"], [{
            "start_date": "2024-10-01", "end_date": "2025-09-30",
            "date_type": "new_awards_only",
        }])
        self.assertEqual(filters["treasury_account_components"], [
            {"aid": "089", "main": "0222"},
        ])

    def test_award_groups_match_count_endpoint_categories(self):
        from adapters.usaspending import AWARD_GROUPS, COUNT_KEYS

        self.assertEqual(AWARD_GROUPS["direct_payments"][:2], ["06", "10"])
        self.assertEqual(
            AWARD_GROUPS["other_financial_assistance"][:3],
            ["09", "11", "-1"],
        )
        self.assertEqual(COUNT_KEYS["direct_payments"], "direct_payments")
        self.assertEqual(COUNT_KEYS["other_financial_assistance"], "other")

    def test_cursor_pagination_requires_count_exactness(self):
        rows = [row(i) for i in range(1, 102)]

        def fake_post(url, payload, retries=5):
            del url, retries
            start = 0 if "last_record_unique_id" not in payload else 100
            page = rows[start:start + 100]
            has_next = start + len(page) < len(rows)
            return {
                "spending_level": "awards",
                "results": page,
                "page_metadata": {
                    "hasNext": has_next,
                    "last_record_unique_id": page[-1]["internal_id"] if has_next else None,
                    "last_record_sort_value": page[-1]["generated_internal_id"] if has_next else None,
                },
                "messages": [],
            }

        with patch("adapters.usaspending.api_post", side_effect=fake_post):
            result = puller().fetch_pass(2025, "grants", "asc", 101)
        self.assertEqual(len(result), 101)

    def test_duplicate_displacement_is_rejected(self):
        duplicate_page = [row(1), row(1)]
        with patch("adapters.usaspending.api_post", return_value={
            "spending_level": "awards", "results": duplicate_page,
            "page_metadata": {"hasNext": False}, "messages": [],
        }):
            with self.assertRaisesRegex(RuntimeError, "unique awards"):
                puller().fetch_pass(2025, "grants", "asc", 2)

    def test_opposite_order_values_must_match(self):
        asc = {"AWARD_1": row(1, amount=1000)}
        desc = {"AWARD_1": row(1, amount=999)}
        with patch.object(USAspendingPull, "fetch_count", side_effect=[1, 1]), \
             patch.object(USAspendingPull, "fetch_pass", side_effect=[asc, desc]), \
             patch("adapters.usaspending.time.sleep"):
            with self.assertRaisesRegex(RuntimeError, "snapshots disagree"):
                puller().fetch_slice(2025, "grants", attempts=1)

    def test_wrong_fiscal_year_and_unused_filters_are_rejected(self):
        cases = [
            ({"spending_level": "awards", "results": [row(1, fy=2024)],
              "page_metadata": {"hasNext": False}, "messages": []},
             "fiscal-year filter mismatch"),
            ({"spending_level": "awards", "results": [row(1)],
              "page_metadata": {"hasNext": False},
              "messages": ["The following filters were not used"]},
             "ignored a configured filter"),
        ]
        for response, message in cases:
            with self.subTest(message=message), \
                 patch("adapters.usaspending.api_post", return_value=response):
                with self.assertRaisesRegex(RuntimeError, message):
                    puller().fetch_pass(2025, "grants", "asc", 1)

    def test_normalize_uses_base_obligation_and_current_total(self):
        normalized = puller().normalize(row(7, amount=123456), "grants")
        self.assertEqual(normalized["id"], "usaspending:AWARD_7")
        self.assertEqual(normalized["date"], "2024-10-15")
        self.assertEqual(normalized["amount"], 123456)
        self.assertEqual(normalized["type"], "std")

    def test_mechanism_bins_survive_store_round_trip(self):
        import tempfile
        records = [
            puller().normalize(row(1, group="grants"), "grants"),
            puller().normalize(row(2, group="contracts"), "contracts"),
            puller().normalize(row(3), "direct_payments"),
        ]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "awards.csv"
            write_store(path, records)
            loaded = load_store(path)
        self.assertEqual([loaded[a["id"]]["type"] for a in records],
                         ["std", "cont", "fell"])


if __name__ == "__main__":
    unittest.main()
