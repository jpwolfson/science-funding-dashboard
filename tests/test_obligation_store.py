import tempfile
import unittest
from pathlib import Path

from adapters.obligation_common import load_store, normalize_event, period_info, write_store


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


if __name__ == "__main__":
    unittest.main()
