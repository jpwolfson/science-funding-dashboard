import tempfile
import unittest
from pathlib import Path

from adapters.obligation_common import (
    account_period_status,
    canonical_period,
    check_final_period_reported,
    classify_file_b_periods,
    covers_and_effective,
    file_b_row_counts_from_provenance,
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
