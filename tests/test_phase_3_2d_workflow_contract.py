"""Workflow contract for the Phase 3.2d worker protocol."""

import re
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent


class Phase32dWorkflowContractTests(unittest.TestCase):
    def test_agent_branches_receive_normal_ci(self):
        workflow = (REPO / ".github/workflows/ci.yml").read_text()
        self.assertIn('"agent/**"', workflow)

    def test_agent_trigger_commit_starts_obligation_backfill(self):
        workflow = (
            REPO / ".github/workflows/update-obligations.yml"
        ).read_text()
        self.assertIn('"agent/**"', workflow)
        self.assertIn(
            'paths: [".github/triggers/update-obligations.json"]',
            workflow,
        )

    def test_obligation_refresh_commits_rebuilt_sentinel_candidate(self):
        workflow = (
            REPO / ".github/workflows/update-obligations.yml"
        ).read_text()
        self.assertIn('["data/obligations", "data/sentinel"]', workflow)

    def test_serial_matrix_partitions_outlive_the_longest_supported_run(self):
        workflow = (
            REPO / ".github/workflows/update-obligations.yml"
        ).read_text()
        partition_start = workflow.index(
            "name: obligation-partition-${{ matrix.artifact }}"
        )
        raw_start = workflow.index("name: obligation-raw-", partition_start)
        partition_upload = workflow[partition_start:raw_start]
        match = re.search(r"retention-days:\s*(\d+)", partition_upload)
        self.assertIsNotNone(match)
        # The observed 100-job DOE matrix takes more than 24 hours at
        # max-parallel=1. Three days is the minimum safe contract; the workflow
        # keeps a larger operational cushion without retaining raw downloads.
        self.assertGreaterEqual(int(match.group(1)), 3)

    def test_failed_job_reruns_keep_raw_artifacts_without_name_collisions(self):
        workflow = (
            REPO / ".github/workflows/update-obligations.yml"
        ).read_text()
        self.assertIn(
            "name: obligation-raw-${{ matrix.artifact }}-"
            "FY${{ matrix.fiscalYear }}-attempt${{ github.run_attempt }}",
            workflow,
        )
        # Normalized artifacts keep their stable account/FY names so the
        # reconciliation fan-in remains independent of the producing attempt.
        self.assertIn(
            "name: obligation-partition-${{ matrix.artifact }}-"
            "FY${{ matrix.fiscalYear }}\n",
            workflow,
        )

    def test_legacy_retry_artifact_recovery_preserves_before_delete(self):
        workflow = (
            REPO / ".github/workflows/preserve-obligation-retry-artifacts.yml"
        ).read_text()
        self.assertIn("actions: write", workflow)
        self.assertIn("contents: write", workflow)
        self.assertIn(
            'paths: [".github/triggers/preserve-obligation-retry-artifacts.json"]',
            workflow,
        )
        preserve = workflow.index("Validate, download, and hash every source ZIP")
        upload = workflow.index("Retain the verified source ZIPs before remote deletion")
        commit = workflow.index(
            "Commit the exact preservation bundle to the operational branch"
        )
        delete = workflow.index("Delete only the exact preserved conflicting artifacts")
        self.assertLess(preserve, upload)
        self.assertLess(upload, commit)
        self.assertLess(commit, delete)


