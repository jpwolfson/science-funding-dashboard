import json
import tempfile
import unittest
from pathlib import Path

from adapters.award_refresh import aggregate_refresh_status, unit_stale_reason
from scripts.validate_award_invariants import validate


def _write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))


def _orgs_cfg():
    """Two leaves under one directorate, so both the leaf-level and the
    rollup-aggregate refresh-status checks (Phase 3.2d remediation W17)
    are exercised: nsf/x/a (stale) and nsf/x/b (fresh)."""
    return {
        "agencies": [
            {"slug": "nsf", "directorates": [
                {"slug": "x", "divisions": [{"slug": "a"}, {"slug": "b"}]},
            ]},
        ],
    }


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


class AwardRefreshStatusInvariantTests(unittest.TestCase):
    """Phase 3.2d remediation W17: fail-closed checks on
    data/refresh_status.json and its consistency with every committed
    dashboard's own refreshStatus field."""

    def fixture(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        _write(root / "config" / "orgs.json", _orgs_cfg())

        entry = {"status": "stale", "staleSince": "2026-09-01",
                 "lastAcceptedAt": None, "reason": unit_stale_reason("2026-09-01")}
        _write(root / "data" / "refresh_status.json", {
            "schemaVersion": 1, "generatedAt": "2026-09-21T09:13:00Z",
            "units": {"nsf/x/a": entry},
        })

        def leaf(slug, refresh=None):
            page = {
                "node": {"level": "division", "path": f"nsf/x/{slug}"},
                "totalAwards": 0, "fiscalYears": [], "monthly": [], "fyCumulative": [],
            }
            if refresh:
                page["refreshStatus"] = refresh
            _write(root / "data" / "nsf" / "x" / slug / "dashboard.json", page)
            return page

        leaf_a = leaf("a", refresh={**entry, "unit": "nsf/x/a"})
        leaf("b")

        dir_refresh = aggregate_refresh_status(
            ["nsf/x/a", "nsf/x/b"], {"nsf/x/a": entry}, "directorate")
        dir_page = {
            "node": {"level": "directorate", "path": "nsf/x"},
            "totalAwards": 0, "fiscalYears": [], "monthly": [], "fyCumulative": [],
            "children": [
                {"path": "nsf/x/a", "totalAwards": 0,
                 "refreshStatus": leaf_a["refreshStatus"]},
                {"path": "nsf/x/b", "totalAwards": 0},
            ],
            "refreshStatus": dir_refresh,
        }
        _write(root / "data" / "nsf" / "x" / "dashboard.json", dir_page)

        agency_refresh = aggregate_refresh_status(
            ["nsf/x/a", "nsf/x/b"], {"nsf/x/a": entry}, "agency")
        agency_page = {
            "node": {"level": "agency", "path": "nsf"},
            "totalAwards": 0, "fiscalYears": [], "monthly": [], "fyCumulative": [],
            "children": [
                {"path": "nsf/x", "totalAwards": 0,
                 "refreshStatus": dir_page["refreshStatus"]},
            ],
            "refreshStatus": agency_refresh,
        }
        _write(root / "data" / "nsf" / "dashboard.json", agency_page)

        root_refresh = aggregate_refresh_status(
            ["nsf/x/a", "nsf/x/b"], {"nsf/x/a": entry}, "root")
        root_page = {
            "node": {"level": "root", "path": ""},
            "totalAwards": 0, "fiscalYears": [], "monthly": [], "fyCumulative": [],
            "children": [
                {"path": "nsf", "totalAwards": 0,
                 "refreshStatus": agency_page["refreshStatus"]},
            ],
            "refreshStatus": root_refresh,
        }
        _write(root / "data" / "dashboard.json", root_page)
        return temp, root

    def test_consistent_refresh_status_tree_passes(self):
        temp, root = self.fixture()
        try:
            errors, checked = validate(root)
            self.assertEqual([], errors)
            self.assertEqual(5, len(checked))
        finally:
            temp.cleanup()

    def test_bare_stale_entry_without_reason_fails_closed(self):
        temp, root = self.fixture()
        try:
            status_path = root / "data" / "refresh_status.json"
            status = json.loads(status_path.read_text())
            status["units"]["nsf/x/a"] = {"status": "stale"}  # no staleSince/reason
            _write(status_path, status)
            errors, _checked = validate(root)
            self.assertTrue(any(
                "stale entry has invalid staleSince" in e for e in errors), errors)
            self.assertTrue(any(
                "stale entry has no reason" in e for e in errors), errors)
        finally:
            temp.cleanup()

    def test_unknown_unit_key_fails_closed(self):
        temp, root = self.fixture()
        try:
            status_path = root / "data" / "refresh_status.json"
            status = json.loads(status_path.read_text())
            status["units"]["nsf/x/not-a-leaf"] = {"status": "fresh"}
            _write(status_path, status)
            errors, _checked = validate(root)
            self.assertTrue(any("not a configured leaf" in e for e in errors), errors)
        finally:
            temp.cleanup()

    def test_leaf_dashboard_mismatch_fails_closed(self):
        temp, root = self.fixture()
        try:
            leaf_path = root / "data" / "nsf" / "x" / "a" / "dashboard.json"
            page = json.loads(leaf_path.read_text())
            page["refreshStatus"]["staleSince"] = "2099-01-01"  # diverges from the status file
            _write(leaf_path, page)
            errors, _checked = validate(root)
            self.assertTrue(any(
                "does not match data/refresh_status.json entry" in e for e in errors), errors)
        finally:
            temp.cleanup()

    def test_rollup_missing_refresh_status_despite_stale_descendant_fails_closed(self):
        temp, root = self.fixture()
        try:
            dir_path = root / "data" / "nsf" / "x" / "dashboard.json"
            page = json.loads(dir_path.read_text())
            del page["refreshStatus"]
            _write(dir_path, page)
            errors, _checked = validate(root)
            self.assertTrue(any(
                "descendant leaf unit(s)" in e and "carries no refreshStatus" in e
                for e in errors), errors)
        finally:
            temp.cleanup()

    def test_child_row_mismatch_fails_closed(self):
        temp, root = self.fixture()
        try:
            agency_path = root / "data" / "nsf" / "dashboard.json"
            page = json.loads(agency_path.read_text())
            page["children"][0]["refreshStatus"]["staleUnits"] = ["nsf/x/a", "extra"]
            _write(agency_path, page)
            errors, _checked = validate(root)
            self.assertTrue(any(
                "child row" in e and "does not match its own dashboard" in e
                for e in errors), errors)
        finally:
            temp.cleanup()


if __name__ == "__main__":
    unittest.main()
