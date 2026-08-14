import json
import tempfile
import unittest
from pathlib import Path

from adapters.obligation_common import (
    event_fingerprint, normalize_event, partition_diff, write_store,
)
from scripts.validate_obligations import validate


class ObligationValidationTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