class PublicationGateDecouplingTests(unittest.TestCase):
    """Phase 3.2d remediation, W2 (HIGH-2): the sentinel and obligation
    publication gates must not run the NIH award-ledger's own suite, and
    must not run scripts/verify.py's full "fast" tier (which does). See
    docs/verification-regime.md, "Workflow-to-gate mapping", and
    docs/phase-3.2d-remediation-brief.md, "W2 -- Decouple publication
    gates"."""

    def test_sentinel_workflow_does_not_discover_the_full_test_tree(self):
        workflow = (
            REPO / ".github/workflows/update-sentinel.yml"
        ).read_text()
        self.assertNotIn("unittest discover -s tests", workflow)

    def test_sentinel_workflow_never_runs_nih_validation_or_nih_tests(self):
        workflow = (
            REPO / ".github/workflows/update-sentinel.yml"
        ).read_text()
        self.assertNotIn("validate_nih.py", workflow)
        self.assertNotIn("test_nih_reporter", workflow)
        self.assertNotIn("test_nih_validation", workflow)

    def test_sentinel_workflow_runs_its_own_unit_and_contract_suites(self):
        workflow = (
            REPO / ".github/workflows/update-sentinel.yml"
        ).read_text()
        for module in (
            "tests.test_funding_sentinel",
            "tests.test_funding_sentinel_validation",
            "tests.test_funding_source_adapters",
            "tests.test_site_contract",
        ):
            self.assertIn(module, workflow)
        self.assertIn("validate_funding_sentinel.py", workflow)

    def test_obligation_reconcile_never_runs_verify_fast_tier(self):
        workflow = (
            REPO / ".github/workflows/update-obligations.yml"
        ).read_text()
        self.assertNotIn("--tier fast", workflow)

    def test_obligation_reconcile_never_runs_nih_validation_or_nih_tests(self):
        workflow = (
            REPO / ".github/workflows/update-obligations.yml"
        ).read_text()
        self.assertNotIn("validate_nih.py", workflow)
        self.assertNotIn("test_nih_reporter", workflow)
        self.assertNotIn("test_nih_validation", workflow)

    def test_obligation_reconcile_keeps_its_own_offline_gates(self):
        workflow = (
            REPO / ".github/workflows/update-obligations.yml"
        ).read_text()
        self.assertIn("validate_obligations.py", workflow)
        self.assertIn("--check-freshness --require-current-provenance", workflow)
        self.assertIn("validate_award_invariants.py", workflow)
        self.assertIn("--tier rendered", workflow)
        for module in (
            "tests.test_obligation_aggregation",
            "tests.test_obligation_validation",
            "tests.test_obligations_dod",
            "tests.test_usaspending_obligations",
            "tests.test_verification_regime",
            "tests.test_pages_footprint",
        ):
            self.assertIn(module, workflow)

    def test_update_data_rollup_still_runs_validate_nih(self):
        # update-data.yml is W1's file, not W2's; W2 only asserts it is left
        # alone -- the NIH ledger keeps validating itself on its own
        # workflow.
        workflow = (REPO / ".github/workflows/update-data.yml").read_text()
        self.assertIn("validate_nih.py --live", workflow)

    def test_verify_main_workflow_exists_with_schedule_fast_tier_and_issue_filing(self):
        path = REPO / ".github/workflows/verify-main.yml"
        self.assertTrue(path.exists(), "expected .github/workflows/verify-main.yml")
        workflow = path.read_text()
        self.assertIn("schedule:", workflow)
        self.assertIn("workflow_run:", workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("--tier fast", workflow)
        self.assertIn("actions/github-script", workflow)
        self.assertIn("issues: write", workflow)
        self.assertIn("verify --tier fast failed on main", workflow)
        self.assertIn("concurrency:", workflow)

    def test_verify_main_workflow_never_gates_a_deploy(self):
        workflow = (REPO / ".github/workflows/verify-main.yml").read_text()
        self.assertNotIn("needs:", workflow)
        self.assertNotIn("deploy-pages", workflow)


if __name__ == "__main__":
    unittest.main()


class NihExclusionLedgerCommitTests(unittest.TestCase):
    """The pull-nih job must commit exclusions-ledger status flips with the
    unit's data, or a returned id is counted by the leaf dashboard but still
    excluded by the committed ledger (2026-09-17 run 35240994598 rollup
    failure: nih/ninds/ninds totalAwards=53141 vs aggregated 53140)."""

    def test_pull_nih_commit_step_stages_the_exclusions_ledger(self):
        text = (REPO / ".github" / "workflows" / "update-data.yml").read_text()
        nih_job = text[text.index("  pull-nih:"):text.index("  rollup:")]
        self.assertIn(
            'git add "data/${{ matrix.unit }}" reference/nih_reporter_exclusions.json',
            nih_job,
        )


class PushRetryTests(unittest.TestCase):
    """Every workflow that commits to the branch must replay its commit on a
    non-fast-forward push instead of failing the run (2026-09-17 sentinel run
    35251254148 failed only at `git push`, after a green build, because NIH
    leaf commits had landed on main meanwhile)."""

    def test_sentinel_and_obligation_commits_retry_with_rebase(self):
        for name in ("update-sentinel.yml", "update-obligations.yml"):
            text = (REPO / ".github" / "workflows" / name).read_text()
            with self.subTest(workflow=name):
                self.assertIn('"pull", "--rebase", "-X", "theirs"', text)
                self.assertNotIn(
                    'subprocess.run(["git", "push", "origin", f"HEAD:{branch}"], check=True)',
                    text,
                )


class ReconcileTolerantOfHistoricalPullFailureTests(unittest.TestCase):
    """Phase 3.2d remediation, W11: a single failed rotating-historical
    re-pull in the 106-job serial matrix (e.g. usda/nifa-research-education
    FY2019 on 2026-09-19, ed/ies FY2018 in every attempt of run
    34141166514) must not skip reconcile and lose the whole weekly pass.
    Only a missing current-FY partition may still block publication -- see
    docs/obligation-ledger.md, "Refresh, freshness, and publication"."""

    def setUp(self):
        self.workflow = (
            REPO / ".github/workflows/update-obligations.yml"
        ).read_text()

    def test_reconcile_runs_even_if_a_pull_job_failed(self):
        reconcile_start = self.workflow.index("  reconcile:")
        deploy_start = self.workflow.index("  deploy:")
        reconcile_job = self.workflow[reconcile_start:deploy_start]
        self.assertIn("needs: [plan, pull-account-year]", reconcile_job)
        self.assertIn(
            "if: ${{ !cancelled() && needs.plan.result == 'success' }}",
            reconcile_job,
        )

    def test_deploy_still_requires_reconcile_to_succeed(self):
        deploy_start = self.workflow.index("  deploy:")
        deploy_job = self.workflow[deploy_start:]
        self.assertIn("needs: reconcile", deploy_job)
        # No override here: deploy keeps the default success()-only gate.
        self.assertNotIn("needs.reconcile.result", deploy_job)

    def test_missing_partitions_are_detected_before_reconciling(self):
        detect_start = self.workflow.index(
            "Detect account-years missing from this run's partitions"
        )
        reconcile_step = self.workflow.index(
            "Reconcile every account into one candidate snapshot"
        )
        self.assertLess(detect_start, reconcile_step)
        detection = self.workflow[detect_start:reconcile_step]
        self.assertIn("needs.plan.outputs.matrix", detection)
        self.assertIn("_missing_partitions.json", detection)
        reconcile_call = self.workflow[reconcile_step:]
        self.assertIn(
            "reconcile_obligation_artifacts.py --staging _partitions\n"
            "          --plan _missing_partitions.json",
            reconcile_call,
        )

    def test_reconcile_script_distinguishes_current_from_historical_purpose(self):
        script = (REPO / "scripts/reconcile_obligation_artifacts.py").read_text()
        self.assertIn('MANDATORY_PURPOSE = "current"', script)
        self.assertIn("SKIPPED (pull failed)", script)
        self.assertIn("GITHUB_STEP_SUMMARY", script)
