import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from adapters.obligation_common import (
    event_fingerprint, normalize_event, partition_diff, write_store,
)
from scripts.rollup_obligations import build as build_obligations
from scripts.validate_obligations import (
    _is_pending_neutral_child,
    _is_pending_partial_pin_transition,
    validate,
)


class ObligationValidationTests(unittest.TestCase):
    class FakeRecovery:
        def __init__(self, pin):
            self.pin = pin

        def baseline_pin(self, account_path, fiscal_year):
            if (account_path, fiscal_year) == ("dhs/cwmd-rd", 2026):
                return self.pin
            return None

    def fixture(self, expected):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        (root / "config").mkdir()
        (root / "reference").mkdir()
        (root / "config" / "obligation_accounts.json").write_text(json.dumps({
            "schemaVersion": 2,
            "refreshDefaults": {"freshnessMaxDays": 10},
            "accounts": [{"path": "doe/sc", "federalAccount": "089-0222",
                          "baseline": "reference/doe_sc_obligation_baseline.json",
                          "programActivities": [{"slug": "bes", "code": "0001",
                                                 "name": "BES"}]}]}))
        (root / "reference" / "doe_sc_obligation_baseline.json").write_text(json.dumps({
            "schemaVersion": 2,
            "federalAccount": "089-0222",
            "fiscalYears": {"2024": {"status": "complete", "obligationsCents": expected}}}))
        row = normalize_event({"id": "one", "source": "file_b_residual",
            "submissionPeriod": "FY2024P12", "federalAccount": "089-0222",
            "programActivityCode": "0001", "programActivityName": "BES",
            "amountCents": 100, "awardId": "", "linked": False})
        write_store(
            root / "data" / "obligations" / "doe" / "sc" / "events",
            [row], {"federalAccount": "089-0222"}, partition_metadata={2024: {
                "schemaVersion": 2, "collectionStatus": "legacy-migrated",
                "migratedAt": "2024-10-01T00:00:00+00:00",
                "accountPath": "doe/sc", "federalAccount": "089-0222",
                "fiscalYear": 2024, "asOfPeriod": 12, "downloads": [],
                "normalized": {"recordCount": 1,
                               "eventFingerprint": event_fingerprint([row]),
                               "netObligationsCents": 100},
                "replacement": {"previousEventFingerprint": None,
                                "previousProvenanceSha256": None},
                "diff": {**partition_diff([], [row]), "kind": "schema-v2-migration"},
                "baselinePin": {"status": "complete", "obligationsCents": expected},
                "migration": {"note": "test legacy migration"},
            }},
        )
        return temp, root

    def set_dual_pin(self, root, file_a=101, file_b=100, variance=1,
                     reason="Official source warning A19"):
        pin = {
            "status": "complete",
            "obligationsCents": file_a,
            "fileBObligationsCents": file_b,
            "fileAFileBVarianceCents": variance,
            "fileAFileBVarianceReason": reason,
        }
        baseline = root / "reference" / "doe_sc_obligation_baseline.json"
        value = json.loads(baseline.read_text())
        value["fiscalYears"]["2024"] = pin
        baseline.write_text(json.dumps(value))
        provenance = (root / "data" / "obligations" / "doe" / "sc" /
                      "events" / "FY2024.provenance.json")
        value = json.loads(provenance.read_text())
        value["baselinePin"] = pin
        provenance.write_text(json.dumps(value))

    def test_exact_gtas_cents_pass(self):
        temp, root = self.fixture(100)
        try:
            self.assertEqual([], validate(root, require_data=False))
        finally:
            temp.cleanup()

    def test_exact_pending_partial_pin_transition_passes(self):
        account = {
            "path": "dhs/cwmd-rd", "federalAccount": "070-0860",
        }
        old_pin = {
            "status": "partial", "asOfPeriod": 9,
            "obligationsCents": 100,
        }
        new_pin = {
            "status": "partial", "asOfPeriod": 10,
            "obligationsCents": 90, "fileBObligationsCents": 110,
            "fileAFileBVarianceCents": -20,
            "fileAFileBVarianceReason": "Exact official source variance",
        }
        row = normalize_event({
            "id": "dhs-p09", "source": "file_b_residual",
            "submissionPeriod": "FY2026P09", "federalAccount": "070-0860",
            "programActivityCode": "0001", "programActivityName": "CWMD",
            "amountCents": 100, "awardId": "", "linked": False,
        })
        provenance = {
            "schemaVersion": 2, "collectionStatus": "accepted",
            "accountPath": "dhs/cwmd-rd", "federalAccount": "070-0860",
            "fiscalYear": 2026, "asOfPeriod": 9, "baselinePin": old_pin,
        }
        recovery = self.FakeRecovery(new_pin)
        evidence = {("dhs/cwmd-rd", 2026, 10)}
        self.assertTrue(_is_pending_partial_pin_transition(
            account, 2026, new_pin, provenance, [row], recovery, evidence
        ))
        self.assertFalse(_is_pending_partial_pin_transition(
            account, 2026, {**new_pin, "asOfPeriod": 11}, provenance,
            [row], recovery, evidence
        ))
        self.assertFalse(_is_pending_partial_pin_transition(
            account, 2026, new_pin, provenance, [row], recovery, set()
        ))

    def test_pending_neutral_child_is_exact_and_evidence_scoped(self):
        account = {"path": "doe/sc"}
        pa = {
            "slug": "source-label-unavailable-63ypt7l1yuj",
            "code": "63YPT7L1YUJ", "park": "63YPT7L1YUJ",
            "name": "Source label unavailable (PARK 63YPT7L1YUJ)",
        }
        stats = {"currentFY": 2026, "asOfPeriod": "FY2026P09"}
        evidence = {("doe/sc", 2026, 10)}
        self.assertTrue(_is_pending_neutral_child(
            account, pa, [], stats, evidence
        ))
        self.assertFalse(_is_pending_neutral_child(
            account, {**pa, "slug": "invented"}, [], stats, evidence
        ))
        self.assertFalse(_is_pending_neutral_child(
            account, pa, [], stats, set()
        ))

    def test_not_reported_p12_is_a_validation_error_not_a_crash(self):
        # scripts/validate_obligations.py must report the P12/complete-year
        # hard error as an ordinary validation error (fail closed) without
        # raising out of validate() and aborting every other account.
        temp, root = self.fixture(100)
        try:
            provenance = (root / "data" / "obligations" / "doe" / "sc" /
                         "events" / "FY2024.provenance.json")
            value = json.loads(provenance.read_text())
            value["collectionStatus"] = "accepted"
            value["acceptedAt"] = "2026-08-11T12:00:00+00:00"
            value["downloads"] = [
                {"submissionType": "object_class_program_activity",
                 "requestScope": {"filters": {"fy": 2024, "period": 6,
                                              "submission_types":
                                                  ["object_class_program_activity"],
                                              "federal_account": "5787"},
                                  "columns": ["submission_period"]},
                 "acceptedRequestScope": {"filters": {"fy": 2024, "period": 6,
                                                      "federal_account": "5787"},
                                          "download_types":
                                              ["object_class_program_activity"]},
                 "status": "finished", "statusRowCount": 100,
                 "parsedRowCount": 100, "memberRowCounts": {"a.csv": 100},
                 "archiveSha256": "0" * 64, "rawArtifactFile": "a.zip"},
                {"submissionType": "object_class_program_activity",
                 "requestScope": {"filters": {"fy": 2024, "period": 12,
                                              "submission_types":
                                                  ["object_class_program_activity"],
                                              "federal_account": "5787"},
                                  "columns": ["submission_period"]},
                 "acceptedRequestScope": {"filters": {"fy": 2024, "period": 12,
                                                      "federal_account": "5787"},
                                          "download_types":
                                              ["object_class_program_activity"]},
                 "status": "finished", "statusRowCount": 40,
                 "parsedRowCount": 40, "memberRowCounts": {"a.csv": 40},
                 "archiveSha256": "0" * 64, "rawArtifactFile": "b.zip"},
                {"submissionType": "award_financial",
                 "requestScope": {"filters": {"fy": 2024, "period": 12,
                                              "submission_types":
                                                  ["award_financial"],
                                              "federal_account": "5787"},
                                  "columns": ["submission_period"]},
                 "acceptedRequestScope": {"filters": {"fy": 2024, "period": 12,
                                                      "federal_account": "5787"},
                                          "download_types": ["award_financial"]},
                 "status": "finished", "statusRowCount": 0,
                 "parsedRowCount": 0, "memberRowCounts": {},
                 "archiveSha256": "0" * 64, "rawArtifactFile": "c.zip"},
            ]
            provenance.write_text(json.dumps(value))
            errors = validate(root, require_data=False)
            self.assertTrue(
                any("FY2024P12 is notReported" in error for error in errors),
                errors,
            )
        finally:
            temp.cleanup()

    def test_large_drop_requires_a_baseline_period_note_above_the_dollar_floor(self):
        temp = tempfile.TemporaryDirectory()
        try:
            root = Path(temp.name)
            (root / "config").mkdir()
            (root / "reference").mkdir()
            (root / "config" / "obligation_accounts.json").write_text(json.dumps({
                "schemaVersion": 2,
                "accounts": [{"path": "dhs/cisa-rd", "federalAccount": "070-0805",
                              "baseline": "reference/dhs_cisa_rd_obligation_baseline.json",
                              "programActivities": [{"slug": "rd", "code": "0001",
                                                     "name": "R&D"}]}]}))
            baseline_path = root / "reference" / "dhs_cisa_rd_obligation_baseline.json"
            baseline_path.write_text(json.dumps({
                "schemaVersion": 2, "federalAccount": "070-0805",
                "fiscalYears": {"2023": {"status": "complete",
                                         "obligationsCents": 100_000_000}}}))
            rows = [
                # Cumulative through P03: $12.9M. Through P04: $1M (a real
                # >50% drop, above the $1M floor).
                normalize_event({
                    "id": "p03", "source": "file_b_residual",
                    "submissionPeriod": "FY2023P03", "federalAccount": "070-0805",
                    "programActivityCode": "0001", "programActivityName": "R&D",
                    "amountCents": 1_290_038_168, "awardId": "", "linked": False,
                }),
                normalize_event({
                    "id": "p04", "source": "file_b_residual",
                    "submissionPeriod": "FY2023P04", "federalAccount": "070-0805",
                    "programActivityCode": "0001", "programActivityName": "R&D",
                    "amountCents": -1_190_038_168, "awardId": "", "linked": False,
                }),
            ]
            store = root / "data" / "obligations" / "dhs" / "cisa-rd" / "events"
            write_store(store, rows, {"federalAccount": "070-0805"})
            errors = validate(root, require_data=False)
            self.assertTrue(
                any("cumulative File B fell" in e and "periodNotes" in e
                    for e in errors), errors,
            )
            # Add the curated note and confirm the same drop no longer fails.
            value = json.loads(baseline_path.read_text())
            value["fiscalYears"]["2023"]["periodNotes"] = [
                {"period": 4, "note": "Provisional note pending re-pull."}]
            baseline_path.write_text(json.dumps(value))
            errors = validate(root, require_data=False)
            self.assertFalse(
                any("cumulative File B fell" in e for e in errors), errors)
        finally:
            temp.cleanup()

    def test_large_drop_below_the_dollar_floor_is_not_flagged(self):
        temp = tempfile.TemporaryDirectory()
        try:
            root = Path(temp.name)
            (root / "config").mkdir()
            (root / "reference").mkdir()
            (root / "config" / "obligation_accounts.json").write_text(json.dumps({
                "schemaVersion": 2,
                "accounts": [{"path": "usda/nifa-integrated-activities",
                              "federalAccount": "012-1502",
                              "baseline": "reference/nifa_obligation_baseline.json",
                              "programActivities": [{"slug": "ia", "code": "0001",
                                                     "name": "Integrated"}]}]}))
            (root / "reference" / "nifa_obligation_baseline.json").write_text(json.dumps({
                "schemaVersion": 2, "federalAccount": "012-1502",
                "fiscalYears": {"2022": {"status": "complete", "obligationsCents": -1000}}}))
            rows = [
                normalize_event({
                    "id": "p02", "source": "file_b_residual",
                    "submissionPeriod": "FY2022P02", "federalAccount": "012-1502",
                    "programActivityCode": "0001", "programActivityName": "Integrated",
                    "amountCents": 24258, "awardId": "", "linked": False,
                }),
                normalize_event({
                    "id": "p03", "source": "file_b_residual",
                    "submissionPeriod": "FY2022P03", "federalAccount": "012-1502",
                    "programActivityCode": "0001", "programActivityName": "Integrated",
                    "amountCents": -25258, "awardId": "", "linked": False,
                }),
            ]
            store = (root / "data" / "obligations" / "usda" /
                    "nifa-integrated-activities" / "events")
            write_store(store, rows, {"federalAccount": "012-1502"})
            errors = validate(root, require_data=False)
            self.assertFalse(
                any("cumulative File B fell" in e for e in errors), errors)
        finally:
            temp.cleanup()

    def test_one_cent_difference_fails(self):
        temp, root = self.fixture(101)
        try:
            self.assertTrue(any("!= GTAS" in e for e in validate(root, require_data=False)))
        finally:
            temp.cleanup()

    def test_dual_exact_file_a_file_b_pins_pass(self):
        temp, root = self.fixture(100)
        try:
            self.set_dual_pin(root)
            self.assertEqual([], validate(root, require_data=False))
        finally:
            temp.cleanup()

    def test_dual_pin_variance_arithmetic_fails_closed(self):
        temp, root = self.fixture(100)
        try:
            self.set_dual_pin(root, variance=2)
            self.assertTrue(any(
                "File A minus File B" in error
                for error in validate(root, require_data=False)
            ))
        finally:
            temp.cleanup()

    def test_dual_pin_still_requires_exact_file_b_cents(self):
        temp, root = self.fixture(100)
        try:
            self.set_dual_pin(root, file_b=99, variance=2)
            self.assertTrue(any(
                "!= pinned File B 99 cents" in error
                for error in validate(root, require_data=False)
            ))
        finally:
            temp.cleanup()

    def test_source_unavailable_year_with_events_fails_without_pin_lookup(self):
        temp, root = self.fixture(100)
        try:
            baseline = root / "reference" / "doe_sc_obligation_baseline.json"
            value = json.loads(baseline.read_text())
            value["fiscalYears"]["2024"] = {
                "status": "unavailable", "reason": "No official source",
            }
            baseline.write_text(json.dumps(value))
            self.assertTrue(any(
                "events exist for a source-unavailable year" in error
                for error in validate(root, require_data=False)
            ))
        finally:
            temp.cleanup()

    def test_foreign_award_url_fails(self):
        temp, root = self.fixture(100)
        try:
            store = root / "data" / "obligations" / "doe" / "sc" / "events"
            rows = [normalize_event({"id": "one", "source": "file_b_residual",
                "submissionPeriod": "FY2024P12", "federalAccount": "089-0222",
                "programActivityCode": "0001", "programActivityName": "BES",
                "amountCents": 100, "awardId": "", "linked": False}),
                normalize_event({"id": "linked", "source": "file_c",
                "submissionPeriod": "FY2024P12", "federalAccount": "089-0222",
                "programActivityCode": "0001", "programActivityName": "BES",
                "amountCents": 0, "awardId": "A1", "linked": True,
                "awardUrl": "https://example.com/award/A1"})]
            write_store(store, rows, {"federalAccount": "089-0222"})
            self.assertTrue(any("invalid public USAspending award URL" in e
                                for e in validate(root, require_data=False)))
        finally:
            temp.cleanup()

    def test_manifest_fingerprint_mismatch_fails(self):
        temp, root = self.fixture(100)
        try:
            manifest = root / "data" / "obligations" / "doe" / "sc" / "events" / "manifest.json"
            value = json.loads(manifest.read_text())
            value["eventFingerprint"] = "bad"
            manifest.write_text(json.dumps(value))
            self.assertTrue(any("manifest fingerprint mismatch" in e
                                for e in validate(root, require_data=False)))
        finally:
            temp.cleanup()

    def test_missing_required_fiscal_year_fails(self):
        temp, root = self.fixture(100)
        try:
            baseline = root / "reference" / "doe_sc_obligation_baseline.json"
            value = json.loads(baseline.read_text())
            value["fiscalYears"]["2023"] = {
                "status": "complete", "obligationsCents": 0,
            }
            baseline.write_text(json.dumps(value))
            self.assertTrue(any("FY2023: required complete snapshot is missing" in e
                                for e in validate(root, require_data=False)))
        finally:
            temp.cleanup()

    def test_reused_code_residuals_are_validated_per_named_identity(self):
        temp, root = self.fixture(300)
        try:
            registry = root / "config" / "obligation_accounts.json"
            value = json.loads(registry.read_text())
            value["accounts"][0]["programActivities"] = [
                {"slug": "first", "code": "0001", "name": "First"},
                {"slug": "second", "code": "0001", "name": "Second"},
            ]
            registry.write_text(json.dumps(value))
            rows = []
            for name, prefix, file_c, residual in (
                    ("First", "first", 40, 60),
                    ("Second", "second", 80, 120)):
                rows.extend([
                    normalize_event({
                        "id": f"{prefix}-c", "source": "file_c",
                        "submissionPeriod": "FY2024P12",
                        "federalAccount": "089-0222",
                        "programActivityCode": "0001",
                        "programActivityName": name,
                        "amountCents": file_c, "awardId": "", "linked": False,
                    }),
                    normalize_event({
                        "id": f"{prefix}-r", "source": "file_b_residual",
                        "submissionPeriod": "FY2024P12",
                        "federalAccount": "089-0222",
                        "programActivityCode": "0001",
                        "programActivityName": name,
                        "amountCents": residual, "awardId": "", "linked": False,
                    }),
                ])
            write_store(root / "data" / "obligations" / "doe" / "sc" / "events",
                        rows, {"federalAccount": "089-0222"})
            errors = validate(root, require_data=False)
            self.assertFalse(any("File B residual rows" in error for error in errors),
                             errors)
        finally:
            temp.cleanup()

    def test_source_variance_ledger_exactly_covers_all_dual_pins(self):
        repo = Path(__file__).resolve().parent.parent
        registry = json.loads(
            (repo / "config" / "obligation_accounts.json").read_text()
        )
        ledger = json.loads(
            (repo / "reference" /
             "obligation_source_variance_ledger.json").read_text()
        )
        self.assertEqual(1, ledger["schemaVersion"])
        entries = {
            (row["accountPath"], row["fiscalYear"]): row
            for row in ledger["entries"]
        }
        self.assertEqual(len(ledger["entries"]), len(entries))

        expected = {}
        for account in registry["accounts"]:
            baseline = json.loads((repo / account["baseline"]).read_text())
            for fiscal_year, pin in baseline["fiscalYears"].items():
                if "fileBObligationsCents" in pin:
                    expected[(account["path"], int(fiscal_year))] = (
                        account, pin
                    )
        self.assertEqual(set(expected), set(entries))

        for key, (account, pin) in expected.items():
            with self.subTest(account=key[0], fiscal_year=key[1]):
                row = entries[key]
                variance = (
                    pin["obligationsCents"] -
                    pin["fileBObligationsCents"]
                )
                ppm = (
                    abs(variance) * 1_000_000 +
                    abs(pin["obligationsCents"]) // 2
                ) // abs(pin["obligationsCents"])
                self.assertEqual(account["federalAccount"],
                                 row["federalAccount"])
                self.assertEqual(pin["obligationsCents"],
                                 row["fileAObligationsCents"])
                self.assertEqual(pin["fileBObligationsCents"],
                                 row["fileBObligationsCents"])
                self.assertEqual(pin["fileAFileBVarianceCents"],
                                 row["fileAFileBVarianceCents"])
                self.assertEqual(variance, row["fileAFileBVarianceCents"])
                self.assertEqual(abs(variance),
                                 row["absoluteVarianceCents"])
                self.assertEqual(ppm, row["absoluteVariancePpmOfFileA"])
                self.assertEqual(pin["fileAFileBVarianceReason"],
                                 row["reason"])
                self.assertEqual(account["baseline"], row["baseline"])
                self.assertEqual("approved",
                                 row["ownerApproval"]["status"])
                evidence = row["evidence"]
                self.assertGreater(evidence["workflowRunId"], 0)
                self.assertGreater(evidence["workflowJobId"], 0)
                self.assertGreater(evidence["rawArtifactId"], 0)
                self.assertRegex(
                    evidence["rawArtifactSha256"], r"^[0-9a-f]{64}$"
                )


