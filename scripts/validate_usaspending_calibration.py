#!/usr/bin/env python3
"""Enforce the Phase 3.1 calibration gate.

The adapter may exist while calibration is blocked, but no registry agency
may use it until the artifact is explicitly reviewed and marked ready.
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CALIBRATION = REPO_ROOT / "reference" / "usaspending_calibration.json"
CONFIG = REPO_ROOT / "config" / "orgs.json"


def validate(repo_root=REPO_ROOT):
    root = Path(repo_root)
    calibration = json.loads(
        (root / "reference" / "usaspending_calibration.json").read_text())
    config = json.loads((root / "config" / "orgs.json").read_text())
    errors = []

    if calibration.get("status") not in {"blocked", "ready"}:
        errors.append("calibration status must be 'blocked' or 'ready'")
    if calibration.get("status") == "blocked" and calibration.get(
            "onboardingAllowed") is not False:
        errors.append("blocked calibration must set onboardingAllowed=false")
    if calibration.get("status") == "ready" and calibration.get(
            "onboardingAllowed") is not True:
        errors.append("ready calibration must set onboardingAllowed=true")

    required_semantics = {"identity", "amount", "date", "timeFilter",
                          "scopeWarning"}
    missing = required_semantics - set(
        calibration.get("selectedAwardSemantics") or {})
    if missing:
        errors.append(f"selectedAwardSemantics is missing {sorted(missing)}")

    comparisons = calibration.get("calibrations") or {}
    for name in ("nsfDmsFy2024", "nihNigmsFy2024"):
        if name not in comparisons:
            errors.append(f"missing required calibration comparator {name}")

    gate = calibration.get("doeScienceGate") or {}
    for key in ("gtasAccountObligations", "newBaseAwardCurrentObligations",
                "accountFilteredTransactionObligations",
                "programActivityProbe", "assessment"):
        if key not in gate:
            errors.append(f"DOE Science gate is missing {key}")

    active = [agency.get("slug") for agency in config.get("agencies", [])
              if agency.get("adapter") == "usaspending"]
    if not calibration.get("onboardingAllowed") and active:
        errors.append(
            "USAspending onboarding is blocked, but registry agencies use it: "
            + ", ".join(active))
    return errors


def main():
    errors = validate()
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        raise SystemExit(
            f"USAspending calibration validation failed with {len(errors)} error(s)")
    status = json.loads(CALIBRATION.read_text())["status"]
    print(f"USAspending calibration gate passed (status: {status})")


if __name__ == "__main__":
    main()
