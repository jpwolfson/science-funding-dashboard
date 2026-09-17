import json
import tempfile
import unittest
from pathlib import Path

from adapters.obligation_common import (
    event_fingerprint, normalize_event, partition_diff, write_store,
)
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


if __name__ == "__main__":
    unittest.main()
