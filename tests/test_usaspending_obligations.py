import http.client
import io
import unittest
from unittest.mock import patch

from adapters.usaspending_obligations import (
    _json, alias_map, combine_file_b_file_c, file_b_period_events,
    parse_file_b_snapshot, parse_file_c,
)


ALIASES = {"0001": {"code": "0001", "name": "BES", "park": "PARK1"},
           "PARK1": {"code": "0001", "name": "BES", "park": "PARK1"},
           "0000": {"code": "0000", "name": "Unknown / other", "park": ""}}


class USAspendingObligationTests(unittest.TestCase):
    def test_multiple_historical_parks_normalize_to_one_canonical_activity(self):
        aliases = alias_map({"programActivities": [{
            "slug": "research", "code": "0001", "name": "Research",
            "park": "CURRENT", "parkAliases": ["HISTORICAL-A", "HISTORICAL-B"],
        }]})
        values = parse_file_b_snapshot([{
            "federal_account_symbol": "999-0001",
            "program_activity_reporting_key": "HISTORICAL-A",
            "program_activity_name": "Old research label",
            "obligations_incurred": "1.00",
        }], "999-0001", aliases)
        self.assertEqual({("0001", "0001", "Research", "CURRENT",
                           "", "", "", ""): 100},
                         values)

    def test_one_park_cannot_alias_multiple_canonical_activities(self):
        with self.assertRaisesRegex(ValueError, "maps to multiple identities"):
            alias_map({"programActivities": [
                {"slug": "first", "code": "0001", "name": "First",
                 "park": "SHARED"},
                {"slug": "second", "code": "0002", "name": "Second",
                 "parkAliases": ["SHARED"]},
            ]})

    def test_reused_code_is_disambiguated_by_exact_name(self):
        aliases = alias_map({"programActivities": [
            {"slug": "spectrum", "code": "0010",
             "name": "Spectrum Relocation Fund"},
            {"slug": "omao", "code": "0010", "name": "OMAO",
             "codeNameAliases": [
                 {"code": "0007", "name": "Office of Marine and Aviation Operations"},
             ]},
        ]})
        values = parse_file_b_snapshot([
            {"federal_account_symbol": "013-1450",
             "program_activity_code": "0010",
             "program_activity_name": "Spectrum Relocation Fund",
             "obligations_incurred": "1.00"},
            {"federal_account_symbol": "013-1450",
             "program_activity_code": "0010",
             "program_activity_name": "OMAO",
             "obligations_incurred": "2.00"},
        ], "013-1450", aliases)
        identities = {(key[0], key[1], key[2]): amount
                      for key, amount in values.items()}
        self.assertEqual({
            ("0010:spectrum", "0010", "Spectrum Relocation Fund"): 100,
            ("0010:omao", "0010", "OMAO"): 200,
        }, identities)
        flows = file_b_period_events({"FY2024P02": values}, "013-1450")
        events = combine_file_b_file_c(flows, [], "013-1450")
        self.assertEqual(300, sum(row["amountCents"] for row in events))
        self.assertEqual(2, len({row["id"] for row in events}))
        self.assertEqual({"OMAO", "Spectrum Relocation Fund"},
                         {row["programActivityName"] for row in events})

    def test_unmapped_nonblank_program_activity_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "unmapped Program Activity"):
            parse_file_b_snapshot([{
                "federal_account_symbol": "089-0222",
                "program_activity_code": "0099",
                "program_activity_name": "New unmapped activity",
                "obligations_incurred": "1.00",
            }], "089-0222", ALIASES)

    def test_unmapped_park_with_blank_legacy_fields_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "unmapped Program Activity"):
            parse_file_b_snapshot([{
                "federal_account_symbol": "089-2250",
                "program_activity_reporting_key": "NEW-PARK",
                "program_activity_code": "",
                "program_activity_name": "",
                "obligations_incurred": "1.00",
            }], "089-2250", ALIASES)

    def test_unmapped_park_does_not_fall_through_to_known_legacy_code(self):
        with self.assertRaisesRegex(ValueError, "unmapped Program Activity"):
            parse_file_b_snapshot([{
                "federal_account_symbol": "089-0222",
                "program_activity_reporting_key": "NEW-PARK",
                "program_activity_code": "0001",
                "program_activity_name": "BES",
                "obligations_incurred": "1.00",
            }], "089-0222", ALIASES)

    def test_remote_disconnect_is_retried(self):
        response = io.BytesIO(b'{"ok": true}')
        with patch(
                "adapters.usaspending_obligations.urllib.request.urlopen",
                side_effect=[http.client.RemoteDisconnected(), response]) as open_, \
             patch("adapters.usaspending_obligations.time.sleep") as sleep:
            self.assertEqual(_json("https://example.test", attempts=2), {"ok": True})
        self.assertEqual(open_.call_count, 2)
        sleep.assert_called_once_with(1)

    def test_file_b_cumulative_snapshots_are_differenced(self):
        key = ("0001", "0001", "BES", "PARK1", "25.1", "D", "", "")
        vanished = ("0001", "0001", "BES", "PARK1", "25.2", "D", "", "")
        flows = file_b_period_events({"FY2024P02": {key: 100, vanished: 50},
                                      "FY2024P03": {key: 130}}, "089-0222")
        self.assertEqual([150, -20], [row["amountCents"] for row in flows])

    def test_file_c_hidden_dimensions_collapse_without_rounding(self):
        base = {"submission_period": "FY2024P02", "federal_account_symbol": "089-0222",
                "program_activity_code": "0001", "program_activity_name": "BES",
                "award_unique_key": "A", "recipient_name": "Lab"}
        parts = {"Assistance.csv": [{**base, "transaction_obligated_amount": "1.25"},
                                     {**base, "transaction_obligated_amount": "-0.25"}],
                 "Contracts.csv": [], "Unlinked.csv": []}
        events = parse_file_c(parts, "089-0222", ALIASES)
        self.assertEqual(1, len(events))
        self.assertEqual(100, events[0]["amountCents"])
        self.assertEqual(2, events[0]["sourceRowCount"])
        self.assertEqual(-25, events[0]["grossNegativeCents"])

    def test_residual_makes_file_b_exact(self):
        c_parts = {"Assistance.csv": [{"submission_period": "FY2024P02",
            "federal_account_symbol": "089-0222", "program_activity_code": "0001",
            "program_activity_name": "BES", "award_unique_key": "A",
            "transaction_obligated_amount": "7.00"}], "Contracts.csv": [], "Unlinked.csv": []}
        c = parse_file_c(c_parts, "089-0222", ALIASES)
        b = [{"submissionPeriod": "FY2024P02", "federalAccount": "089-0222",
              "programActivityCode": "0001", "programActivityName": "BES",
              "programActivityReportingKey": "PARK1", "amountCents": 1000}]
        both = combine_file_b_file_c(b, c, "089-0222")
        self.assertEqual(1000, sum(e["amountCents"] for e in both))
        self.assertEqual(300, next(e["amountCents"] for e in both if e["source"] == "file_b_residual"))

    def test_unknown_file_c_bucket_without_file_b_anchor_nets_to_zero(self):
        c_parts = {"Assistance.csv": [{
            "submission_period": "FY2020P03",
            "federal_account_symbol": "089-0222",
            "program_activity_code": "",
            "program_activity_name": "",
            "award_unique_key": "A",
            "transaction_obligated_amount": "7.00",
        }], "Contracts.csv": [], "Unlinked.csv": []}
        c = parse_file_c(c_parts, "089-0222", ALIASES)
        both = combine_file_b_file_c([], c, "089-0222")
        self.assertEqual(0, sum(e["amountCents"] for e in both))
        self.assertEqual(["0000", "0000"],
                         [e["programActivityCode"] for e in both])
        self.assertEqual(-700, next(
            e["amountCents"] for e in both
            if e["source"] == "file_b_residual"))

    def test_known_file_c_bucket_without_file_b_anchor_still_fails(self):
        c_parts = {"Assistance.csv": [{
            "submission_period": "FY2020P03",
            "federal_account_symbol": "089-0222",
            "program_activity_code": "0001",
            "program_activity_name": "BES",
            "award_unique_key": "A",
            "transaction_obligated_amount": "7.00",
        }], "Contracts.csv": [], "Unlinked.csv": []}
        c = parse_file_c(c_parts, "089-0222", ALIASES)
        with self.assertRaisesRegex(ValueError, "absent from File B"):
            combine_file_b_file_c([], c, "089-0222")

    def test_quarterly_file_c_joins_period_ending_file_b(self):
        parts = {"Assistance.csv": [{"submission_period": "FY2017Q2",
            "federal_account_symbol": "089-0222", "program_activity_code": "0001",
            "program_activity_name": "BES", "award_unique_key": "A",
            "transaction_obligated_amount": "1.00"}], "Contracts.csv": [], "Unlinked.csv": []}
        c = parse_file_c(parts, "089-0222", ALIASES)
        self.assertEqual("FY2017P06", c[0]["submissionPeriod"])


if __name__ == "__main__":
    unittest.main()
