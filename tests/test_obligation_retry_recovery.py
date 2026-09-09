import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from scripts.obligation_retry_recovery import (
    RecoveryError,
    RetryRecovery,
    load_retry_recovery,
)
from scripts.pull_obligation_account import FILE_B_COLUMNS, _baseline_pin, _download


REPOSITORY = "jpwolfson/science-funding-dashboard"
RUN_ID = 34141166514
SOURCE_SHA = "e8fa3b584fa1a66687667804ffa6d0f4f2d0a35d"
EVIDENCE_SHA = "b2a5055aaec482cc10330ad7a57d09987e21c294"
ACCOUNT = {
    "path": "agency/account",
    "federalAccount": "999-0001",
    "baseline": "reference/account.json",
}


def zipped(members):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, payload in members.items():
            archive.writestr(name, payload)
    return output.getvalue()


def descriptor_file(name, payload):
    return {
        "memberName": name,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size": len(payload),
    }


def fixture():
    csv_payload = (
        "submission_period,federal_account_symbol,program_activity_reporting_key,"
        "program_activity_code,program_activity_name,obligations_incurred\n"
        "FY2026P02,999-0001,PARK1,0001,Research,1.25\n"
    ).encode()
    raw_payload = zipped({"source.csv": csv_payload})
    raw_name = (
        "agency--account-FY2026P02-object_class_program_activity-"
        f"{hashlib.sha256(raw_payload).hexdigest()[:12]}.zip"
    )
    resume_value = {
        "schemaVersion": 1,
        "requests": [{
            "account": ACCOUNT["path"],
            "fiscalYear": 2026,
            "period": 3,
            "submissionType": "object_class_program_activity",
            "result": {
                "status_url": "/api/v2/download/status/accepted",
                "download_request": {
                    "account_level": "federal_account",
                    "file_format": "csv",
                    "columns": FILE_B_COLUMNS,
                    "download_types": ["object_class_program_activity"],
                    "filters": {
                        "federal_account": "42",
                        "fy": 2026,
                        "period": 3,
                    },
                },
            },
        }],
    }
    resume_payload = (json.dumps(resume_value, sort_keys=True) + "\n").encode()
    resume_name = "obligation-download-resume-agency--account-FY2026P03-object_class_program_activity.json"

    events = b"accepted normalized events\n"
    provenance = (json.dumps({
        "schemaVersion": 2,
        "collectionStatus": "accepted",
        "accountPath": ACCOUNT["path"],
        "federalAccount": ACCOUNT["federalAccount"],
        "fiscalYear": 2026,
    }, sort_keys=True) + "\n").encode()
    normalized = {
        "FY2026.csv.gz": events,
        "FY2026.provenance.json": provenance,
    }
    partition = (json.dumps({
        "schemaVersion": 2,
        "accountPath": ACCOUNT["path"],
        "federalAccount": ACCOUNT["federalAccount"],
        "fiscalYears": [2026],
        "files": [
            {"name": name, "sha256": hashlib.sha256(payload).hexdigest()}
            for name, payload in normalized.items()
        ],
    }, sort_keys=True) + "\n").encode()
    normalized["partition.json"] = partition

    outer = zipped({raw_name: raw_payload, resume_name: resume_payload, **normalized})
    artifact_id = 17
    artifact = {
        "artifactId": artifact_id,
        "artifactName": "obligation-raw-agency--account-FY2026-attempt1",
        "artifactDigest": "sha256:" + hashlib.sha256(outer).hexdigest(),
        "artifactSize": len(outer),
        "deleteAfterPreserve": False,
    }
    pin = {
        "status": "partial",
        "asOfPeriod": 10,
        "obligationsCents": 101,
        "fileBObligationsCents": 99,
        "fileAFileBVarianceCents": 2,
        "fileAFileBVarianceReason": "Exact source-declared difference",
    }
    manifest = {
        "schemaVersion": 1,
        "repository": REPOSITORY,
        "workflowRunId": RUN_ID,
        "sourceAttempt": 1,
        "minimumRetryAttempt": 2,
        "sourceHeadSha": SOURCE_SHA,
        "sourceEvent": "schedule",
        "headBranch": "main",
        "evidenceBranch": "agent/recovery-evidence",
        "evidenceCommit": EVIDENCE_SHA,
        "preservationPath": "reference/obligation-retry-evidence/34141166514/preservation.json",
        "preservedArtifacts": [artifact],
        "rawEvidence": [{
            "artifactId": artifact_id,
            "accountPath": ACCOUNT["path"],
            "federalAccount": ACCOUNT["federalAccount"],
            "sourceAccountId": "42",
            "fiscalYear": 2026,
            "rawArchives": [{
                **descriptor_file(raw_name, raw_payload),
                "period": 2,
                "submissionType": "object_class_program_activity",
                "memberRowCounts": {"source.csv": 1},
                "parsedRowCount": 1,
            }],
            "resumeRequests": [{
                **descriptor_file(resume_name, resume_payload),
                "fiscalYear": 2026,
                "period": 3,
                "submissionType": "object_class_program_activity",
            }],
        }],
        "normalizedPartitions": [{
            "artifactId": artifact_id + 1,
            "accountPath": ACCOUNT["path"],
            "federalAccount": ACCOUNT["federalAccount"],
            "fiscalYear": 2026,
            "files": [
                descriptor_file(name, payload)
                for name, payload in normalized.items()
            ],
        }],
        "baselinePins": [{
            "accountPath": ACCOUNT["path"],
            "fiscalYear": 2026,
            "pin": pin,
        }],
    }
    partition_outer = zipped(normalized)
    partition_artifact = {
        "artifactId": artifact_id + 1,
        "artifactName": "obligation-partition-agency--account-FY2026",
        "artifactDigest": "sha256:" + hashlib.sha256(partition_outer).hexdigest(),
        "artifactSize": len(partition_outer),
        "deleteAfterPreserve": True,
    }
    manifest["preservedArtifacts"].append(partition_artifact)
    record = {
        "schemaVersion": 1,
        "repository": REPOSITORY,
        "runId": RUN_ID,
        "artifacts": [
            {
                "id": artifact_id,
                "name": artifact["artifactName"],
                "digest": artifact["artifactDigest"],
                "deleteAfterPreserve": False,
                "file": f"artifacts/{artifact_id}.zip",
                "size": artifact["artifactSize"],
            },
            {
                "id": artifact_id + 1,
                "name": partition_artifact["artifactName"],
                "digest": partition_artifact["artifactDigest"],
                "deleteAfterPreserve": True,
                "file": f"artifacts/{artifact_id + 1}.zip",
                "size": partition_artifact["artifactSize"],
            },
        ],
    }
    root = Path(manifest["preservationPath"]).parent
    blobs = {
        manifest["preservationPath"]: json.dumps(record).encode(),
        str(root / "artifacts" / f"{artifact_id}.zip"): outer,
        str(root / "artifacts" / f"{artifact_id + 1}.zip"): partition_outer,
    }
    return manifest, blobs, raw_name, pin