class NotReportedLatestPeriodPinTests(unittest.TestCase):
    """W10 (Phase 3.2d remediation): a partial fiscal year whose latest File
    B snapshot collapses to `notReported` must not error just because the
    pin correctly stays behind it (docs/obligation-ledger.md
    "Snapshot acceptance and not-reported periods" / "Baseline-pin
    advancement"). Reproduces the run-35253300879 failure signature on
    doe/sc and doe/fossil-energy FY2026 P10 on a minimal fixture."""

    FEDERAL_ACCOUNT = "089-0222"
    PATH = "doe/sc"

    def _download(self, fy, period, kind, row_count):
        return {
            "submissionType": kind,
            "requestScope": {
                "filters": {"fy": fy, "period": period,
                           "submission_types": [kind],
                           "federal_account": self.FEDERAL_ACCOUNT},
                "columns": ["submission_period"],
            },
            "acceptedRequestScope": {
                "filters": {"fy": fy, "period": period,
                           "federal_account": self.FEDERAL_ACCOUNT},
                "download_types": [kind],
            },
            "status": "finished", "statusRowCount": row_count,
            "parsedRowCount": row_count, "memberRowCounts": {"a.csv": row_count},
            "archiveSha256": "0" * 64, "rawArtifactFile": f"p{period:02}-{kind}.zip",
        }

    def _fixture(self, file_b_rows, pin_as_of_period, pin_cents,
                include_p10_residual):
        """Build a doe/sc FY2026 partial fixture.

        ``file_b_rows`` maps period -> File B statusRowCount (periods 8-10).
        Period 10 always gets a File C event; it also gets a residual only
        when ``include_p10_residual``, matching whether P10 is meant to
        reconcile as an ordinary reported period.
        """
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        (root / "config").mkdir()
        (root / "reference").mkdir()
        (root / "config" / "obligation_accounts.json").write_text(json.dumps({
            "schemaVersion": 2,
            "refreshDefaults": {"freshnessMaxDays": 10},
            "accounts": [{
                "path": self.PATH, "federalAccount": self.FEDERAL_ACCOUNT,
                "baseline": "reference/doe_sc_obligation_baseline.json",
                "availability": {"regularFirstPeriod": 8},
                "programActivities": [{"slug": "bes", "code": "0001", "name": "BES"}],
            }],
        }))
        (root / "reference" / "doe_sc_obligation_baseline.json").write_text(json.dumps({
            "schemaVersion": 2, "federalAccount": self.FEDERAL_ACCOUNT,
            "fiscalYears": {"2026": {
                "status": "partial", "asOfPeriod": pin_as_of_period,
                "obligationsCents": pin_cents,
            }},
        }))
        rows = [
            normalize_event({
                "id": "p08-c", "source": "file_c", "submissionPeriod": "FY2026P08",
                "federalAccount": self.FEDERAL_ACCOUNT, "programActivityCode": "0001",
                "programActivityName": "BES", "amountCents": 500,
                "awardId": "", "linked": False,
            }),
            normalize_event({
                "id": "p08-r", "source": "file_b_residual", "submissionPeriod": "FY2026P08",
                "federalAccount": self.FEDERAL_ACCOUNT, "programActivityCode": "0001",
                "programActivityName": "BES", "amountCents": 300,
                "awardId": "", "linked": False,
            }),
            normalize_event({
                "id": "p09-c", "source": "file_c", "submissionPeriod": "FY2026P09",
                "federalAccount": self.FEDERAL_ACCOUNT, "programActivityCode": "0001",
                "programActivityName": "BES", "amountCents": 600,
                "awardId": "", "linked": False,
            }),
            normalize_event({
                "id": "p09-r", "source": "file_b_residual", "submissionPeriod": "FY2026P09",
                "federalAccount": self.FEDERAL_ACCOUNT, "programActivityCode": "0001",
                "programActivityName": "BES", "amountCents": 400,
                "awardId": "", "linked": False,
            }),
            normalize_event({
                "id": "p10-c", "source": "file_c", "submissionPeriod": "FY2026P10",
                "federalAccount": self.FEDERAL_ACCOUNT, "programActivityCode": "0001",
                "programActivityName": "BES", "amountCents": 200,
                "awardId": "", "linked": False,
            }),
        ]
        if include_p10_residual:
            rows.append(normalize_event({
                "id": "p10-r", "source": "file_b_residual", "submissionPeriod": "FY2026P10",
                "federalAccount": self.FEDERAL_ACCOUNT, "programActivityCode": "0001",
                "programActivityName": "BES", "amountCents": 150,
                "awardId": "", "linked": False,
            }))
        downloads = [
            self._download(2026, period, "object_class_program_activity", count)
            for period, count in sorted(file_b_rows.items())
        ] + [self._download(2026, 10, "award_financial", 1)]
        provenance = {
            "schemaVersion": 2, "collectionStatus": "accepted",
            "acceptedAt": "2026-09-18T00:00:00+00:00",
            "accountPath": self.PATH, "federalAccount": self.FEDERAL_ACCOUNT,
            "fiscalYear": 2026, "asOfPeriod": 10, "downloads": downloads,
            "normalized": {
                "recordCount": len(rows),
                "eventFingerprint": event_fingerprint(rows),
                "netObligationsCents": sum(e["amountCents"] for e in
                                          (normalize_event(r) for r in rows)),
            },
            "replacement": {"previousEventFingerprint": event_fingerprint([]),
                            "previousProvenanceSha256": None},
            "diff": partition_diff([], rows),
            "baselinePin": {"status": "partial", "asOfPeriod": pin_as_of_period,
                           "obligationsCents": pin_cents},
        }
        write_store(
            root / "data" / "obligations" / "doe" / "sc" / "events", rows,
            {"federalAccount": self.FEDERAL_ACCOUNT},
            partition_metadata={2026: provenance},
        )
        return temp, root

    def test_pin_at_last_reported_period_with_notreported_tail_passes(self):
        # P08/P09 reported (20/21 rows), P10 collapses to 5 rows (< half of
        # 21) with no later period to recover -- provisional notReported,
        # exactly the run-35253300879 shape. The pin correctly stays at
        # P09 (the last reported period) with P09's cumulative cents, and
        # P10 has a real File C event but no residual.
        temp, root = self._fixture(
            file_b_rows={8: 20, 9: 21, 10: 5},
            pin_as_of_period=9, pin_cents=500 + 300 + 600 + 400,
            include_p10_residual=False,
        )
        try:
            self.assertEqual([], validate(root, require_data=False))
        finally:
            temp.cleanup()

    def test_pin_advanced_onto_the_notreported_period_fails(self):
        # Same notReported P10 collapse, but the pin was wrongly advanced
        # to P10 instead of staying at P09 -- must error.
        temp, root = self._fixture(
            file_b_rows={8: 20, 9: 21, 10: 5},
            pin_as_of_period=10, pin_cents=500 + 300 + 600 + 400,
            include_p10_residual=False,
        )
        try:
            self.assertTrue(validate(root, require_data=False))
        finally:
            temp.cleanup()

    def test_pin_lagging_a_fully_reported_latest_period_still_fails(self):
        # No collapse at all -- P10 is an ordinary reported period (22
        # rows, no dip) -- but the pin was left behind at P09. This must
        # still error exactly as before the notReported-aware fix.
        temp, root = self._fixture(
            file_b_rows={8: 20, 9: 21, 10: 22},
            pin_as_of_period=9, pin_cents=500 + 300 + 600 + 400,
            include_p10_residual=True,
        )
        try:
            errors = validate(root, require_data=False)
            self.assertTrue(
                any("no same-period GTAS pin" in e for e in errors), errors,
            )
        finally:
            temp.cleanup()


