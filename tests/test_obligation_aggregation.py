import unittest

from adapters.obligation_common import aggregate, normalize_event
from scripts.validate_obligations import reporting_period_problems


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

    def test_top_flows_use_gross_components_before_same_event_netting(self):
        row = ev("mixed", 600, "FY2024P02", award="A", recipient="U1")
        row["grossPositiveCents"] = 1000
        row["grossNegativeCents"] = -400
        fy = aggregate([row], 2024)["fiscalYears"][0]
        self.assertEqual(1000, fy["positiveFlows"][0]["amountCents"])
        self.assertEqual(-400, fy["negativeFlows"][0]["amountCents"])
        self.assertEqual(600, fy["positiveFlows"][0]["netAmountCents"])
        self.assertEqual(600, fy["negativeFlows"][0]["netAmountCents"])

    def test_coverage_contract_marks_historical_partial_year(self):
        rows = [ev("1", 100, "FY2017P06")]
        out = aggregate(
            rows, current_fy=2026,
            covered_periods={"FY2017P06", "FY2017P12", "FY2026P02"},
            partial_fys={2017, 2026},
        )
        by_fy = {row["fy"]: row for row in out["fiscalYears"]}
        self.assertTrue(by_fy[2017]["partial"])
        self.assertTrue(by_fy[2026]["partial"])
        self.assertEqual(0, by_fy[2026]["netObligationsCents"])
        self.assertEqual("FY2026P02", out["asOfPeriod"])

    def test_zero_activity_periods_are_materialized_for_child_charts(self):
        out = aggregate(
            [ev("1", 100, "FY2024P02")], current_fy=2024,
            covered_periods={"FY2024P02", "FY2024P03", "FY2024P04"},
            partial_fys=set(),
        )
        self.assertEqual(
            ["FY2024P02", "FY2024P03", "FY2024P04"],
            [row["submissionPeriod"] for row in out["reportingPeriods"]],
        )
        self.assertEqual(
            [100, 0, 0],
            [row["netObligationsCents"] for row in out["reportingPeriods"]],
        )
        self.assertFalse(out["fiscalYears"][0]["partial"])

    def test_not_reported_period_row_has_null_activity_and_covers_note(self):
        rows = [ev("p10", 10000, "FY2025P10"), ev("p12", 1300, "FY2025P12")]
        period_status = {"FY2025P10": "reported", "FY2025P11": "notReported",
                         "FY2025P12": "reported"}
        out = aggregate(rows, current_fy=2025,
                        covered_periods={"FY2025P10", "FY2025P11", "FY2025P12"},
                        partial_fys=set(), period_status=period_status)
        by_period = {row["submissionPeriod"]: row for row in out["reportingPeriods"]}
        self.assertEqual("notReported", by_period["FY2025P11"]["status"])
        self.assertIsNone(by_period["FY2025P11"]["netObligationsCents"])
        self.assertEqual("reported", by_period["FY2025P12"]["status"])
        self.assertEqual(["FY2025P11", "FY2025P12"],
                         by_period["FY2025P12"]["coversPeriods"])
        self.assertNotIn("coversPeriods", by_period["FY2025P10"])

    def test_cumulative_point_holds_last_reported_value_at_not_reported_period(self):
        rows = [ev("p10", 10000, "FY2025P10"), ev("p12", 1300, "FY2025P12")]
        period_status = {"FY2025P10": "reported", "FY2025P11": "notReported",
                         "FY2025P12": "reported"}
        out = aggregate(rows, current_fy=2025,
                        covered_periods={"FY2025P10", "FY2025P11", "FY2025P12"},
                        partial_fys=set(), period_status=period_status)
        points = {p["submissionPeriod"]: p for p in out["fyCumulative"][0]["points"]}
        self.assertTrue(points["FY2025P11"]["held"])
        self.assertEqual(points["FY2025P10"]["netObligationsCents"],
                         points["FY2025P11"]["netObligationsCents"])
        self.assertNotIn("held", points["FY2025P12"])
        # The cumulative endpoint invariant still holds exactly.
        self.assertEqual(out["fiscalYears"][0]["netObligationsCents"],
                         points["FY2025P12"]["netObligationsCents"])

    def test_leading_not_reported_run_holds_null_not_zero(self):
        # commerce/noaa-orf FY2024 shape: a run of notReported periods at
        # the START of the fiscal year, before any period has ever been
        # reported. The cumulative is genuinely unknown there, not $0 --
        # the site must be able to skip these points rather than draw a
        # false flat-zero line before the first real reported point.
        rows = [ev("p12", 725000, "FY2024P12")]
        period_status = {"FY2024P02": "notReported", "FY2024P03": "notReported",
                         "FY2024P11": "notReported", "FY2024P12": "reported"}
        out = aggregate(rows, current_fy=2024,
                        covered_periods={"FY2024P02", "FY2024P03",
                                        "FY2024P11", "FY2024P12"},
                        partial_fys=set(), period_status=period_status)
        points = {p["submissionPeriod"]: p for p in out["fyCumulative"][0]["points"]}
        for label in ("FY2024P02", "FY2024P03", "FY2024P11"):
            self.assertTrue(points[label]["held"], label)
            self.assertIsNone(points[label]["netObligationsCents"], label)
            self.assertIsNone(points[label]["netObligations"], label)
            self.assertIsNone(points[label]["distinctLinkedAwards"], label)
        # The FY's own final (reported) point is unaffected: it holds its
        # real value and is not marked held.
        self.assertNotIn("held", points["FY2024P12"])
        self.assertEqual(725000, points["FY2024P12"]["netObligationsCents"])

    def test_leading_not_reported_run_then_a_later_reported_period_holds_real_value(self):
        # Once a reported period exists earlier in the fiscal year, a later
        # notReported period reverts to the ordinary held-at-real-value
        # behavior (unaffected by the leading-run fix).
        rows = [ev("p10", 10000, "FY2025P10"), ev("p12", 1300, "FY2025P12")]
        period_status = {"FY2025P02": "notReported", "FY2025P10": "reported",
                         "FY2025P11": "notReported", "FY2025P12": "reported"}
        out = aggregate(rows, current_fy=2025,
                        covered_periods={"FY2025P02", "FY2025P10",
                                        "FY2025P11", "FY2025P12"},
                        partial_fys=set(), period_status=period_status)
        points = {p["submissionPeriod"]: p for p in out["fyCumulative"][0]["points"]}
        self.assertIsNone(points["FY2025P02"]["netObligationsCents"])
        self.assertTrue(points["FY2025P11"]["held"])
        self.assertEqual(points["FY2025P10"]["netObligationsCents"],
                         points["FY2025P11"]["netObligationsCents"])

    def test_dangling_not_reported_final_period_keeps_a_real_endpoint(self):
        # The most recent period is itself notReported with nothing after
        # it yet: the endpoint invariant must still hold, so it is shown at
        # its real (if incomplete) computed value rather than held.
        rows = [ev("p10", 10000, "FY2025P10")]
        period_status = {"FY2025P10": "reported", "FY2025P11": "notReported"}
        out = aggregate(rows, current_fy=2025,
                        covered_periods={"FY2025P10", "FY2025P11"},
                        partial_fys={2025}, period_status=period_status)
        points = {p["submissionPeriod"]: p for p in out["fyCumulative"][0]["points"]}
        self.assertNotIn("held", points["FY2025P11"])
        self.assertEqual(out["fiscalYears"][0]["netObligationsCents"],
                         points["FY2025P11"]["netObligationsCents"])

    def _covering_row_case(self):
        # dod/navy-rdte FY2024 P11/P12 shape (issue #88): the transient
        # period P11 is notReported but still carries its own File B
        # residual (+) and File C (+) events; P12 carries a large reversal.
        rows = [ev("p10", 10000, "FY2025P10"),
                ev("p11c", 700, "FY2025P11", award="A2"),
                ev("p11r", 29200, "FY2025P11", source="file_b_residual", award=""),
                ev("p12c", -300, "FY2025P12", award="A3"),
                ev("p12r", -25050, "FY2025P12", source="file_b_residual", award="")]
        period_status = {"FY2025P10": "reported", "FY2025P11": "notReported",
                         "FY2025P12": "reported"}
        return aggregate(rows, current_fy=2025,
                         covered_periods={"FY2025P10", "FY2025P11", "FY2025P12"},
                         partial_fys=set(), period_status=period_status)

    def test_covering_row_spans_every_covered_period(self):
        out = self._covering_row_case()
        by_period = {row["submissionPeriod"]: row for row in out["reportingPeriods"]}
        points = {p["submissionPeriod"]: p for p in out["fyCumulative"][0]["points"]}
        p12 = by_period["FY2025P12"]
        self.assertEqual(points["FY2025P12"]["netObligationsCents"]
                         - points["FY2025P10"]["netObligationsCents"],
                         p12["netObligationsCents"])
        self.assertEqual(700 - 300, p12["awardLinkedObligationsCents"])
        self.assertEqual(29200 - 25050, p12["residualObligationsCents"])
        # File C + residual = File B stays exact on the covering row.
        self.assertEqual(p12["netObligationsCents"],
                         p12["awardLinkedObligationsCents"]
                         + p12["residualObligationsCents"])
        self.assertEqual(700 + 29200, p12["grossObligationsCents"])
        self.assertEqual(-300 - 25050, p12["deobligationsCents"])
        self.assertEqual(2, p12["distinctLinkedAwards"])

    def test_reported_rows_sum_to_fiscal_year_endpoint(self):
        out = self._covering_row_case()
        reported = [row["netObligationsCents"] for row in out["reportingPeriods"]
                    if row["status"] == "reported"]
        self.assertEqual(out["fiscalYears"][0]["netObligationsCents"], sum(reported))


    def test_validator_flags_a_covering_row_that_drops_absorbed_periods(self):
        out = self._covering_row_case()
        self.assertEqual([], reporting_period_problems(out))
        p12 = next(r for r in out["reportingPeriods"]
                   if r["submissionPeriod"] == "FY2025P12")
        # The pre-fix shape: the covering row carried only P12's own events.
        p12.update(netObligationsCents=-25350, awardLinkedObligationsCents=-300,
                   residualObligationsCents=-25050)
        problems = reporting_period_problems(out)
        self.assertTrue(any("FY2025P12: row -25350 != cumulative difference 4550"
                            in p for p in problems), problems)
        self.assertTrue(any(p.startswith("FY2025: reported rows sum to")
                            for p in problems), problems)


if __name__ == "__main__":
    unittest.main()
