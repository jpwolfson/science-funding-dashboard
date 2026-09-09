#!/usr/bin/env python3
"""Fail-closed reuse of accepted evidence for one exact workflow retry.

The recovery manifest is inert outside the named workflow run, retry attempt,
branch, event, and original head SHA. Evidence is fetched from an immutable
commit on the dedicated operational branch and verified before any bytes are
used. This prevents a failed-job retry from resubmitting source requests that
already completed successfully in the original attempt.
"""

from __future__ import annotations

import copy
import hashlib
import io
import json
import os
import re
import subprocess
import zipfile
from pathlib import Path
from typing import Callable

from adapters.obligation_common import baseline_pin_problems
from adapters.usaspending_obligations import archive_rows


MANIFEST_PATH = Path("reference/obligation_retry_recovery.json")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
GIT_SHA = re.compile(r"[0-9a-f]{40}\Z")
BRANCH = re.compile(r"[A-Za-z0-9._/-]+\Z")
ACCOUNT = re.compile(r"[a-z0-9._-]+/[a-z0-9._-]+\Z")
RAW_ARCHIVE = re.compile(
    r"[A-Za-z0-9._-]+-FY[0-9]{4}P[0-9]{2}-"
    r"(?:object_class_program_activity|award_financial)-[0-9a-f]{12}\.zip\Z"
)