class InterpretationNoteRollupTests(unittest.TestCase):
    """Phase 3.2d remediation decision 3: `interpretationNote` is an
    optional registry field (docs/verification-regime.md specialization
    schema). scripts/rollup_obligations.py is what actually carries it from
    the registry into every dashboard.json the site reads, and no existing
    validator schema-checks a dashboard.json's own shape -- this is the one
    place in the obligation-validation suite where that flow is covered
    end to end, on a minimal two-account fixture (append-only per the W4
    worker contract)."""

    def build_fixture(self, note="Note text."):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        (root / "config").mkdir()
        (root / "reference").mkdir()
        accounts = [
            {"path": "dod/army-rdte", "name": "Army RDT&E", "abbrev": "Army",
             "agency": "Department of Defense", "federalAccount": "021-2040",
             "baseline": "reference/army_baseline.json",
             "interpretationNote": note,
             "programActivities": [{"slug": "basic-research", "code": "0001",
                                    "name": "Basic Research"}]},
            {"path": "doe/sc", "name": "Office of Science", "abbrev": "DOE SC",
             "agency": "Department of Energy", "federalAccount": "089-0222",
             "baseline": "reference/doe_sc_baseline.json",
             "programActivities": [{"slug": "bes", "code": "0001", "name": "BES"}]},
        ]
        (root / "config" / "obligation_accounts.json").write_text(json.dumps({
            "schemaVersion": 2, "refreshDefaults": {"freshnessMaxDays": 10},
            "accounts": accounts}))
        for name, federal_account in (
            ("army_baseline.json", "021-2040"), ("doe_sc_baseline.json", "089-0222"),
        ):
            (root / "reference" / name).write_text(json.dumps({
                "schemaVersion": 2, "federalAccount": federal_account,
                "fiscalYears": {"2024": {"status": "complete", "obligationsCents": 100}}}))
        for account in accounts:
            row = normalize_event({
                "id": f"{account['path']}-one", "source": "file_c",
                "submissionPeriod": "FY2024P12",
                "federalAccount": account["federalAccount"],
                "programActivityCode": "0001",
                "programActivityName": account["programActivities"][0]["name"],
                "amountCents": 100, "awardId": "", "linked": False,
            })
            write_store(root / "data" / "obligations" / account["path"] / "events", [row])
        return temp, root

    def test_note_flows_to_account_and_program_activity_dashboards_only_for_the_noted_account(self):
        import scripts.rollup_obligations as rollup_obligations
        temp, root = self.build_fixture()
        try:
            rollup_obligations.build(root)
            noted = json.loads(
                (root / "data" / "obligations" / "dod" / "army-rdte" / "dashboard.json").read_text()
            )
            self.assertEqual("Note text.", noted["interpretationNote"])
            noted_pa = json.loads((root / "data" / "obligations" / "dod" / "army-rdte" /
                                   "basic-research" / "dashboard.json").read_text())
            self.assertEqual("Note text.", noted_pa["interpretationNote"])
            # The account page's own "Program activities" table children must
            # NOT each carry the note: the account page already shows it once
            # near the top, so repeating it as a per-PA-row footnote (one per
            # activity) would be exact-text repetition, not a useful note.
            for child in noted["children"]:
                self.assertNotIn("interpretationNote", child)

            unnoted = json.loads(
                (root / "data" / "obligations" / "doe" / "sc" / "dashboard.json").read_text()
            )
            self.assertNotIn("interpretationNote", unnoted)
            unnoted_pa = json.loads((root / "data" / "obligations" / "doe" / "sc" /
                                     "bes" / "dashboard.json").read_text())
            self.assertNotIn("interpretationNote", unnoted_pa)

            # The obligations root dashboard's children list is what the
            # site's landing-table row-note rendering reads.
            root_dashboard = json.loads(
                (root / "data" / "obligations" / "dashboard.json").read_text()
            )
            self.assertEqual(2, root_dashboard["accountCount"])
            dod_child = next(c for c in root_dashboard["children"]
                              if c["path"] == "obligations/dod")
            doe_child = next(c for c in root_dashboard["children"]
                              if c["path"] == "obligations/doe")
            self.assertEqual("Note text.", dod_child["interpretationNote"])
            self.assertNotIn("interpretationNote", doe_child)
        finally:
            temp.cleanup()


