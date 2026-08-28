import json
import unittest
from pathlib import Path

from adapters.usaspending_obligations import alias_map
from scripts.plan_obligation_refresh import plan


REPO = Path(__file__).resolve().parent.parent

ACCOUNT_META = {
    "dod/army-rdte": {
        "federalAccount": "021-2040",
        "name": "Research, Development, Test and Evaluation, Army",
        "baseline": "reference/dod_army_rdte_obligation_baseline.json",
        "programActivities": 12,
        "pins": [
            1335551508911, 1658237560606, 1941282900467,
            2944022806618, 5649553107182, 5252715920406,
            2826746057722, 2462016948008, 2432841622809,
            1899886149032,
        ],
    },
    "dod/navy-rdte": {
        "federalAccount": "017-1319",
        "name": "Research, Development, Test, and Evaluation, Navy",
        "baseline": "reference/dod_navy_rdte_obligation_baseline.json",
        "programActivities": 11,
        "pins": [
            1815670608261, 1906604818960, 1989612897412,
            2110379803523, 2104077406079, 2211161457342,
            2645738486155, 2956285398710, 2788535575911,
            2552546450852,
        ],
    },
}


class DoDObligationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        registry = json.loads(
            (REPO / "config" / "obligation_accounts.json").read_text()
        )
        cls.accounts = {
            row["path"]: row for row in registry["accounts"]
            if row["path"] in ACCOUNT_META
        }

    def test_stage_one_has_exact_account_contracts(self):
        self.assertEqual(set(ACCOUNT_META), set(self.accounts))
        for path, expected in ACCOUNT_META.items():
            with self.subTest(path=path):
                account = self.accounts[path]
                self.assertEqual(expected["federalAccount"], account["federalAccount"])
                self.assertEqual(expected["name"], account["name"])
                self.assertEqual("Department of Defense", account["agency"])
                self.assertEqual("usaspending_obligations", account["adapter"])
                self.assertEqual(expected["baseline"], account["baseline"])
                self.assertEqual(expected["programActivities"],
                                 len(account["programActivities"]))
                self.assertEqual({
                    "firstFiscalYear": 2017,
                    "firstFiscalYearPeriod": 6,
                    "regularFirstPeriod": 2,
                }, account["availability"])

    def test_stage_one_aliases_are_collision_free(self):
        for path, account in self.accounts.items():
            with self.subTest(path=path):
                aliases = alias_map(account)
                self.assertTrue(aliases)
                self.assertEqual(len(aliases), len(set(aliases)))

    def test_stage_one_preserves_exact_file_a_pins(self):
        for path, expected in ACCOUNT_META.items():
            with self.subTest(path=path):
                baseline = json.loads((REPO / expected["baseline"]).read_text())
                self.assertEqual(2, baseline["schemaVersion"])
                self.assertEqual(expected["federalAccount"],
                                 baseline["federalAccount"])
                self.assertIn("api.usaspending.gov/api/v2/federal_accounts/",
                              baseline["source"])
                years = baseline["fiscalYears"]
                self.assertEqual({str(fy) for fy in range(2015, 2027)}, set(years))
                for fy in (2015, 2016):
                    self.assertEqual("unavailable", years[str(fy)]["status"])
                self.assertEqual(6, years["2017"]["firstPeriod"])
                self.assertEqual(12, years["2017"]["asOfPeriod"])
                self.assertEqual(9, years["2026"]["asOfPeriod"])
                observed = [years[str(fy)]["obligationsCents"]
                            for fy in range(2017, 2027)]
                self.assertEqual(expected["pins"], observed)

    def test_stage_one_custom_plan_is_exactly_twenty_serial_partitions(self):
        matrix = plan(
            repo=REPO,
            mode="custom",
            selectors="dod/army-rdte,dod/navy-rdte",
            from_fy=2017,
            to_fy=2026,
            current_period=9,
        )["include"]
        self.assertEqual(20, len(matrix))
        self.assertEqual(set(ACCOUNT_META), {row["account"] for row in matrix})
        for path in ACCOUNT_META:
            rows = [row for row in matrix if row["account"] == path]
            self.assertEqual(list(range(2017, 2027)),
                             [row["fiscalYear"] for row in rows])
            self.assertEqual([12] * 9 + [9], [row["period"] for row in rows])

    def test_public_semantics_keep_file_b_canonical(self):
        handoff = (REPO / "docs" / "phase-3.2d-dod-handoff.md").read_text()
        self.assertIn("File B account obligations are canonical", handoff)
        self.assertIn("not evidence of missing account dollars", handoff)
        self.assertNotIn("completeness percentage", handoff.lower())


if __name__ == "__main__":
    unittest.main()