class RecoveryError(ValueError):
    """Recovery evidence or its activation scope failed validation."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _object(value, label: str) -> dict:
    if not isinstance(value, dict):
        raise RecoveryError(f"{label} must be an object")
    return value


def _list(value, label: str) -> list:
    if not isinstance(value, list):
        raise RecoveryError(f"{label} must be a list")
    return value


def _exact_keys(value: dict, keys: set[str], label: str) -> None:
    if set(value) != keys:
        raise RecoveryError(f"{label} has unexpected fields")


def _safe_member(name: object, label: str) -> str:
    if (
        not isinstance(name, str)
        or not name
        or Path(name).name != name
        or name in {".", ".."}
    ):
        raise RecoveryError(f"{label} must be a basename")
    return name


def _positive_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise RecoveryError(f"{label} must be a positive integer")
    return value


def _digest(value: object, label: str) -> str:
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        raise RecoveryError(f"{label} must be a lowercase SHA-256")
    return value


def _commit(value: object, label: str) -> str:
    if not isinstance(value, str) or not GIT_SHA.fullmatch(value):
        raise RecoveryError(f"{label} must be a lowercase 40-character Git SHA")
    return value


def _submission_type(value: object, label: str) -> str:
    if value not in {"object_class_program_activity", "award_financial"}:
        raise RecoveryError(f"{label} is invalid")
    return str(value)


class RetryRecovery:
    """Read and verify one immutable recovery bundle lazily."""

    def __init__(
        self,
        repo: Path,
        manifest: dict,
        blob_reader: Callable[[str], bytes] | None = None,
    ):
        self.repo = Path(repo)
        self.manifest = manifest
        self._blob_reader = blob_reader
        self._evidence_ready = False
        self._outer_cache: dict[int, bytes] = {}
        self._preserved: dict[int, dict] = {}
        self._raw: dict[tuple[str, int, int, str], tuple[dict, dict]] = {}
        self._resumes: dict[tuple[str, int, int, str], tuple[dict, dict]] = {}
        self._partitions: dict[tuple[str, int], dict] = {}
        self._pins: dict[tuple[str, int], dict] = {}
        self._validate_manifest()

    def _validate_manifest(self) -> None:
        expected = {
            "schemaVersion", "repository", "workflowRunId", "sourceAttempt",
            "minimumRetryAttempt", "sourceHeadSha", "sourceEvent",
            "headBranch", "evidenceBranch", "evidenceCommit",
            "preservationPath", "preservedArtifacts", "rawEvidence",
            "normalizedPartitions", "baselinePins",
        }
        _exact_keys(self.manifest, expected, "recovery manifest")
        if self.manifest.get("schemaVersion") != 1:
            raise RecoveryError("recovery manifest must be schema v1")
        repository = self.manifest.get("repository")
        if not isinstance(repository, str) or not re.fullmatch(
            r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository
        ):
            raise RecoveryError("recovery repository must be owner/name")
        _positive_int(self.manifest.get("workflowRunId"), "workflowRunId")
        _positive_int(self.manifest.get("sourceAttempt"), "sourceAttempt")
        _positive_int(
            self.manifest.get("minimumRetryAttempt"), "minimumRetryAttempt"
        )
        if self.manifest["minimumRetryAttempt"] <= self.manifest["sourceAttempt"]:
            raise RecoveryError("minimumRetryAttempt must follow sourceAttempt")
        _commit(self.manifest.get("sourceHeadSha"), "sourceHeadSha")
        _commit(self.manifest.get("evidenceCommit"), "evidenceCommit")
        if self.manifest.get("sourceEvent") != "schedule":
            raise RecoveryError("recovery sourceEvent must be schedule")
        for field in ("headBranch", "evidenceBranch"):
            value = self.manifest.get(field)
            if not isinstance(value, str) or not BRANCH.fullmatch(value):
                raise RecoveryError(f"invalid {field}")
        path = Path(str(self.manifest.get("preservationPath", "")))
        if path.is_absolute() or ".." in path.parts or not path.parts:
            raise RecoveryError("invalid preservationPath")

        for index, value in enumerate(
            _list(self.manifest.get("preservedArtifacts"), "preservedArtifacts")
        ):
            row = _object(value, f"preservedArtifacts[{index}]")
            _exact_keys(row, {
                "artifactId", "artifactName", "artifactDigest", "artifactSize",
                "deleteAfterPreserve",
            }, f"preservedArtifacts[{index}]")
            artifact_id = _positive_int(row.get("artifactId"), "artifactId")
            if artifact_id in self._preserved:
                raise RecoveryError("duplicate preserved artifact ID")
            name = row.get("artifactName")
            if not isinstance(name, str) or not name.startswith("obligation-"):
                raise RecoveryError("invalid preserved artifact name")
            if any(value["artifactName"] == name for value in self._preserved.values()):
                raise RecoveryError("duplicate preserved artifact name")
            artifact_digest = row.get("artifactDigest")
            if not isinstance(artifact_digest, str) or not artifact_digest.startswith(
                "sha256:"
            ):
                raise RecoveryError("invalid preserved artifact digest")
            _digest(artifact_digest.removeprefix("sha256:"), "artifactDigest")
            _positive_int(row.get("artifactSize"), "artifactSize")
            if not isinstance(row.get("deleteAfterPreserve"), bool):
                raise RecoveryError("deleteAfterPreserve must be boolean")
            self._preserved[artifact_id] = row

        for index, value in enumerate(
            _list(self.manifest.get("rawEvidence"), "rawEvidence")
        ):
            row = _object(value, f"rawEvidence[{index}]")
            _exact_keys(row, {
                "artifactId", "accountPath", "federalAccount",
                "sourceAccountId", "fiscalYear", "rawArchives",
                "resumeRequests",
            }, f"rawEvidence[{index}]")
            artifact_id = _positive_int(row.get("artifactId"), "artifactId")
            if artifact_id not in self._preserved:
                raise RecoveryError("raw evidence references an unpreserved artifact")
            account = row.get("accountPath")
            if not isinstance(account, str) or not ACCOUNT.fullmatch(account):
                raise RecoveryError("invalid raw evidence accountPath")
            federal = row.get("federalAccount")
            if not isinstance(federal, str) or not re.fullmatch(
                r"[0-9]{3}-[0-9]{4}", federal
            ):
                raise RecoveryError("invalid raw evidence federalAccount")
            source_id = row.get("sourceAccountId")
            if not isinstance(source_id, str) or not source_id.isdigit():
                raise RecoveryError("invalid sourceAccountId")
            fy = _positive_int(row.get("fiscalYear"), "fiscalYear")
            expected_artifact = (
                f"obligation-raw-{account.replace('/', '--')}-FY{fy}-"
                f"attempt{self.manifest['sourceAttempt']}"
            )
            if self._preserved[artifact_id]["artifactName"] != expected_artifact:
                raise RecoveryError("raw evidence artifact name/scope mismatch")
            for archive_index, archive_value in enumerate(
                _list(row.get("rawArchives"), "rawArchives")
            ):
                archive = _object(archive_value, "raw archive")
                _exact_keys(archive, {
                    "memberName", "sha256", "size", "period",
                    "submissionType", "memberRowCounts", "parsedRowCount",
                }, f"raw archive {archive_index}")
                name = _safe_member(archive.get("memberName"), "raw memberName")
                if not RAW_ARCHIVE.fullmatch(name):
                    raise RecoveryError("invalid raw archive memberName")
                digest = _digest(archive.get("sha256"), "raw archive sha256")
                if name.rsplit("-", 1)[-1].removesuffix(".zip") != digest[:12]:
                    raise RecoveryError("raw archive name/hash mismatch")
                _positive_int(archive.get("size"), "raw archive size")
                period = _positive_int(archive.get("period"), "raw period")
                if period not in range(2, 13):
                    raise RecoveryError("raw period is outside P02-P12")
                kind = _submission_type(
                    archive.get("submissionType"), "raw submissionType"
                )
                expected_name = (
                    f"{account.replace('/', '--')}-FY{fy}P{period:02}-"
                    f"{kind}-{digest[:12]}.zip"
                )
                if name != expected_name:
                    raise RecoveryError("raw archive name/scope mismatch")
                counts = _object(
                    archive.get("memberRowCounts"), "memberRowCounts"
                )
                if not counts or any(
                    not isinstance(key, str)
                    or not isinstance(count, int)
                    or isinstance(count, bool)
                    or count < 0
                    for key, count in counts.items()
                ):
                    raise RecoveryError("invalid memberRowCounts")
                parsed = archive.get("parsedRowCount")
                if (
                    not isinstance(parsed, int)
                    or isinstance(parsed, bool)
                    or parsed < 0
                    or sum(counts.values()) != parsed
                ):
                    raise RecoveryError("raw parsed row count does not reconcile")
                key = (account, fy, period, kind)
                if key in self._raw:
                    raise RecoveryError(f"duplicate raw recovery key {key}")
                self._raw[key] = (row, archive)
            for resume_index, resume_value in enumerate(
                _list(row.get("resumeRequests"), "resumeRequests")
            ):
                resume = _object(resume_value, "resume request")
                _exact_keys(resume, {
                    "memberName", "sha256", "size", "fiscalYear", "period",
                    "submissionType",
                }, f"resume request {resume_index}")
                _safe_member(resume.get("memberName"), "resume memberName")
                _digest(resume.get("sha256"), "resume sha256")
                _positive_int(resume.get("size"), "resume size")
                resume_fy = _positive_int(
                    resume.get("fiscalYear"), "resume fiscalYear"
                )
                period = _positive_int(resume.get("period"), "resume period")
                if period not in range(2, 13):
                    raise RecoveryError("resume period is outside P02-P12")
                kind = _submission_type(
                    resume.get("submissionType"), "resume submissionType"
                )
                expected_name = (
                    "obligation-download-resume-"
                    f"{account.replace('/', '--')}-FY{resume_fy}P{period:02}-"
                    f"{kind}.json"
                )
                if resume["memberName"] != expected_name:
                    raise RecoveryError("resume request name/scope mismatch")
                key = (account, resume_fy, period, kind)
                if key in self._resumes or key in self._raw:
                    raise RecoveryError(f"duplicate recovered request key {key}")
                self._resumes[key] = (row, resume)

        for index, value in enumerate(_list(
            self.manifest.get("normalizedPartitions"), "normalizedPartitions"
        )):
            row = _object(value, f"normalizedPartitions[{index}]")
            _exact_keys(row, {
                "artifactId", "accountPath", "federalAccount", "fiscalYear",
                "files",
            }, f"normalizedPartitions[{index}]")
            artifact_id = _positive_int(row.get("artifactId"), "artifactId")
            if artifact_id not in self._preserved:
                raise RecoveryError(
                    "normalized partition references an unpreserved artifact"
                )
            account = row.get("accountPath")
            fy = _positive_int(row.get("fiscalYear"), "fiscalYear")
            if not isinstance(account, str) or not ACCOUNT.fullmatch(account):
                raise RecoveryError("invalid normalized accountPath")
            expected_artifact = (
                f"obligation-partition-{account.replace('/', '--')}-FY{fy}"
            )
            if self._preserved[artifact_id]["artifactName"] != expected_artifact:
                raise RecoveryError("normalized artifact name/scope mismatch")
            files = _list(row.get("files"), "normalized files")
            if len(files) != 3:
                raise RecoveryError("normalized partition must contain three files")
            names = set()
            for file_index, file_value in enumerate(files):
                file_row = _object(file_value, "normalized file")
                _exact_keys(
                    file_row, {"memberName", "sha256", "size"},
                    f"normalized file {file_index}",
                )
                names.add(_safe_member(
                    file_row.get("memberName"), "normalized memberName"
                ))
                _digest(file_row.get("sha256"), "normalized sha256")
                _positive_int(file_row.get("size"), "normalized size")
            if names != {f"FY{fy}.csv.gz", f"FY{fy}.provenance.json", "partition.json"}:
                raise RecoveryError("normalized partition file set is incomplete")
            key = (account, fy)
            if key in self._partitions:
                raise RecoveryError(f"duplicate normalized partition {key}")
            self._partitions[key] = row

        for index, value in enumerate(
            _list(self.manifest.get("baselinePins"), "baselinePins")
        ):
            row = _object(value, f"baselinePins[{index}]")
            _exact_keys(
                row, {"accountPath", "fiscalYear", "pin"},
                f"baselinePins[{index}]",
            )
            account = row.get("accountPath")
            fy = _positive_int(row.get("fiscalYear"), "baseline fiscalYear")
            if not isinstance(account, str) or not ACCOUNT.fullmatch(account):
                raise RecoveryError("invalid baseline accountPath")
            pin = _object(row.get("pin"), "baseline pin")
            problems = baseline_pin_problems(pin)
            if problems:
                raise RecoveryError("invalid recovery baseline pin: " + "; ".join(problems))
            key = (account, fy)
            if key in self._pins:
                raise RecoveryError(f"duplicate recovery baseline pin {key}")
            self._pins[key] = copy.deepcopy(pin)

    def _git_blob(self, path: str) -> bytes:
        if self._blob_reader is not None:
            return self._blob_reader(path)
        completed = subprocess.run(
            ["git", "show", f"{self.manifest['evidenceCommit']}:{path}"],
            cwd=self.repo,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if completed.returncode:
            detail = completed.stderr.decode("utf-8", errors="replace").strip()
            raise RecoveryError(f"cannot read recovery evidence {path}: {detail}")
        return completed.stdout

    def _ensure_evidence(self) -> None:
        if self._evidence_ready:
            return
        if self._blob_reader is None:
            completed = subprocess.run(
                [
                    "git", "fetch", "--no-tags", "--depth=1", "origin",
                    f"refs/heads/{self.manifest['evidenceBranch']}",
                ],
                cwd=self.repo,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            if completed.returncode:
                detail = completed.stderr.decode(
                    "utf-8", errors="replace"
                ).strip()
                raise RecoveryError(f"cannot fetch recovery evidence: {detail}")
            fetched = subprocess.check_output(
                ["git", "rev-parse", "FETCH_HEAD"], cwd=self.repo, text=True
            ).strip()
            if fetched != self.manifest["evidenceCommit"]:
                raise RecoveryError(
                    f"evidence branch moved: expected {self.manifest['evidenceCommit']}, "
                    f"observed {fetched}"
                )
        record_bytes = self._git_blob(self.manifest["preservationPath"])
        try:
            record = json.loads(record_bytes)
        except json.JSONDecodeError as error:
            raise RecoveryError("invalid preservation record JSON") from error
        expected = {
            "schemaVersion": 1,
            "repository": self.manifest["repository"],
            "runId": self.manifest["workflowRunId"],
            "artifacts": [
                {
                    "id": row["artifactId"],
                    "name": row["artifactName"],
                    "digest": row["artifactDigest"],
                    "deleteAfterPreserve": row["deleteAfterPreserve"],
                    "file": f"artifacts/{row['artifactId']}.zip",
                    "size": row["artifactSize"],
                }
                for row in self.manifest["preservedArtifacts"]
            ],
        }
        if record != expected:
            raise RecoveryError("preservation record differs from recovery manifest")
        self._evidence_ready = True

    def _outer(self, artifact_id: int) -> bytes:
        self._ensure_evidence()
        if artifact_id in self._outer_cache:
            return self._outer_cache[artifact_id]
        row = self._preserved[artifact_id]
        root = Path(self.manifest["preservationPath"]).parent
        path = str(root / "artifacts" / f"{artifact_id}.zip")
        payload = self._git_blob(path)
        if len(payload) != row["artifactSize"]:
            raise RecoveryError(f"artifact {artifact_id} evidence size mismatch")
        if "sha256:" + _sha256(payload) != row["artifactDigest"]:
            raise RecoveryError(f"artifact {artifact_id} evidence digest mismatch")
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            names = archive.namelist()
            if archive.testzip() is not None:
                raise RecoveryError(f"artifact {artifact_id} evidence failed CRC")
            if len(names) != len(set(names)):
                raise RecoveryError(f"artifact {artifact_id} has duplicate members")
        self._outer_cache[artifact_id] = payload
        return payload

    def _member(self, artifact_id: int, expected: dict) -> bytes:
        outer = self._outer(artifact_id)
        name = expected["memberName"]
        with zipfile.ZipFile(io.BytesIO(outer)) as archive:
            try:
                payload = archive.read(name)
            except KeyError as error:
                raise RecoveryError(
                    f"artifact {artifact_id} is missing {name}"
                ) from error
        if len(payload) != expected["size"]:
            raise RecoveryError(f"artifact member {name} size mismatch")
        if _sha256(payload) != expected["sha256"]:
            raise RecoveryError(f"artifact member {name} digest mismatch")
        return payload

    def recover_raw(
        self,
        account: dict,
        account_id: str,
        fy: int,
        period: int,
        kind: str,
        columns: list[str],
        raw_archive_dir: Path | str | None,
    ):
        match = self._raw.get((account["path"], fy, period, kind))
        if match is None:
            return None
        evidence, archive = match
        if (
            evidence["federalAccount"] != account["federalAccount"]
            or evidence["sourceAccountId"] != str(account_id)
        ):
            raise RecoveryError("recovered raw account scope mismatch")
        payload = self._member(evidence["artifactId"], archive)
        members = archive_rows(payload)
        counts = {name: len(rows) for name, rows in sorted(members.items())}
        if counts != archive["memberRowCounts"]:
            raise RecoveryError(
                f"recovered FY{fy} P{period:02} {kind} row counts changed"
            )
        if sum(counts.values()) != archive["parsedRowCount"]:
            raise RecoveryError("recovered raw parsed row count changed")
        if raw_archive_dir:
            target = Path(raw_archive_dir) / archive["memberName"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
        request_scope = {
            "account_level": "federal_account",
            "file_format": "csv",
            "filters": {
                "fy": fy,
                "period": period,
                "submission_types": [kind],
                "federal_account": str(account_id),
            },
            "columns": list(columns),
        }
        audit = {
            "submissionType": kind,
            "requestScope": request_scope,
            "acceptedRequestScope": None,
            "status": "finished",
            "statusRowCount": archive["parsedRowCount"],
            "parsedRowCount": archive["parsedRowCount"],
            "memberRowCounts": counts,
            "archiveSha256": archive["sha256"],
            "rawArtifactFile": archive["memberName"],
            "recoveryEvidence": {
                "workflowRunId": self.manifest["workflowRunId"],
                "sourceAttempt": self.manifest["sourceAttempt"],
                "artifactId": evidence["artifactId"],
                "artifactDigest": self._preserved[
                    evidence["artifactId"]
                ]["artifactDigest"],
                "evidenceCommit": self.manifest["evidenceCommit"],
            },
        }
        print(
            f"reused accepted FY{fy} P{period:02} {kind}: "
            f"{archive['parsedRowCount']:,} rows",
            flush=True,
        )
        return members, audit

    def resume_result(
        self,
        account: dict,
        account_id: str,
        fy: int,
        period: int,
        kind: str,
    ) -> dict | None:
        match = self._resumes.get((account["path"], fy, period, kind))
        if match is None:
            return None
        evidence, resume = match
        if (
            evidence["federalAccount"] != account["federalAccount"]
            or evidence["sourceAccountId"] != str(account_id)
        ):
            raise RecoveryError("resume evidence account scope mismatch")
        payload = self._member(evidence["artifactId"], resume)
        try:
            value = json.loads(payload)
        except json.JSONDecodeError as error:
            raise RecoveryError("resume evidence is invalid JSON") from error
        requests = value.get("requests") if isinstance(value, dict) else None
        if value.get("schemaVersion") != 1 or not isinstance(requests, list):
            raise RecoveryError("resume evidence has an invalid schema")
        matches = [row for row in requests if (
            row.get("account") == account["path"]
            and row.get("fiscalYear") == fy
            and row.get("period") == period
            and row.get("submissionType") == kind
        )]
        if len(matches) != 1 or not isinstance(matches[0].get("result"), dict):
            raise RecoveryError("resume evidence request scope mismatch")
        return copy.deepcopy(matches[0]["result"])

    def restore_partition(
        self,
        account: dict,
        years: list[int],
        destination: Path | str | None,
    ) -> bool:
        matches = [
            self._partitions[(account["path"], fy)]
            for fy in years
            if (account["path"], fy) in self._partitions
        ]
        if not matches:
            return False
        if len(matches) != len(years) or len(matches) != 1:
            raise RecoveryError("normalized recovery partition scope is incomplete")
        if destination is None:
            raise RecoveryError("normalized recovery requires partition output")
        row = matches[0]
        if row["federalAccount"] != account["federalAccount"]:
            raise RecoveryError("normalized recovery federal account mismatch")
        target = Path(destination)
        if target.exists() and any(target.iterdir()):
            raise RecoveryError(f"normalized recovery target is not empty: {target}")
        target.mkdir(parents=True, exist_ok=True)
        for file_row in row["files"]:
            payload = self._member(row["artifactId"], file_row)
            (target / file_row["memberName"]).write_bytes(payload)
        descriptor = json.loads((target / "partition.json").read_text())
        fy = row["fiscalYear"]
        if (
            descriptor.get("schemaVersion") != 2
            or descriptor.get("accountPath") != account["path"]
            or descriptor.get("federalAccount") != account["federalAccount"]
            or descriptor.get("fiscalYears") != [fy]
            or {value.get("name"): value.get("sha256")
                for value in descriptor.get("files", [])}
            != {value["memberName"]: value["sha256"]
                for value in row["files"]
                if value["memberName"] != "partition.json"}
        ):
            raise RecoveryError("normalized partition descriptor mismatch")
        provenance = json.loads(
            (target / f"FY{fy}.provenance.json").read_text()
        )
        if (
            provenance.get("schemaVersion") != 2
            or provenance.get("collectionStatus") != "accepted"
            or provenance.get("accountPath") != account["path"]
            or provenance.get("federalAccount") != account["federalAccount"]
            or provenance.get("fiscalYear") != fy
        ):
            raise RecoveryError("normalized partition provenance mismatch")
        print(
            f"reused accepted normalized partition for {account['path']} FY{fy}",
            flush=True,
        )
        return True

    def baseline_pin(self, account_path: str, fy: int) -> dict | None:
        value = self._pins.get((account_path, fy))
        return copy.deepcopy(value) if value is not None else None


def load_retry_recovery(
    repo: Path,
    environ: dict[str, str] | None = None,
    blob_reader: Callable[[str], bytes] | None = None,
) -> RetryRecovery | None:
    """Return the exact recovery only inside its named failed-job retry."""
    repo = Path(repo)
    path = repo / MANIFEST_PATH
    if not path.exists():
        return None
    try:
        manifest = json.loads(path.read_text())
    except json.JSONDecodeError as error:
        raise RecoveryError("invalid recovery manifest JSON") from error
    manifest = _object(manifest, "recovery manifest")
    env = os.environ if environ is None else environ
    try:
        run_id = int(env.get("GITHUB_RUN_ID", "0"))
        attempt = int(env.get("GITHUB_RUN_ATTEMPT", "0"))
    except ValueError as error:
        raise RecoveryError("workflow run ID and attempt must be integers") from error
    if run_id != manifest.get("workflowRunId"):
        return None
    if attempt < int(manifest.get("minimumRetryAttempt", 0)):
        return None
    expected = {
        "GITHUB_REPOSITORY": manifest.get("repository"),
        "GITHUB_REF_NAME": manifest.get("headBranch"),
        "GITHUB_EVENT_NAME": manifest.get("sourceEvent"),
        "GITHUB_SHA": manifest.get("sourceHeadSha"),
    }
    observed = {key: env.get(key) for key in expected}
    if observed != expected:
        raise RecoveryError(
            f"workflow retry activation mismatch: expected {expected}, "
            f"observed {observed}"
        )
    return RetryRecovery(repo, manifest, blob_reader=blob_reader)
