import http.client
import io
import unittest
from unittest.mock import patch

from adapters.usaspending_obligations import (
    _json, combine_file_b_file_c, file_b_period_events, parse_file_c,
)


ALIASES = {"0001": {"code": "0001", "name": "BES", "park": "PARK1"},
           "PARK1": {"code": "0001", "name": "BES", "park": "PARK1"},
           "0000": {"code": "0000", "name": "Unknown / other", "park": ""}}


class USAspendingObligationTests(unittest.TestCase):
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
        key = ("0001", "BES", "PARK1", "25.1", "D", "", "")
        vanished = ("0001", "BES", "PARK1", "25.2", "D", "", "")
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

    def test_quarterly_file_c_joins_period_ending_file_b(self):
        parts = {"Assistance.csv": [{"submission_period": "FY2017Q2",
            "federal_account_symbol": "089-0222", "program_activity_code": "0001",
            "program_activity_name": "BES", "award_unique_key": "A",
            "transaction_obligated_amount": "1.00"}], "Contracts.csv": [], "Unlinked.csv": []}
        c = parse_file_c(parts, "089-0222", ALIASES)
        self.assertEqual("FY2017P06", c[0]["submissionPeriod"])


if __name__ == "__main__":
    unittest.main()
