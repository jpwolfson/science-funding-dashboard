import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.manage_workflow_retry_artifacts import (
    ManifestError,
    delete_preserved,
    load_source_manifest,
    preserve,
)


REPOSITORY = "jpwolfson/science-funding-dashboard"
RUN_ID = 31623021735
CONTENT = b"raw source zip evidence"
DIGEST = "sha256:" + hashlib.sha256(CONTENT).hexdigest()
ROW = {
    "id": 9159398924,
    "name": "obligation-raw-nsf--mrefc-FY2024",
    "digest": DIGEST,
}
NORMALIZED_ROW = {**ROW, "deleteAfterPreserve": True}


class FakeArtifacts:
    def __init__(self):
        self.deleted = []

    def run_metadata(self, run_id):
        return {"id": run_id, "status": "completed"}

    def metadata(self, artifact_id):
        return {
            "id": artifact_id,
            "name": ROW["name"],
            "digest": DIGEST,
            "expired": False,
            "workflow_run": {"id": RUN_ID},
        }

    def download(self, artifact_id, target):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(CONTENT)
        return len(CONTENT), DIGEST

    def delete(self, artifact_id):
        self.deleted.append(artifact_id)


class WorkflowRetryArtifactTests(unittest.TestCase):
    def source_manifest(self, root, row=ROW):
        path = root / "source.json"
        path.write_text(json.dumps({
            "schemaVersion": 1,
            "repository": REPOSITORY,
            "runId": RUN_ID,
            "artifacts": [row],
        }))
        return path

    def test_only_exact_obligation_retry_artifacts_are_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rows = load_source_manifest(
                self.source_manifest(root), REPOSITORY, RUN_ID
            )
            self.assertEqual(rows, [NORMALIZED_ROW])
            partition = {
                **ROW,
                "id": ROW["id"] + 1,
                "name": "obligation-partition-nsf--mrefc-FY2024",
            }
            rows = load_source_manifest(
                self.source_manifest(root, partition), REPOSITORY, RUN_ID
            )
            self.assertEqual(rows, [{**partition, "deleteAfterPreserve": True}])
            unsafe = {**ROW, "name": "verify-reports"}
            with self.assertRaisesRegex(ManifestError, "not an obligation retry"):
                load_source_manifest(
                    self.source_manifest(root, unsafe), REPOSITORY, RUN_ID
                )

    def test_preservation_precedes_exact_deletion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rows = load_source_manifest(
                self.source_manifest(root), REPOSITORY, RUN_ID
            )
            api = FakeArtifacts()
            record = preserve(rows, REPOSITORY, RUN_ID, root / "saved", api)
            self.assertEqual(api.deleted, [])
            delete_preserved(record, api)
            self.assertEqual(api.deleted, [ROW["id"]])

    def test_preserve_only_artifact_is_not_deleted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            preserve_only = {**ROW, "deleteAfterPreserve": False}
            rows = load_source_manifest(
                self.source_manifest(root, preserve_only), REPOSITORY, RUN_ID
            )
            api = FakeArtifacts()
            record = preserve(rows, REPOSITORY, RUN_ID, root / "saved", api)
            delete_preserved(record, api)
            self.assertEqual(api.deleted, [])

    def test_changed_preserved_zip_blocks_every_delete(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rows = load_source_manifest(
                self.source_manifest(root), REPOSITORY, RUN_ID
            )
            api = FakeArtifacts()
            record = preserve(rows, REPOSITORY, RUN_ID, root / "saved", api)
            (record.parent / "artifacts" / f"{ROW['id']}.zip").write_bytes(b"changed")
            with self.assertRaisesRegex(ManifestError, "changed"):
                delete_preserved(record, api)
            self.assertEqual(api.deleted, [])

    def test_active_source_run_blocks_preservation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rows = load_source_manifest(
                self.source_manifest(root), REPOSITORY, RUN_ID
            )
            api = FakeArtifacts()
            api.run_metadata = lambda run_id: {"id": run_id, "status": "in_progress"}
            with self.assertRaisesRegex(ManifestError, "not terminal"):
                preserve(rows, REPOSITORY, RUN_ID, root / "saved", api)
            self.assertEqual(api.deleted, [])


if __name__ == "__main__":
    unittest.main()
