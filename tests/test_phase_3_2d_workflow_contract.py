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


if __name__ == "__main__":
    unittest.main()
