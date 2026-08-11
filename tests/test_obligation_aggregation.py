import unittest

from adapters.obligation_common import aggregate, normalize_event


def ev(i, amount, period, pa="0001", award="A1", source="file_c", recipient="Lab"):
    return normalize_event({"id": i, "source": source, "submissionPeriod": period,
        "federalAccount": "089-0222", "programActivityCode": pa,
        "programActivityName": pa, "amountCents": amount, "awardId": award,
        "linked": source == "file_c", "recipientUEI": recipient,
        "recipient": recipient, "grossPositiveCents": max(amount, 0),
        "grossNegativeCents": min(amount, 0)})


class ObligationAggregationTests(unittest.TestCase):
    def test_signed_totals_distinct_union_and_endpoint(self):
        rows = [ev("1", 10000, "FY2024P02"),
                ev("2", -2500, "FY2024P03", pa="0002"),
                ev("3", 5000, "FY2024P03", award="A2"),
                ev("r", 1000, "FY2024P03", source="file_b_residual", award="")]
        out = aggregate(rows, 2024)
        self.assertEqual(13500, out["netObligationsCents"])
        self.assertEqual(135, out["totalNetObligations"])
        self.assertEqual(12500, out["awardLinkedObligationsCents"])
        self.assertEqual(1000, out["residualObligationsCents"])
        self.assertEqual(2, out["distinctLinkedAwards"])
        self.assertEqual(-2500, out["deobligationsCents"])
        self.assertEqual(out["fiscalYears"][0]["netObligationsCents"],
                         out["fyCumulative"][0]["points"][-1]["netObligationsCents"])

    def test_top_recipient_and_signed_flows_are_file_c_only(self):
        rows = [ev("1", 500, "FY2024P02", award="A", recipient="U1"),
                ev("2", -900, "FY2024P02", award="B", recipient="U2"),
                ev("3", 50000, "FY2024P02", source="file_b_residual", award="")]
        fy = aggregate(rows, 2024)["fiscalYears"][0]
        self.assertEqual("U1", fy["topRecipients"][0]["recipient"])
        self.assertEqual(-900, fy["negativeFlows"][0]["amountCents"])
        self.assertEqual(1, len(fy["positiveFlows"]))


if __name__ == "__main__":
    unittest.main()