class RefreshStatusValidationTests(unittest.TestCase):
    """Phase 3.2d remediation W12: per-account atomicity + published
    staleness. A marked-stale account (data/obligations/refresh_status.json)
    must pass --check-freshness/--require-current-provenance instead of
    failing the whole reconcile, but its dashboard.json must still surface
    the disclosure; an account beyond the SLA with no such marking is still
    an error."""

    def build_fixture(self, accepted_at):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        (root / "config").mkdir()
        (root / "reference").mkdir()
        (root / "config" / "obligation_accounts.json").write_text(json.dumps({
            "schemaVersion": 2, "refreshDefaults": {"freshnessMaxDays": 10},
            "accounts": [{
                "path": "doe/sc", "name": "Science", "abbrev": "SC",
                "agency": "Energy", "federalAccount": "089-0222",
                "baseline": "reference/doe_sc_baseline.json",
                "programActivities": [{"slug": "bes", "code": "0001",
                                       "name": "BES"}],
            }],
        }))
        (root / "reference" / "doe_sc_baseline.json").write_text(json.dumps({
            "schemaVersion": 2, "federalAccount": "089-0222",
            "fiscalYears": {"2026": {"status": "partial", "asOfPeriod": 9,
                                      "firstPeriod": 9,
                                      "obligationsCents": 300}},
        }))
        row = normalize_event({
            "id": "one", "source": "file_b_residual",
            "submissionPeriod": "FY2026P09", "federalAccount": "089-0222",
            "programActivityCode": "0001", "programActivityName": "BES",
            "amountCents": 300, "awardId": "", "linked": False,
        })
        empty_sha = "0" * 64
        downloads = []
        for kind, period in (
                [("object_class_program_activity", value) for value in range(2, 10)]
                + [("award_financial", 9)]):
            row_count = 1 if kind == "object_class_program_activity" and period == 9 else 0
            downloads.append({
                "submissionType": kind,
                "requestScope": {"filters": {
                    "fy": 2026, "period": period,
                    "submission_types": [kind], "federal_account": "5778",
                }, "columns": ["submission_period"]},
                "acceptedRequestScope": {"filters": {
                    "fy": 2026, "period": period, "federal_account": "5778",
                }, "download_types": [kind]},
                "status": "finished", "statusRowCount": row_count,
                "parsedRowCount": row_count,
                "memberRowCounts": {"file": row_count} if row_count else {},
                "archiveSha256": empty_sha,
                "rawArtifactFile": f"{kind}-P{period:02}.zip",
            })
        provenance = {
            "schemaVersion": 2, "collectionStatus": "accepted",
            "acceptedAt": accepted_at,
            "accountPath": "doe/sc", "federalAccount": "089-0222",
            "fiscalYear": 2026, "asOfPeriod": 9, "downloads": downloads,
            "normalized": {"recordCount": 1,
                           "eventFingerprint": event_fingerprint([row]),
                           "netObligationsCents": 300},
            "replacement": {"previousEventFingerprint": empty_sha,
                            "previousProvenanceSha256": None},
            "diff": partition_diff([], [row]),
            "baselinePin": {"status": "partial", "asOfPeriod": 9,
                            "firstPeriod": 9, "obligationsCents": 300},
        }
        write_store(root / "data" / "obligations" / "doe" / "sc" / "events",
                    [row], {"federalAccount": "089-0222"},
                    partition_metadata={2026: provenance})
        return temp, root

    def write_refresh_status(self, root, entry):
        (root / "data" / "obligations" / "refresh_status.json").write_text(
            json.dumps({"schemaVersion": 1, "generatedAt": "2026-09-20T00:00:00+00:00",
                        "accounts": {"doe/sc": entry} if entry else {}})
        )

    def test_marked_stale_account_passes_freshness_and_dashboard_carries_it(self):
        temp, root = self.build_fixture("2026-08-25T00:00:00+00:00")
        try:
            stale_entry = {
                "lastRefreshAttemptAt": "2026-09-20T10:00:00+00:00",
                "lastAcceptedAt": "2026-08-25T00:00:00+00:00",
                "status": "stale", "staleSince": "2026-08-25",
                "reason": "the scheduled current-FY (FY2026) pull for this "
                          "account did not produce a partition in this run",
            }
            self.write_refresh_status(root, stale_entry)
            build_obligations(root)
            dashboard = json.loads(
                (root / "data" / "obligations" / "doe" / "sc" / "dashboard.json")
                .read_text()
            )
            self.assertEqual(stale_entry, dashboard["freshness"]["refreshStatus"])
            errors = validate(root, require_data=True, check_freshness=True,
                              require_current_provenance=True,
                              as_of=date(2026, 9, 20))
            self.assertEqual([], errors)
        finally:
            temp.cleanup()

    def test_unmarked_stale_account_still_fails_freshness(self):
        temp, root = self.build_fixture("2026-08-25T00:00:00+00:00")
        try:
            # No refresh_status.json at all: the account defaults to
            # "fresh", so an SLA breach is still an error -- nothing may go
            # stale silently.
            build_obligations(root)
            errors = validate(root, require_data=True, check_freshness=True,
                              require_current_provenance=True,
                              as_of=date(2026, 9, 20))
            self.assertTrue(
                any("outside the 0" in error and "not recorded as stale" in error
                    for error in errors),
                errors,
            )
        finally:
            temp.cleanup()

    def test_stale_status_without_reason_still_fails_freshness(self):
        temp, root = self.build_fixture("2026-08-25T00:00:00+00:00")
        try:
            # A bare status: "stale" with no reason does not count as a
            # proper disclosure.
            self.write_refresh_status(root, {"status": "stale"})
            build_obligations(root)
            errors = validate(root, require_data=True, check_freshness=True,
                              require_current_provenance=True,
                              as_of=date(2026, 9, 20))
            self.assertTrue(
                any("not recorded as stale" in error for error in errors), errors,
            )
        finally:
            temp.cleanup()

    def test_fresh_account_is_unaffected_by_refresh_status(self):
        temp, root = self.build_fixture("2026-09-18T00:00:00+00:00")
        try:
            # Recently accepted, well within the SLA, and no
            # refresh_status.json at all -- ordinary, unaffected accounts
            # must see no behavior change from this feature.
            build_obligations(root)
            dashboard = json.loads(
                (root / "data" / "obligations" / "doe" / "sc" / "dashboard.json")
                .read_text()
            )
            self.assertEqual({"status": "fresh"}, dashboard["freshness"]["refreshStatus"])
            errors = validate(root, require_data=True, check_freshness=True,
                              require_current_provenance=True,
                              as_of=date(2026, 9, 20))
            self.assertEqual([], errors)
        finally:
            temp.cleanup()

    def test_rollup_propagates_stale_account_to_agency_and_root_rows(self):
        # Phase 3.2d remediation W12: refreshStatus reaches every listing a
        # reader could browse without opening the stale account's own page
        # -- the agency page's account row and the root page's agency row
        # (aggregated, since staleness is not agency-uniform) -- plus the
        # root's own staleAccountCount.
        temp = tempfile.TemporaryDirectory()
        try:
            root = Path(temp.name)
            (root / "config").mkdir()
            (root / "reference").mkdir()
            accounts = [
                {"path": "doe/sc", "name": "Science", "abbrev": "SC",
                 "agency": "Energy", "federalAccount": "089-0222",
                 "baseline": "reference/doe_sc_baseline.json",
                 "programActivities": [{"slug": "bes", "code": "0001",
                                        "name": "BES"}]},
                {"path": "doe/fossil-energy", "name": "Fossil Energy",
                 "abbrev": "FE", "agency": "Energy",
                 "federalAccount": "089-0223",
                 "baseline": "reference/doe_fe_baseline.json",
                 "programActivities": [{"slug": "fe", "code": "0001",
                                        "name": "FE"}]},
            ]
            (root / "config" / "obligation_accounts.json").write_text(json.dumps({
                "schemaVersion": 2, "refreshDefaults": {"freshnessMaxDays": 10},
                "accounts": accounts,
            }))
            for account in accounts:
                (root / account["baseline"]).write_text(json.dumps({
                    "schemaVersion": 2, "federalAccount": account["federalAccount"],
                    "fiscalYears": {"2024": {"status": "complete",
                                              "obligationsCents": 100}},
                }))
                row = normalize_event({
                    "id": f"{account['path']}-one", "source": "file_c",
                    "submissionPeriod": "FY2024P12",
                    "federalAccount": account["federalAccount"],
                    "programActivityCode": "0001",
                    "programActivityName": account["programActivities"][0]["name"],
                    "amountCents": 100, "awardId": "", "linked": False,
                })
                write_store(root / "data" / "obligations" / account["path"] / "events",
                           [row])
            stale_entry = {
                "lastRefreshAttemptAt": "2026-09-20T10:00:00+00:00",
                "lastAcceptedAt": "2026-08-25T00:00:00+00:00",
                "status": "stale", "staleSince": "2026-08-25",
                "reason": "the scheduled current-FY (FY2026) pull for this "
                          "account did not produce a partition in this run",
            }
            self.write_refresh_status(root, stale_entry)
            build_obligations(root)

            agency_page = json.loads(
                (root / "data" / "obligations" / "doe" / "dashboard.json").read_text()
            )
            sc_row = next(c for c in agency_page["children"] if c["path"] == "obligations/doe/sc")
            fe_row = next(c for c in agency_page["children"]
                         if c["path"] == "obligations/doe/fossil-energy")
            self.assertEqual(stale_entry, sc_row["refreshStatus"])
            self.assertNotIn("refreshStatus", fe_row)

            root_page = json.loads(
                (root / "data" / "obligations" / "dashboard.json").read_text()
            )
            self.assertEqual(1, root_page["staleAccountCount"])
            doe_row = next(c for c in root_page["children"] if c["path"] == "obligations/doe")
            self.assertEqual("stale", doe_row["refreshStatus"]["status"])
            self.assertIn("1 of 2", doe_row["refreshStatus"]["reason"])
            self.assertEqual("2026-08-25", doe_row["refreshStatus"]["staleSince"])
        finally:
            temp.cleanup()

    def test_dashboard_refresh_status_mismatch_fails_closed(self):
        temp, root = self.build_fixture("2026-08-25T00:00:00+00:00")
        try:
            stale_entry = {
                "lastRefreshAttemptAt": "2026-09-20T10:00:00+00:00",
                "lastAcceptedAt": "2026-08-25T00:00:00+00:00",
                "status": "stale", "staleSince": "2026-08-25",
                "reason": "the scheduled current-FY (FY2026) pull for this "
                          "account did not produce a partition in this run",
            }
            self.write_refresh_status(root, stale_entry)
            build_obligations(root)
            # Simulate a dashboard that was never rebuilt after
            # refresh_status.json changed (a staleness disclosure risk this
            # check is designed to catch).
            dashboard_path = (root / "data" / "obligations" / "doe" / "sc"
                              / "dashboard.json")
            dashboard = json.loads(dashboard_path.read_text())
            dashboard["freshness"]["refreshStatus"] = {"status": "fresh"}
            dashboard_path.write_text(json.dumps(dashboard))
            errors = validate(root, require_data=True, check_freshness=True,
                              require_current_provenance=True,
                              as_of=date(2026, 9, 20))
            self.assertTrue(
                any("refreshStatus" in error and "does not match" in error
                    for error in errors),
                errors,
            )
        finally:
            temp.cleanup()


if __name__ == "__main__":
    unittest.main()
