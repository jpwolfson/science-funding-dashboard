"""Contract test for the uniform verification regime (docs/verification-regime.md).

GOVERNING PRINCIPLE: the verification regime is uniform across agencies. The
verifier contains universal invariants only; every agency-specific fact is a
declared parameter in that account's registry entry
(config/obligation_accounts.json) or baseline file
(reference/*_obligation_baseline.json). No agency-conditional code paths in
any verifier.

This test enforces that mechanically: no registry agency/account slug may
appear as a string literal in the shared verifier modules. The slug list is
derived from the registry itself at test time, so a newly onboarded agency
is covered automatically without ever touching this file.

scripts/validate_funding_sentinel.py is intentionally excluded. Its DOE
October 2025 announcement pins ("doe-october-2025-portfolio-action" etc.)
are per-SOURCE content pins that hold one sourced event's structured fields
constant (see Phase 3.2c-2) -- sentinel scope, not obligation-account
verification -- so they are not a violation of this contract and are not
flagged here.
"""

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.smoke_obligation_pages import _evaluate_case, _start_chrome
from scripts.verify import _lint_account, _run_command

REPO = Path(__file__).resolve().parent.parent
CHECKED_FILES = (
    "scripts/verify.py",
    "scripts/validate_obligations.py",
    "scripts/validate_award_invariants.py",
    "scripts/smoke_obligation_pages.py",
)


def registry_slugs():
    config = json.loads(
        (REPO / "config" / "obligation_accounts.json").read_text()
    )
    slugs = set()
    for account in config.get("accounts", []):
        path = account.get("path", "")
        segments = [segment for segment in path.split("/") if segment]
        slugs.update(segments)
        if path:
            slugs.add(path)
    # Slugs shorter than 3 characters are too collision-prone against
    # ordinary English words/identifiers to check as a whole-word literal
    # (there are none in the registry today; this guards future entries).
    return {slug for slug in slugs if len(slug) >= 3}


