import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_award_invariants import validate


def _write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))


class AwardInvariantValidationTests(unittest.TestCase):
    def fixture(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        leaf = {
            "node": {"level": "leaf", "path": "nsf/x/x"},
            "totalAwards": 3,
            "fiscalYears": [{"fy": 2025, "awards": 3, "dollars": 300}],
            "monthly": [
                {"month": "2024-10", "awards": 2, "dollars": 200},
                {"month": "2024-11", "awards": 1, "dollars": 100},
            ],
            "fyCumulative": [
                {"fy": 2025, "points": [
                    {"d": 1, "awards": 2, "dollars": 200},
                    {"d": 2, "awards": 3, "dollars": 300},
                ]},
            ],
        }
        _write(root / "data" / "nsf" / "x" / "x" / "dashboard.json", leaf)
        root_page = {
            "node": {"level": "root", "path": ""},
            "totalAwards": 3,
            "fiscalYears": [{"fy": 2025, "awards": 3, "dollars": 300}],
            "monthly": [{"month": "2024-10", "awards": 3, "dollars": 300}],
            "fyCumulative": [],
            "children": [{"slug": "nsf", "totalAwards": 3}],
        }
        _write(root / "data" / "dashboard.json", root_page)
        return temp, root, leaf

    def test_consistent_dashboards_pass(self):
        temp, root, _leaf = self.fixture()
        try:
            errors, checked = validate(root)
            self.assertEqual([], errors)
            self.assertEqual(2, len(checked))
        finally:
            temp.cleanup()

    def test_total_awards_mismatching_fiscal_years_fails(self):
        temp, root, leaf = self.fixture()
        try:
            leaf["totalAwards"] = 4
            _write(root / "data" / "nsf" / "x" / "x" / "dashboard.json", leaf)
            errors, _checked = validate(root)
            self.assertTrue(any("totalAwards" in e and "fiscalYears" in e for e in errors))
        finally:
            temp.cleanup()

    def test_fycumulative_endpoint_mismatch_fails(self):
        """Regression fixture for the 2026-08-12 nih/od/od bug: a
        future-dated award left the cumulative endpoint one award short of
        its fiscal-year row."""
        temp, root, leaf = self.fixture()
        try:
            leaf["fyCumulative"][0]["points"][-1]["awards"] = 2
            _write(root / "data" / "nsf" / "x" / "x" / "dashboard.json", leaf)
            errors, _checked = validate(root)
            self.assertTrue(any("fyCumulative endpoint" in e for e in errors))
        finally:
            temp.cleanup()

    def test_root_children_sum_mismatch_fails(self):
        temp, root, _leaf = self.fixture()
        try:
            root_path = root / "data" / "dashboard.json"
            root_page = json.loads(root_path.read_text())
            root_page["children"][0]["totalAwards"] = 2
            _write(root_path, root_page)
            errors, _checked = validate(root)
            self.assertTrue(any("sum(children.totalAwards)" in e for e in errors))
        finally:
            temp.cleanup()

    def test_obligation_and_sentinel_dashboards_are_skipped(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        try:
            _write(root / "data" / "obligations" / "dashboard.json",
                   {"kind": "obligations", "totalNetObligationsCents": 5})
            _write(root / "data" / "sentinel" / "dashboard.json",
                   {"kind": "sentinel", "episodes": []})
            errors, checked = validate(root)
            self.assertEqual([], errors)
            self.assertEqual([], checked)
        finally:
            temp.cleanup()


if __name__ == "__main__":
    unittest.main()
