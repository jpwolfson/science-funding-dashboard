import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_usaspending_calibration import validate


class USAspendingCalibrationTests(unittest.TestCase):
    def fixture(self, root, adapter="nsf"):
        (root / "reference").mkdir()
        (root / "config").mkdir()
        calibration = {
            "status": "blocked",
            "onboardingAllowed": False,
            "selectedAwardSemantics": {
                "identity": "base award", "amount": "current total",
                "date": "base date", "timeFilter": "new_awards_only",
                "scopeWarning": "whole-award amount",
            },
            "calibrations": {"nsfDmsFy2024": {}, "nihNigmsFy2024": {}},
            "doeScienceGate": {
                "gtasAccountObligations": 1,
                "newBaseAwardCurrentObligations": 1,
                "accountFilteredTransactionObligations": 1,
                "programActivityProbe": {}, "assessment": "blocked",
            },
            "obligationLedger": {
                "status": "implementation-complete-backfill-pending",
                "canonicalSource": "File B cumulative CPE deltas",
                "awardEnrichmentSource": "File C reporting-period transaction obligated amounts",
                "federalAccount": "089-0222", "fileCFy2024ObligationsCents": 1,
                "gtasFy2024ObligationsCents": 1, "fileCCoverage": 1,
            },
        }
        (root / "reference" / "usaspending_calibration.json").write_text(
            json.dumps(calibration))
        (root / "config" / "orgs.json").write_text(json.dumps({
            "agencies": [{"slug": "pilot", "adapter": adapter}],
        }))

    def test_blocked_gate_allows_inactive_adapter_code(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            self.assertEqual(validate(root), [])

    def test_blocked_gate_rejects_registry_onboarding(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root, adapter="usaspending")
            self.assertTrue(any("registry agencies" in error
                                for error in validate(root)))

    def test_ready_gate_requires_passed_obligation_ledger(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            path = root / "reference" / "usaspending_calibration.json"
            calibration = json.loads(path.read_text())
            calibration["status"] = "ready"
            calibration["onboardingAllowed"] = True
            path.write_text(json.dumps(calibration))
            self.assertTrue(any("passed obligation-ledger" in error
                                for error in validate(root)))
            calibration["obligationLedger"]["status"] = "passed"
            path.write_text(json.dumps(calibration))
            self.assertEqual([], validate(root))


if __name__ == "__main__":
    unittest.main()