class UniformityContractTests(unittest.TestCase):
    def test_rendered_gate_retries_only_chrome_cold_start(self):
        first, second = Mock(pid=101), Mock(pid=202)
        page = {"webSocketDebuggerUrl": "ws://127.0.0.1:9222/devtools/page/1"}
        with tempfile.TemporaryDirectory() as profile_root, patch(
                "scripts.smoke_obligation_pages._free_port",
                side_effect=[9101, 9102]), patch(
                "scripts.smoke_obligation_pages.subprocess.Popen",
                side_effect=[first, second]) as popen, patch(
                "scripts.smoke_obligation_pages._wait_for_devtools",
                side_effect=[TimeoutError("cold start"), page]) as wait, patch(
                "scripts.smoke_obligation_pages._stop_chrome",
                return_value="first attempt diagnostics") as stop:
            process, observed = _start_chrome(
                "/chrome", profile_root, attempts=2, startup_timeout=20
            )

        self.assertIs(second, process)
        self.assertEqual(page, observed)
        self.assertEqual(2, popen.call_count)
        self.assertEqual(2, wait.call_count)
        stop.assert_called_once_with(first)
        first_command, second_command = (
            call.args[0] for call in popen.call_args_list
        )
        self.assertIn("--remote-debugging-port=9101", first_command)
        self.assertIn("--remote-debugging-port=9102", second_command)
        self.assertNotEqual(
            next(value for value in first_command
                 if value.startswith("--user-data-dir=")),
            next(value for value in second_command
                 if value.startswith("--user-data-dir=")),
        )

    def test_rendered_gate_rejects_every_collected_browser_error(self):
        document = {
            "html": '<html data-render-complete="true"><a href="/">home</a></html>',
            "text": "home", "width": 1440, "dark": False,
        }
        errors = _evaluate_case(
            document,
            "Failed to load resource: status 404",
            1440,
            "light",
        )
        self.assertEqual(
            ["browser diagnostic: Failed to load resource: status 404"],
            errors,
        )

    def test_failed_command_evidence_retains_actionable_trace_tail(self):
        result = _run_command(
            "diagnostic",
            [sys.executable, "-c", (
                "import sys; "
                "print('exact failing test'); "
                "print('Traceback: actionable detail', file=sys.stderr); "
                "raise SystemExit(1)"
            )],
            cwd=REPO,
        )
        self.assertFalse(result["passed"])
        self.assertIn("exact failing test", result["evidence"])
        self.assertIn("Traceback: actionable detail", result["evidence"])

    def account_fixture(self):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        (root / "reference").mkdir()
        baseline = root / "reference" / "account.json"
        baseline.write_text(json.dumps({
            "schemaVersion": 2,
            "federalAccount": "999-0001",
            "source": "Official baseline",
            "fiscalYears": {
                "2024": {"status": "complete", "obligationsCents": 1},
            },
        }))
        account = {
            "path": "agency/account", "name": "Account", "abbrev": "A",
            "agency": "Agency", "federalAccount": "999-0001",
            "agencyIdentifier": "999", "adapter": "usaspending_obligations",
            "baseline": "reference/account.json",
            "availability": {"firstFiscalYear": 2024,
                             "firstFiscalYearPeriod": 2,
                             "regularFirstPeriod": 2},
            "programActivities": [
                {"slug": "program", "code": "0001", "name": "Program"},
            ],
        }
        return temporary, root, account

    def test_resolved_mapping_is_not_blocked_by_separate_provisional_view(self):
        temporary, root, account = self.account_fixture()
        try:
            rows = [
                {"aaas_row_key": "resolved-view", "status": "resolved",
                 "federal_accounts": [{"code": "999-0001"}]},
                {"aaas_row_key": "provisional-view", "status": "provisional",
                 "federal_accounts": [{"code": "999-0001"}]},
            ]
            check = _lint_account(root, account, rows)[-1]
            self.assertTrue(check["passed"])
            self.assertIn("deferred", check["evidence"])
        finally:
            temporary.cleanup()

    def test_account_with_only_provisional_mapping_still_fails(self):
        temporary, root, account = self.account_fixture()
        try:
            rows = [
                {"aaas_row_key": "provisional-view", "status": "provisional",
                 "federal_accounts": [{"code": "999-0001"}]},
            ]
            check = _lint_account(root, account, rows)[-1]
            self.assertFalse(check["passed"])
            self.assertIn("no resolved", check["evidence"])
        finally:
            temporary.cleanup()

    def test_registry_lints_dual_exact_file_a_file_b_pins(self):
        temporary, root, account = self.account_fixture()
        try:
            baseline = root / account["baseline"]
            value = json.loads(baseline.read_text())
            value["fiscalYears"]["2024"] = {
                "status": "complete",
                "obligationsCents": 101,
                "fileBObligationsCents": 100,
                "fileAFileBVarianceCents": 1,
                "fileAFileBVarianceReason": "Official source warning A19",
            }
            baseline.write_text(json.dumps(value))
            checks = _lint_account(root, account, [])
            status = next(check for check in checks
                          if "baseline per-FY status map" in check["name"])
            self.assertTrue(status["passed"], status["evidence"])

            value["fiscalYears"]["2024"].pop("fileAFileBVarianceReason")
            baseline.write_text(json.dumps(value))
            checks = _lint_account(root, account, [])
            status = next(check for check in checks
                          if "baseline per-FY status map" in check["name"])
            self.assertFalse(status["passed"])
            self.assertIn("must be declared together", status["evidence"])
        finally:
            temporary.cleanup()

    def test_no_registry_slug_is_a_string_literal_in_shared_verifiers(self):
        slugs = registry_slugs()
        self.assertTrue(slugs, "expected at least one registry slug to check")
        violations = []
        for rel_path in CHECKED_FILES:
            text = (REPO / rel_path).read_text()
            for slug in sorted(slugs):
                pattern = re.compile(r"(?<![\w/-])" + re.escape(slug) + r"(?![\w/-])")
                if pattern.search(text):
                    violations.append(f"{rel_path}: contains registry slug {slug!r}")
        self.assertEqual(
            [], violations,
            "shared verifiers must read agency-specific facts from the "
            "registry/baseline, never hardcode them:\n" + "\n".join(violations),
        )

    def test_funding_sentinel_validator_is_deliberately_excluded(self):
        self.assertNotIn(
            "scripts/validate_funding_sentinel.py", CHECKED_FILES,
            "the sentinel validator's DOE-announcement pins are per-source "
            "content pins, not account verification -- see module docstring",
        )


if __name__ == "__main__":
    unittest.main()
