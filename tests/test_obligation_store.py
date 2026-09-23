import tempfile
import unittest
from pathlib import Path

from adapters.obligation_common import (
    account_period_status,
    baseline_period_notes_problems,
    baseline_pin_problems,
    canonical_period,
    check_final_period_reported,
    classify_file_b_periods,
    covers_and_effective,
    file_b_row_counts_from_provenance,
    fy_cumulative_cents,
    load_store,
    merge_period_status,
    normalize_award_url,
    normalize_event,
    period_info,
    write_partition_provenance,
    write_store,
)


def event(event_id="e1", amount=123, period="FY2024P02", source="file_c"):
    return normalize_event({"id": event_id, "source": source,
        "submissionPeriod": period, "federalAccount": "089-0222",
        "programActivityCode": "0001", "programActivityName": "BES",
        "programActivityReportingKey": "park", "amountCents": amount,
        "awardId": "A1" if source == "file_c" else "", "linked": source == "file_c"})


class ObligationStoreTests(unittest.TestCase):
    def test_period_is_submission_period(self):
        self.assertEqual((2024, 2, "2023-11-30"),
                         (period_info("FY2024P02")[0], period_info("FY2024P02")[1],
                          period_info("FY2024P02")[2].isoformat()))
        self.assertEqual("2024-03-31", period_info("FY2024Q2")[2].isoformat())
        self.assertEqual("FY2024P06", canonical_period("FY2024Q2"))
        with self.assertRaises(ValueError):
            period_info("FY2024P01")

    def test_deterministic_gzip_and_negative_cents(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events"
            rows = [event(amount=-125), event("e2", 300)]
            write_store(path, rows)
            first = (path / "FY2024.csv.gz").read_bytes()
            write_store(path, list(reversed(rows)))
            self.assertEqual(first, (path / "FY2024.csv.gz").read_bytes())
            loaded = load_store(path)
            self.assertEqual([-125, 300], sorted(e["amountCents"] for e in loaded))

    def test_duplicate_id_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                write_store(Path(tmp), [event(), event()])

    def test_internal_usaspending_permalink_becomes_public(self):
        expected = "https://www.usaspending.gov/award/CONT_AWD_123/"
        self.assertEqual(expected, normalize_award_url(
            "localhost:3000/award/CONT_AWD_123/"))
        self.assertEqual(expected, normalize_award_url(
            "http://localhost:3000/award/CONT_AWD_123/"))
        self.assertEqual(expected, normalize_award_url(expected))

    def test_classify_zero_and_half_drop_rows_as_not_reported(self):
        status = classify_file_b_periods({
            "FY2025P02": 228, "FY2025P03": 0, "FY2025P04": 227,
            "FY2025P05": 100,  # < half of 227
        })
        self.assertEqual({
            "FY2025P02": "reported", "FY2025P03": "notReported",
            "FY2025P04": "reported", "FY2025P05": "notReported",
        }, status)

    def test_classify_first_period_zero_rows_is_not_reported_without_prior(self):
        # No previous *reported* period exists yet: only the zero-row rule
        # applies (not the half-of-previous rule).
        status = classify_file_b_periods({"FY2022P02": 0, "FY2022P03": 5})
        self.assertEqual(
            {"FY2022P02": "notReported", "FY2022P03": "reported"}, status)

    def test_final_period_not_reported_is_a_hard_error_at_p12(self):
        status = classify_file_b_periods({"FY2025P11": 228, "FY2025P12": 1})
        with self.assertRaisesRegex(ValueError, "FY2025P12 is notReported"):
            check_final_period_reported(status, fy_complete=False)

    def test_final_period_not_reported_is_a_hard_error_when_fy_complete(self):
        # Not P12 numerically, but the fiscal year's own baseline says it
        # is complete: still cannot reconcile without a reported endpoint.
        status = classify_file_b_periods({"FY2017P06": 40, "FY2017P07": 1})
        with self.assertRaisesRegex(ValueError, "FY2017P07 is notReported"):
            check_final_period_reported(status, fy_complete=True)

    def test_final_period_not_reported_mid_year_is_not_an_error(self):
        status = classify_file_b_periods({"FY2026P09": 40, "FY2026P10": 1})
        check_final_period_reported(status, fy_complete=False)  # no raise

    def test_sustained_drop_is_a_restructuring_not_a_gap(self):
        # commerce/census-current-surveys FY2020: rows settle from ~100 at
        # P06 to ~45 from P07 on and never recover -- a real regime change,
        # not a stub. Every later period stays below half of P06's rows,
        # so the whole run is `reported`, each becoming the next baseline.
        status = classify_file_b_periods({
            "FY2020P03": 96, "FY2020P04": 96, "FY2020P05": 96,
            "FY2020P06": 101, "FY2020P07": 44, "FY2020P08": 44,
            "FY2020P09": 46, "FY2020P10": 49, "FY2020P11": 50,
            "FY2020P12": 50,
        })
        self.assertTrue(all(value == "reported" for value in status.values()),
                        status)

    def test_transient_dip_that_recovers_stays_not_reported(self):
        # dod/navy-rdte FY2025: P11 (1 row) is a stub against a 239-row
        # baseline, but P12 recovers to 243 -- the dip stays notReported
        # and P12 becomes the new baseline.
        status = classify_file_b_periods({
            "FY2025P10": 239, "FY2025P11": 1, "FY2025P12": 243,
        })
        self.assertEqual({
            "FY2025P10": "reported", "FY2025P11": "notReported",
            "FY2025P12": "reported",
        }, status)

    def test_backward_floor_catches_a_run_of_stub_periods(self):
        # commerce/noaa-orf FY2024: P04-P08 (5-10 rows) are each individually
        # "reported" against their immediate neighbors (no >50% drop
        # between consecutive stub periods), but are all far below a
        # quarter of P12's 551 rows -- the backward rule catches them even
        # though the forward rule alone would not.
        status = classify_file_b_periods({
            "FY2024P02": 0, "FY2024P03": 0, "FY2024P04": 6, "FY2024P05": 6,
            "FY2024P06": 5, "FY2024P07": 10, "FY2024P08": 9,
            "FY2024P09": 0, "FY2024P10": 0, "FY2024P11": 0, "FY2024P12": 551,
        })
        for period in ("FY2024P02", "FY2024P03", "FY2024P04", "FY2024P05",
                      "FY2024P06", "FY2024P07", "FY2024P08", "FY2024P09",
                      "FY2024P10", "FY2024P11"):
            self.assertEqual("notReported", status[period], period)
        self.assertEqual("reported", status["FY2024P12"])

    def test_backward_floor_does_not_misfire_on_a_small_account(self):
        # A genuinely small account whose early periods are proportionately
        # smaller, not stub-sized, must not be flagged: 3/8 = 0.375 is
        # above the 0.25 floor.
        status = classify_file_b_periods({
            "FY2024P02": 3, "FY2024P03": 4, "FY2024P04": 5, "FY2024P05": 6,
            "FY2024P06": 6, "FY2024P07": 7, "FY2024P08": 7, "FY2024P12": 8,
        })
        self.assertTrue(all(value == "reported" for value in status.values()),
                        status)

    def test_covers_and_effective_span_a_single_gap(self):
        status = {"FY2025P10": "reported", "FY2025P11": "notReported",
                  "FY2025P12": "reported"}
        covers, effective = covers_and_effective(status)
        self.assertEqual({"FY2025P12": ["FY2025P11", "FY2025P12"]}, covers)
        self.assertEqual({
            "FY2025P10": "FY2025P10", "FY2025P11": "FY2025P12",
            "FY2025P12": "FY2025P12",
        }, effective)

    def test_covers_and_effective_leaves_a_dangling_tail_uncovered(self):
        status = {"FY2025P10": "reported", "FY2025P11": "notReported"}
        covers, effective = covers_and_effective(status)
        self.assertEqual({}, covers)
        self.assertEqual({"FY2025P10": "FY2025P10"}, effective)
        self.assertNotIn("FY2025P11", effective)

    def test_file_b_row_counts_from_provenance_reads_accepted_downloads(self):
        provenance = {
            "fiscalYear": 2025,
            "downloads": [
                {"acceptedRequestScope": {
                    "download_types": ["object_class_program_activity"],
                    "filters": {"fy": 2025, "period": 11}},
                 "statusRowCount": 1},
                {"acceptedRequestScope": {
                    "download_types": ["award_financial"],
                    "filters": {"fy": 2025, "period": 12}},
                 "statusRowCount": 900},
            ],
        }
        self.assertEqual({"FY2025P11": 1},
                         file_b_row_counts_from_provenance(provenance))

    def test_account_period_status_matches_pull_time_classification(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp) / "events"
            store.mkdir()
            rows = [event(event_id="p10", period="FY2025P10"),
                    event(event_id="p12", period="FY2025P12")]
            write_store(store, rows)
            write_partition_provenance(store, 2025, {
                "collectionStatus": "accepted",
                "downloads": [
                    {"acceptedRequestScope": {
                        "download_types": ["object_class_program_activity"],
                        "filters": {"fy": 2025, "period": 10}},
                     "statusRowCount": 228},
                    {"acceptedRequestScope": {
                        "download_types": ["object_class_program_activity"],
                        "filters": {"fy": 2025, "period": 11}},
                     "statusRowCount": 1},
                    {"acceptedRequestScope": {
                        "download_types": ["object_class_program_activity"],
                        "filters": {"fy": 2025, "period": 12}},
                     "statusRowCount": 243},
                ],
            })
            status = account_period_status(store, load_store(store), partial_fys=set())
            self.assertEqual({
                "FY2025P10": "reported", "FY2025P11": "notReported",
                "FY2025P12": "reported",
            }, status)

    def test_account_period_status_never_raises_even_on_p12_not_reported(self):
        # A hard P12/complete-year error is a validation-time concern
        # (scripts/validate_obligations.py calls check_final_period_reported
        # itself, per fiscal year, and appends an error) -- not something
        # account_period_status raises, which would abort rebuilding every
        # other account's dashboard in the same process over one already-
        # committed historical fiscal year's row-count anomaly.
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp) / "events"
            store.mkdir()
            rows = [event(event_id="p12", period="FY2020P12")]
            write_store(store, rows)
            write_partition_provenance(store, 2020, {
                "collectionStatus": "accepted",
                "downloads": [
                    {"acceptedRequestScope": {
                        "download_types": ["object_class_program_activity"],
                        "filters": {"fy": 2020, "period": 6}},
                     "statusRowCount": 100},
                    {"acceptedRequestScope": {
                        "download_types": ["object_class_program_activity"],
                        "filters": {"fy": 2020, "period": 12}},
                     "statusRowCount": 40},
                ],
            })
            status = account_period_status(store, load_store(store), partial_fys=set())
            self.assertEqual("notReported", status["FY2020P12"])
            with self.assertRaisesRegex(ValueError, "FY2020P12 is notReported"):
                check_final_period_reported(status, fy_complete=True)

    def test_fy_cumulative_cents_telescopes_through_each_label(self):
        # W19: this is the single formula account_period_status (rebuild/
        # validator) and the pull path (scripts/pull_obligation_account.py)
        # both call, so their two derivations of rule 4's input cannot
        # drift apart.
        events = [
            event(event_id="p2", amount=1_000, period="FY2024P02"),
            event(event_id="p3", amount=2_000, period="FY2024P03"),
            event(event_id="p5a", amount=250, period="FY2024P05"),
            event(event_id="p5b", amount=250, period="FY2024P05"),
        ]
        result = fy_cumulative_cents(
            events, ["FY2024P02", "FY2024P03", "FY2024P05"]
        )
        self.assertEqual({
            "FY2024P02": 1_000, "FY2024P03": 3_000, "FY2024P05": 3_500,
        }, result)
        # A label with no events at or before it sums to zero, not KeyError.
        self.assertEqual(
            {"FY2024P02": 0},
            fy_cumulative_cents([], ["FY2024P02"]),
        )

    def test_account_period_status_dollar_transient_regression_pin(self):
        # Regression pin for the W19 refactor (account_period_status now
        # calls the extracted fy_cumulative_cents helper instead of an
        # inline cumulative-sum comprehension): must still derive the
        # identical rule-4 result it did before the refactor on the real
        # dod/navy-rdte FY2024 P10/P11/P12 cents (same figures as
        # DollarTransientClassificationTests in test_usaspending_obligations.py).
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp) / "events"
            store.mkdir()
            rows = [
                event(event_id="p10", amount=2_540_914_848_134, period="FY2024P10"),
                event(event_id="p11",
                     amount=5_460_831_665_422 - 2_540_914_848_134,
                     period="FY2024P11"),
                event(event_id="p12",
                     amount=2_956_285_398_710 - 5_460_831_665_422,
                     period="FY2024P12"),
            ]
            write_store(store, rows)
            write_partition_provenance(store, 2024, {
                "collectionStatus": "accepted",
                "downloads": [
                    {"acceptedRequestScope": {
                        "download_types": ["object_class_program_activity"],
                        "filters": {"fy": 2024, "period": p}},
                     "statusRowCount": 200}
                    for p in (10, 11, 12)
                ],
            })
            status = account_period_status(store, load_store(store), partial_fys=set())
            self.assertEqual({
                "FY2024P10": "reported", "FY2024P11": "notReported",
                "FY2024P12": "reported",
            }, status)

    def test_period_notes_schema_is_a_list_of_period_and_note(self):
        self.assertEqual([], baseline_period_notes_problems({"status": "complete"}))
        self.assertEqual([], baseline_period_notes_problems({
            "status": "complete", "obligationsCents": 100,
            "periodNotes": [{"period": 11, "note": "Provisional note."}],
        }))
        self.assertTrue(baseline_period_notes_problems({"periodNotes": []}))
        self.assertTrue(baseline_period_notes_problems({
            "periodNotes": [{"period": 1, "note": "x"}]}))  # out of range
        self.assertTrue(baseline_period_notes_problems({
            "periodNotes": [{"period": 11, "note": "  "}]}))  # blank note
        self.assertTrue(baseline_period_notes_problems({
            "periodNotes": "not a list"}))
        # publicNote is optional; when present it must be a non-empty string.
        self.assertEqual([], baseline_period_notes_problems({
            "status": "complete", "obligationsCents": 100,
            "periodNotes": [{"period": 11, "note": "Provisional note.",
                              "publicNote": "Reader-facing statement."}],
        }))
        self.assertTrue(baseline_period_notes_problems({
            "periodNotes": [{"period": 11, "note": "x", "publicNote": ""}]}))
        self.assertTrue(baseline_period_notes_problems({
            "periodNotes": [{"period": 11, "note": "x", "publicNote": "   "}]}))
        self.assertTrue(baseline_period_notes_problems({
            "periodNotes": [{"period": 11, "note": "x", "publicNote": 7}]}))
        # Reaches the shared registry-tier lint through baseline_pin_problems.
        self.assertTrue(any(
            "periodNotes" in problem for problem in baseline_pin_problems({
                "status": "complete", "obligationsCents": 100,
                "periodNotes": [{"period": 99, "note": "x"}],
            })
        ))

    def test_merge_period_status_requires_unanimous_not_reported(self):
        merged = merge_period_status([
            {"FY2025P11": "notReported"},
            {"FY2025P11": "notReported"},
        ])
        self.assertEqual({"FY2025P11": "notReported"}, merged)
        mixed = merge_period_status([
            {"FY2025P11": "notReported"},
            {"FY2025P11": "reported"},
        ])
        self.assertEqual({"FY2025P11": "reported"}, mixed)


if __name__ == "__main__":
    unittest.main()
