"""Phase 3.2d remediation W17 (award-pipeline atomicity, the award-ledger
analogue of W12's data/obligations/refresh_status.json). Covers the
adapters/award_refresh.py build logic and scripts/rollup.py's leaf/rollup
stamping against a small three-leaf temp fixture."""

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

import scripts.rollup as rollup_mod
from adapters.award_refresh import (
    build_refresh_status, check_all_missing, unit_stale_reason,
    write_refresh_status,
)
from adapters.common import load_store, write_dashboard, write_store


def _orgs_cfg():
    """Three leaves: two under one NSF directorate (a multi-leaf aggregate
    case), one under an NIH passthrough directorate (a single-leaf
    aggregate case, mirroring nih/fic over nih/fic/fic in the real
    registry)."""
    return {
        "agencies": [
            {"slug": "nsf", "abbrev": "NSF", "name": "National Science Foundation",
             "adapter": "nsf",
             "directorates": [
                 {"slug": "bfa", "abbrev": "BFA",
                  "name": "Budget, Finance and Award Management",
                  "divisions": [
                      {"slug": "bfa", "abbrev": "BFA", "name": "BFA Division"},
                      {"slug": "dob", "abbrev": "DOB", "name": "Division of Budget"},
                  ]},
             ]},
            {"slug": "nih", "abbrev": "NIH", "name": "National Institutes of Health",
             "adapter": "nih_reporter",
             "directorates": [
                 {"slug": "fic", "abbrev": "FIC", "name": "Fogarty International Center",
                  "divisions": [
                      {"slug": "fic", "abbrev": "FIC", "name": "Fogarty International Center"},
                  ]},
             ]},
        ],
    }


def _award(aid, day="2025-01-15"):
    return {"id": aid, "date": day, "amount": 1000,
            "transType": "Standard/new award", "title": "Example",
            "awardee": "Example University"}


