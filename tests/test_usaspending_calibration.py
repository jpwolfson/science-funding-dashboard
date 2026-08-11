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


if __name__ == "__main__":
    unittest.main()
