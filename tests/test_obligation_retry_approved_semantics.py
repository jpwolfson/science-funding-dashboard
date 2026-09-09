"""Owner-approved semantic contracts for the scheduled-obligation retry."""

import json
import unittest
from decimal import Decimal
from pathlib import Path

from adapters.usaspending_obligations import (
    alias_map,
    combine_file_b_file_c,
    file_b_period_events,
    parse_file_b_snapshot,
)


REPO = Path(__file__).resolve().parent.parent

APPROVED_NEUTRAL_IDENTITIES = {
    "commerce/noaa-orf": (
        "013-1450", "5Q0283FWZJM", 165_020_122,
    ),
    "doe/fossil-energy": (
        "089-0213", "63YPT7KCME5", 30_542_859_947,
    ),
    "doe/nuclear-energy": (
        "089-0319", "63YPT7SABUB", 64_633_246_335,
    ),
    "doe/nuclear-energy#63YPT7SACCY": (
        "089-0319", "63YPT7SACCY", 780_253_045,
    ),
    "doe/sc": (
        "089-0222", "63YPT7L1YUJ", 740_694_471_015,
    ),
    "dot/ost-research-technology": (
        "069-1730", "5RMTTPEQ0CS", 1_637_958,
    ),
}


class ApprovedRetrySemanticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        registry = json.loads(
            (REPO / "config" / "obligation_accounts.json").read_text()
        )
        cls.accounts = {row["path"]: row for row in registry["accounts"]}

    def test_neutral_identities_are_exact_and_replay_exact_cents(self):
        for key, (federal_account, park, expected_cents) in (
                APPROVED_NEUTRAL_IDENTITIES.items()):
            path = key.split("#", 1)[0]
            with self.subTest(path=path, park=park):
                account = self.accounts[path]
                slug = f"source-label-unavailable-{park.lower()}"
                expected_name = f"Source label unavailable (PARK {park})"
                matches = [
                    row for row in account["programActivities"]
                    if row["slug"] == slug
                ]
                self.assertEqual([{
                    "slug": slug,
                    "code": park,
                    "park": park,
                    "name": expected_name,
                }], matches)

                amount = str(Decimal(expected_cents) / Decimal(100))
                snapshot = parse_file_b_snapshot([{
                    "federal_account_symbol": federal_account,
                    "program_activity_reporting_key": park,
                    "program_activity_code": "",
                    "program_activity_name": "",
                    "obligations_incurred": amount,
                }], federal_account, alias_map(account))
                flows = file_b_period_events(
                    {"FY2026P10": snapshot}, federal_account
                )
                events = combine_file_b_file_c(flows, [], federal_account)
                self.assertEqual(1, len(events))
                self.assertEqual(expected_cents, events[0]["amountCents"])
                self.assertEqual(park, events[0]["programActivityCode"])
                self.assertEqual(expected_name, events[0]["programActivityName"])
                self.assertEqual(park, events[0]["_programActivityKey"])


if __name__ == "__main__":
    unittest.main()