class ObligationRetryRecoveryTests(unittest.TestCase):
    def test_repository_manifest_has_exact_recovery_scope(self):
        repo = Path(__file__).resolve().parent.parent
        manifest = json.loads(
            (repo / "reference" / "obligation_retry_recovery.json").read_text()
        )
        RetryRecovery(repo, manifest, lambda _: b"")
        self.assertEqual(RUN_ID, manifest["workflowRunId"])
        self.assertEqual(EVIDENCE_SHA, manifest["evidenceCommit"])
        self.assertEqual(9, len(manifest["preservedArtifacts"]))
        self.assertEqual(8, len(manifest["rawEvidence"]))
        self.assertEqual(1, len(manifest["normalizedPartitions"]))
        self.assertEqual([], manifest["baselinePins"])

    def test_manifest_is_inert_outside_exact_retry(self):
        manifest, _, _, _ = fixture()
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            path = repo / "reference" / "obligation_retry_recovery.json"
            path.parent.mkdir()
            path.write_text(json.dumps(manifest))
            env = {
                "GITHUB_RUN_ID": str(RUN_ID + 1),
                "GITHUB_RUN_ATTEMPT": "2",
            }
            self.assertIsNone(load_retry_recovery(repo, env))
            env["GITHUB_RUN_ID"] = str(RUN_ID)
            env["GITHUB_RUN_ATTEMPT"] = "1"
            self.assertIsNone(load_retry_recovery(repo, env))

    def test_activation_mismatch_fails_closed(self):
        manifest, blobs, _, _ = fixture()
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            path = repo / "reference" / "obligation_retry_recovery.json"
            path.parent.mkdir()
            path.write_text(json.dumps(manifest))
            env = {
                "GITHUB_RUN_ID": str(RUN_ID),
                "GITHUB_RUN_ATTEMPT": "2",
                "GITHUB_REPOSITORY": REPOSITORY,
                "GITHUB_REF_NAME": "wrong-branch",
                "GITHUB_EVENT_NAME": "schedule",
                "GITHUB_SHA": SOURCE_SHA,
            }
            with self.assertRaisesRegex(RecoveryError, "activation mismatch"):
                load_retry_recovery(repo, env, blob_reader=blobs.__getitem__)

    def test_raw_reuse_does_not_submit_a_new_request(self):
        manifest, blobs, raw_name, _ = fixture()
        recovery = RetryRecovery(Path("."), manifest, blobs.__getitem__)
        with tempfile.TemporaryDirectory() as directory, patch(
            "scripts.pull_obligation_account.request_download"
        ) as request:
            members, audit = _download(
                Path(directory), ACCOUNT, "42", 2026, 2,
                "object_class_program_activity", FILE_B_COLUMNS,
                raw_archive_dir=directory, recovery=recovery,
            )
            request.assert_not_called()
            self.assertEqual(1, len(members["source.csv"]))
            self.assertEqual(1, audit["parsedRowCount"])
            self.assertTrue((Path(directory) / raw_name).exists())
            self.assertEqual(EVIDENCE_SHA, audit["recoveryEvidence"]["evidenceCommit"])

    def test_resume_and_normalized_partition_are_exact(self):
        manifest, blobs, _, _ = fixture()
        recovery = RetryRecovery(Path("."), manifest, blobs.__getitem__)
        resumed = recovery.resume_result(
            ACCOUNT, "42", 2026, 3, "object_class_program_activity"
        )
        self.assertEqual(
            "/api/v2/download/status/accepted", resumed["status_url"]
        )
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "partition"
            self.assertTrue(
                recovery.restore_partition(ACCOUNT, [2026], destination)
            )
            self.assertEqual(
                {"FY2026.csv.gz", "FY2026.provenance.json", "partition.json"},
                {path.name for path in destination.iterdir()},
            )

    def test_exact_baseline_pin_override_is_gated_by_file_b_total(self):
        manifest, blobs, _, pin = fixture()
        recovery = RetryRecovery(Path("."), manifest, blobs.__getitem__)
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            baseline = repo / "reference" / "account.json"
            baseline.parent.mkdir()
            baseline.write_text(json.dumps({
                "schemaVersion": 2,
                "federalAccount": ACCOUNT["federalAccount"],
                "fiscalYears": {"2026": {
                    "status": "partial",
                    "asOfPeriod": 9,
                    "obligationsCents": 90,
                }},
            }))
            self.assertEqual(
                pin,
                _baseline_pin(
                    repo, ACCOUNT, 2026, 10, 99, recovery=recovery
                ),
            )
            with self.assertRaisesRegex(ValueError, "does not match accepted"):
                _baseline_pin(
                    repo, ACCOUNT, 2026, 10, 98, recovery=recovery
                )

    def test_preservation_or_artifact_tampering_is_rejected(self):
        manifest, blobs, _, _ = fixture()
        bad_record = dict(blobs)
        bad_record[manifest["preservationPath"]] = b"{}"
        recovery = RetryRecovery(Path("."), manifest, bad_record.__getitem__)
        with self.assertRaisesRegex(RecoveryError, "preservation record differs"):
            recovery.recover_raw(
                ACCOUNT, "42", 2026, 2, "object_class_program_activity",
                FILE_B_COLUMNS, None,
            )

        bad_outer = dict(blobs)
        artifact_path = next(path for path in blobs if path.endswith("/17.zip"))
        bad_outer[artifact_path] += b"tamper"
        recovery = RetryRecovery(Path("."), manifest, bad_outer.__getitem__)
        with self.assertRaisesRegex(RecoveryError, "size mismatch"):
            recovery.recover_raw(
                ACCOUNT, "42", 2026, 2, "object_class_program_activity",
                FILE_B_COLUMNS, None,
            )


if __name__ == "__main__":
    unittest.main()