class AwardRefreshStatusBuildTests(unittest.TestCase):
    """adapters/award_refresh.py's build_refresh_status/check_all_missing,
    mirroring scripts/reconcile_obligation_artifacts.py's
    _build_refresh_status test coverage (W12), generalized from account to
    unit."""

    def orgs(self):
        return _orgs_cfg()

    def test_planned_with_marker_is_fresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entries = build_refresh_status(
                root, self.orgs(), ["nsf/bfa/bfa"],
                {"nsf/bfa/bfa": {"completedAt": "2026-09-21T09:00:00Z"}},
                "2026-09-21T09:13:00Z")
            self.assertEqual(entries["nsf/bfa/bfa"], {
                "status": "fresh",
                "lastRefreshAttemptAt": "2026-09-21T09:13:00Z",
                "lastAcceptedAt": "2026-09-21T09:00:00Z",
            })
            # Every configured leaf is present; an unplanned one with no
            # prior record defaults to fresh with no other fields.
            self.assertEqual(entries["nsf/bfa/dob"], {"status": "fresh"})
            self.assertEqual(set(entries), {"nsf/bfa/bfa", "nsf/bfa/dob", "nih/fic/fic"})

    def test_planned_without_marker_falls_back_to_leaf_dashboard_generated_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            leaf_dir = root / "data" / "nsf" / "bfa" / "bfa"
            leaf_dir.mkdir(parents=True)
            (leaf_dir / "dashboard.json").write_text(json.dumps({"generated": "2026-09-01"}))
            entries = build_refresh_status(
                root, self.orgs(), ["nsf/bfa/bfa"], {}, "2026-09-21T09:13:00Z")
            entry = entries["nsf/bfa/bfa"]
            self.assertEqual(entry["status"], "stale")
            self.assertEqual(entry["staleSince"], "2026-09-01")
            self.assertIsNone(entry["lastAcceptedAt"])
            self.assertEqual(entry["lastRefreshAttemptAt"], "2026-09-21T09:13:00Z")
            self.assertEqual(entry["reason"], unit_stale_reason("2026-09-01"))

    def test_planned_without_marker_falls_back_to_today_absent_prior_and_dashboard(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entries = build_refresh_status(
                root, self.orgs(), ["nsf/bfa/bfa"], {}, "2026-09-21T09:13:00Z")
            self.assertEqual(entries["nsf/bfa/bfa"]["staleSince"], "2026-09-21")

    def test_planned_without_marker_falls_back_to_prior_last_accepted_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_refresh_status(root, {
                "nsf/bfa/bfa": {"status": "fresh",
                                "lastAcceptedAt": "2026-09-10T00:00:00Z"},
            }, "2026-09-14T09:13:00Z")
            entries = build_refresh_status(
                root, self.orgs(), ["nsf/bfa/bfa"], {}, "2026-09-21T09:13:00Z")
            entry = entries["nsf/bfa/bfa"]
            self.assertEqual(entry["staleSince"], "2026-09-10")
            self.assertEqual(entry["lastAcceptedAt"], "2026-09-10T00:00:00Z")

    def test_stale_since_preserved_across_repeated_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_refresh_status(root, {
                "nsf/bfa/bfa": {
                    "status": "stale", "staleSince": "2026-09-07",
                    "lastAcceptedAt": "2026-09-01T00:00:00Z",
                    "reason": unit_stale_reason("2026-09-07"),
                },
            }, "2026-09-14T09:13:00Z")
            entries = build_refresh_status(
                root, self.orgs(), ["nsf/bfa/bfa"], {}, "2026-09-21T09:13:00Z")
            entry = entries["nsf/bfa/bfa"]
            # Not reset to "today" (2026-09-21) on a second consecutive
            # failure -- it still names when the unit first went stale.
            self.assertEqual(entry["staleSince"], "2026-09-07")
            self.assertEqual(entry["lastAcceptedAt"], "2026-09-01T00:00:00Z")
            self.assertEqual(entry["reason"], unit_stale_reason("2026-09-07"))

    def test_unplanned_unit_carries_forward_prior_entry_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prior = {"status": "stale", "staleSince": "2026-09-01",
                     "lastAcceptedAt": None, "reason": unit_stale_reason("2026-09-01")}
            write_refresh_status(root, {"nsf/bfa/dob": prior}, "2026-09-14T09:13:00Z")
            # This run's plan only touches nsf/bfa/bfa; nsf/bfa/dob is not
            # planned (a scoped custom run) and must keep its prior entry
            # byte-for-byte.
            entries = build_refresh_status(
                root, self.orgs(), ["nsf/bfa/bfa"],
                {"nsf/bfa/bfa": {"completedAt": "2026-09-21T09:00:00Z"}},
                "2026-09-21T09:13:00Z")
            self.assertEqual(entries["nsf/bfa/dob"], prior)

    def test_stale_to_fresh_recovery_drops_the_stamp(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_refresh_status(root, {
                "nsf/bfa/bfa": {
                    "status": "stale", "staleSince": "2026-09-07",
                    "lastAcceptedAt": "2026-09-01T00:00:00Z",
                    "reason": unit_stale_reason("2026-09-07"),
                },
            }, "2026-09-14T09:13:00Z")
            entries = build_refresh_status(
                root, self.orgs(), ["nsf/bfa/bfa"],
                {"nsf/bfa/bfa": {"completedAt": "2026-09-21T09:00:00Z"}},
                "2026-09-21T09:13:00Z")
            self.assertEqual(entries["nsf/bfa/bfa"], {
                "status": "fresh",
                "lastRefreshAttemptAt": "2026-09-21T09:13:00Z",
                "lastAcceptedAt": "2026-09-21T09:00:00Z",
            })

    def test_all_planned_units_missing_a_marker_refuses(self):
        with self.assertRaisesRegex(
                ValueError, "refusing to publish an all-units-stale"):
            check_all_missing(["nsf/bfa/bfa", "nsf/bfa/dob"], {})

    def test_one_of_several_planned_missing_a_marker_does_not_refuse(self):
        check_all_missing(["nsf/bfa/bfa", "nsf/bfa/dob"], {"nsf/bfa/bfa": {}})

    def test_no_planned_units_does_not_refuse(self):
        check_all_missing([], {})

    def test_unknown_planned_unit_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(
                    ValueError, r"not in config/orgs\.json"):
                build_refresh_status(
                    root, self.orgs(), ["nsf/bfa/nope"], {}, "2026-09-21T09:13:00Z")


class RollupRefreshStatusStampingTests(unittest.TestCase):
    """scripts/rollup.py: leaf stamping, rollup-node aggregation (the
    single-leaf passthrough case and the multi-leaf non-uniform-aggregate
    case), root wording, fresh leaves left unstamped, and child rows
    copying refreshStatus from the child's own dashboard -- against a
    small three-leaf temp fixture. Module globals (REPO_ROOT/DATA) are
    monkeypatched for the duration of each test and restored in tearDown;
    every function under test reads them dynamically from the module
    namespace at call time."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "config").mkdir(parents=True)
        (self.root / "config" / "orgs.json").write_text(json.dumps(_orgs_cfg()))
        for leaf in ("nsf/bfa/bfa", "nsf/bfa/dob", "nih/fic/fic"):
            self._write_leaf(leaf)
        self._orig_data = rollup_mod.DATA
        self._orig_repo_root = rollup_mod.REPO_ROOT
        rollup_mod.REPO_ROOT = self.root
        rollup_mod.DATA = self.root / "data"

    def tearDown(self):
        rollup_mod.DATA = self._orig_data
        rollup_mod.REPO_ROOT = self._orig_repo_root
        self._tmp.cleanup()

    def _write_leaf(self, unit_path, day="2025-01-15"):
        leaf_dir = self.root / "data" / unit_path
        write_store(leaf_dir / "awards.csv",
                    [_award(unit_path.replace("/", ":") + ":1", day)])
        awards = list(load_store(leaf_dir).values())
        write_dashboard(leaf_dir,
                        {"name": unit_path, "abbrev": "", "path": unit_path,
                         "level": "leaf"},
                        "test source", awards, [], date(2025, 6, 1))

    def _dashboard(self, path):
        return json.loads((self.root / "data" / path / "dashboard.json").read_text())

    def _root_dashboard(self):
        return json.loads((self.root / "data" / "dashboard.json").read_text())

    def test_full_rollup_stamps_leaves_and_aggregates(self):
        write_refresh_status(self.root, {
            "nsf/bfa/bfa": {
                "status": "stale", "staleSince": "2026-09-20",
                "lastAcceptedAt": "2026-09-13T00:00:00Z",
                "reason": unit_stale_reason("2026-09-20"),
            },
            "nih/fic/fic": {
                "status": "stale", "staleSince": "2026-09-21",
                "lastAcceptedAt": "2026-09-14T00:00:00Z",
                "reason": unit_stale_reason("2026-09-21"),
            },
        }, "2026-09-21T09:13:00Z")

        rollup_mod.main()

        # Leaf stamp: a stale leaf's own dashboard carries its entry plus `unit`.
        bfa_leaf = self._dashboard("nsf/bfa/bfa")
        self.assertEqual(bfa_leaf["refreshStatus"], {
            "status": "stale", "staleSince": "2026-09-20",
            "lastAcceptedAt": "2026-09-13T00:00:00Z",
            "reason": unit_stale_reason("2026-09-20"),
            "unit": "nsf/bfa/bfa",
        })
        # Fresh leaves are left unstamped entirely.
        dob_leaf = self._dashboard("nsf/bfa/dob")
        self.assertNotIn("refreshStatus", dob_leaf)

        # Passthrough directorate (nih/fic aggregates exactly one leaf):
        # republishes that leaf's own entry, `unit` included, so the
        # directorate's own page (the unit's visible page) gets the
        # single-unit header note.
        fic_dir = self._dashboard("nih/fic")
        self.assertEqual(fic_dir["refreshStatus"], {
            "status": "stale", "staleSince": "2026-09-21",
            "lastAcceptedAt": "2026-09-14T00:00:00Z",
            "reason": unit_stale_reason("2026-09-21"),
            "unit": "nih/fic/fic",
        })
        # The nih agency also aggregates exactly this one leaf -> the same
        # single-leaf passthrough rule applies at the agency level too.
        nih_agency = self._dashboard("nih")
        self.assertEqual(nih_agency["refreshStatus"], fic_dir["refreshStatus"])

        # Multi-leaf directorate (nsf/bfa aggregates 2 leaves, 1 stale):
        # a non-uniform aggregate reason, no `unit` key.
        bfa_dir = self._dashboard("nsf/bfa")
        self.assertEqual(bfa_dir["refreshStatus"], {
            "status": "stale", "staleSince": "2026-09-20",
            "staleUnits": ["nsf/bfa/bfa"],
            "reason": ("1 of 2 unit(s) in this directorate were not "
                       "refreshed in the most recent scheduled pull; see "
                       "the directorate page for which unit."),
        })
        self.assertNotIn("unit", bfa_dir["refreshStatus"])

        # nsf agency aggregates the same 2 leaves (its only directorate).
        nsf_agency = self._dashboard("nsf")
        self.assertEqual(nsf_agency["refreshStatus"], {
            "status": "stale", "staleSince": "2026-09-20",
            "staleUnits": ["nsf/bfa/bfa"],
            "reason": ("1 of 2 unit(s) in this agency were not refreshed "
                       "in the most recent scheduled pull; see the agency "
                       "page for which unit."),
        })

        # Root aggregates all 3 configured leaves, 2 of them stale.
        root_dash = self._root_dashboard()
        self.assertEqual(root_dash["refreshStatus"], {
            "status": "stale", "staleSince": "2026-09-20",
            "staleUnits": ["nsf/bfa/bfa", "nih/fic/fic"],
            "reason": ("2 of 3 unit(s) were not refreshed in the most "
                       "recent scheduled pull; see the agency page for "
                       "which unit."),
        })

        # Child rows carry refreshStatus copied verbatim from the child's
        # own dashboard, at every level.
        bfa_dir_children = {c["path"]: c for c in bfa_dir["children"]}
        self.assertEqual(bfa_dir_children["nsf/bfa/bfa"]["refreshStatus"],
                         bfa_leaf["refreshStatus"])
        self.assertNotIn("refreshStatus", bfa_dir_children["nsf/bfa/dob"])

        nsf_agency_children = {c["path"]: c for c in nsf_agency["children"]}
        self.assertEqual(nsf_agency_children["nsf/bfa"]["refreshStatus"],
                         bfa_dir["refreshStatus"])

        nih_agency_children = {c["path"]: c for c in nih_agency["children"]}
        self.assertEqual(nih_agency_children["nih/fic"]["refreshStatus"],
                         fic_dir["refreshStatus"])

        root_children = {c["path"]: c for c in root_dash["children"]}
        self.assertEqual(root_children["nsf"]["refreshStatus"], nsf_agency["refreshStatus"])
        self.assertEqual(root_children["nih"]["refreshStatus"], nih_agency["refreshStatus"])

    def test_recovery_to_fresh_removes_every_stamp(self):
        write_refresh_status(self.root, {
            "nsf/bfa/bfa": {"status": "stale", "staleSince": "2026-09-20",
                            "lastAcceptedAt": None,
                            "reason": unit_stale_reason("2026-09-20")},
        }, "2026-09-21T09:13:00Z")
        rollup_mod.main()
        self.assertIn("refreshStatus", self._dashboard("nsf/bfa/bfa"))
        self.assertIn("refreshStatus", self._dashboard("nsf/bfa"))
        self.assertIn("refreshStatus", self._dashboard("nsf"))
        self.assertIn("refreshStatus", self._root_dashboard())

        write_refresh_status(self.root, {"nsf/bfa/bfa": {"status": "fresh"}},
                             "2026-09-28T09:13:00Z")
        rollup_mod.main()
        self.assertNotIn("refreshStatus", self._dashboard("nsf/bfa/bfa"))
        self.assertNotIn("refreshStatus", self._dashboard("nsf/bfa"))
        self.assertNotIn("refreshStatus", self._dashboard("nsf"))
        self.assertNotIn("refreshStatus", self._dashboard("nih"))
        self.assertNotIn("refreshStatus", self._root_dashboard())

    def test_restamping_survives_a_metadata_dropping_leaf_rewrite(self):
        # scripts/reaggregate.py rewrites each leaf's dashboard.json via
        # adapters.common.write_dashboard() without carrying forward a
        # previously stamped refreshStatus (it has no staleness knowledge
        # of its own), then finishes by calling rollup.main(). This test
        # exercises the mechanism that guarantees the disclosure survives
        # that round trip: rollup.main()'s leaf-stamping pass restamps
        # every configured leaf unconditionally, straight from the
        # untouched data/refresh_status.json, before building any rollup.
        write_refresh_status(self.root, {
            "nsf/bfa/bfa": {"status": "stale", "staleSince": "2026-09-20",
                            "lastAcceptedAt": None,
                            "reason": unit_stale_reason("2026-09-20")},
        }, "2026-09-21T09:13:00Z")
        rollup_mod.main()
        self.assertIn("refreshStatus", self._dashboard("nsf/bfa/bfa"))

        # Simulate reaggregate.py's per-leaf rewrite: a fresh
        # write_dashboard() call with no refreshStatus in its metadata
        # drops the field, exactly as reaggregate.py's own loop would.
        leaf_dir = self.root / "data" / "nsf" / "bfa" / "bfa"
        awards = list(load_store(leaf_dir).values())
        write_dashboard(leaf_dir,
                        {"name": "nsf/bfa/bfa", "abbrev": "", "path": "nsf/bfa/bfa",
                         "level": "leaf"},
                        "test source", awards, [], date(2025, 6, 2))
        self.assertNotIn("refreshStatus", self._dashboard("nsf/bfa/bfa"))

        rollup_mod.main()
        self.assertIn("refreshStatus", self._dashboard("nsf/bfa/bfa"))


if __name__ == "__main__":
    unittest.main()
