#!/usr/bin/env python3
"""Preserve and remove exact raw artifacts that block a failed-job rerun.

GitHub reruns execute the workflow definition from the original run. Older
obligation runs therefore reuse their unsuffixed raw artifact names. This
utility accepts an exact artifact manifest, downloads and hashes every ZIP,
and only then permits a second invocation to delete those same artifacts.
Normalized reconciliation artifacts are rejected by construction.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


API_ROOT = "https://api.github.com"
DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
RAW_NAME = re.compile(r"obligation-raw-[A-Za-z0-9._-]+\Z")


class ManifestError(ValueError):
    """The requested deletion scope is not exact or safe."""


class _SafeRedirect(urllib.request.HTTPRedirectHandler):
    """Do not forward the GitHub token to the signed artifact host."""

    def redirect_request(self, request, fp, code, msg, headers, new_url):
        redirected = super().redirect_request(
            request, fp, code, msg, headers, new_url
        )
        if redirected is None:
            return None
        old_host = urllib.parse.urlsplit(request.full_url).netloc
        new_host = urllib.parse.urlsplit(new_url).netloc
        if old_host != new_host:
            redirected.remove_header("Authorization")
        return redirected


class GitHubArtifacts:
    def __init__(self, repository: str, token: str):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise ManifestError("repository must be owner/name")
        if not token:
            raise ManifestError("GITHUB_TOKEN is required")
        self.repository = repository
        self.token = token
        self.opener = urllib.request.build_opener(_SafeRedirect())

    def _request(self, path: str, *, method: str = "GET"):
        request = urllib.request.Request(
            API_ROOT + path,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "science-funding-dashboard-artifact-recovery",
            },
        )
        try:
            return self.opener.open(request, timeout=120)
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"GitHub API {method} {path} failed: {error.code} {detail}"
            ) from error

    def metadata(self, artifact_id: int) -> dict:
        path = f"/repos/{self.repository}/actions/artifacts/{artifact_id}"
        with self._request(path) as response:
            return json.load(response)

    def run_metadata(self, run_id: int) -> dict:
        path = f"/repos/{self.repository}/actions/runs/{run_id}"
        with self._request(path) as response:
            return json.load(response)

    def download(self, artifact_id: int, target: Path) -> tuple[int, str]:
        path = (
            f"/repos/{self.repository}/actions/artifacts/{artifact_id}/zip"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_suffix(".part")
        digest = hashlib.sha256()
        size = 0
        with self._request(path) as response, partial.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
                digest.update(chunk)
                size += len(chunk)
        partial.replace(target)
        return size, f"sha256:{digest.hexdigest()}"

    def delete(self, artifact_id: int) -> None:
        path = f"/repos/{self.repository}/actions/artifacts/{artifact_id}"
        with self._request(path, method="DELETE") as response:
            if response.status != 204:
                raise RuntimeError(
                    f"artifact {artifact_id} delete returned {response.status}"
                )


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise ManifestError(f"cannot read JSON manifest {path}: {error}") from error
    if not isinstance(value, dict):
        raise ManifestError("manifest must be a JSON object")
    return value


def load_source_manifest(path: Path, repository: str, run_id: int) -> list[dict]:
    value = _read_json(path)
    if value.get("schemaVersion") != 1:
        raise ManifestError("manifest schemaVersion must be 1")
    if value.get("repository") != repository:
        raise ManifestError("manifest repository does not match invocation")
    if value.get("runId") != run_id:
        raise ManifestError("manifest runId does not match invocation")
    rows = value.get("artifacts")
    if not isinstance(rows, list) or not rows:
        raise ManifestError("manifest artifacts must be a nonempty list")
    if len(rows) > 200:
        raise ManifestError("manifest exceeds the 200-artifact safety limit")

    return validate_source_rows(rows)


def validate_source_rows(rows: list[dict]) -> list[dict]:
    ids: set[int] = set()
    names: set[str] = set()
    result = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"id", "name", "digest"}:
            raise ManifestError("each artifact must contain only id, name, digest")
        artifact_id = row["id"]
        name = row["name"]
        digest = row["digest"]
        if not isinstance(artifact_id, int) or artifact_id <= 0:
            raise ManifestError("artifact id must be a positive integer")
        if not isinstance(name, str) or not RAW_NAME.fullmatch(name):
            raise ManifestError(
                f"artifact {artifact_id} is not an obligation raw artifact"
            )
        if not isinstance(digest, str) or not DIGEST.fullmatch(digest):
            raise ManifestError(f"artifact {artifact_id} has an invalid digest")
        if artifact_id in ids or name in names:
            raise ManifestError("artifact ids and names must be unique")
        ids.add(artifact_id)
        names.add(name)
        result.append(row)
    return result


def validate_remote(row: dict, metadata: dict, run_id: int) -> None:
    workflow_run = metadata.get("workflow_run") or {}
    expected = {
        "id": row["id"],
        "name": row["name"],
        "digest": row["digest"],
        "runId": run_id,
    }
    observed = {
        "id": metadata.get("id"),
        "name": metadata.get("name"),
        "digest": metadata.get("digest"),
        "runId": workflow_run.get("id"),
    }
    if observed != expected:
        raise ManifestError(
            f"artifact {row['id']} metadata mismatch: expected {expected}, "
            f"observed {observed}"
        )
    if metadata.get("expired") is not False:
        raise ManifestError(f"artifact {row['id']} is expired")


def preserve(
    rows: list[dict], repository: str, run_id: int, output: Path, api
) -> Path:
    run = api.run_metadata(run_id)
    if run.get("id") != run_id or run.get("status") != "completed":
        raise ManifestError(f"workflow run {run_id} is not terminal")
    if output.exists():
        if any(output.iterdir()):
            raise ManifestError(f"preservation directory is not empty: {output}")
    else:
        output.mkdir(parents=True)

    preserved = []
    for row in rows:
        metadata = api.metadata(row["id"])
        validate_remote(row, metadata, run_id)
        relative = Path("artifacts") / f"{row['id']}.zip"
        size, digest = api.download(row["id"], output / relative)
        if digest != row["digest"]:
            raise ManifestError(
                f"downloaded artifact {row['id']} digest mismatch: {digest}"
            )
        preserved.append({**row, "file": str(relative), "size": size})

    record = {
        "schemaVersion": 1,
        "repository": repository,
        "runId": run_id,
        "artifacts": preserved,
    }
    record_path = output / "preservation.json"
    record_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    return record_path


def delete_preserved(record_path: Path, api) -> None:
    record = _read_json(record_path)
    repository = record.get("repository")
    run_id = record.get("runId")
    rows = record.get("artifacts")
    if record.get("schemaVersion") != 1 or not isinstance(rows, list) or not rows:
        raise ManifestError("invalid preservation record")
    root = record_path.parent.resolve()

    run = api.run_metadata(run_id)
    if run.get("id") != run_id or run.get("status") != "completed":
        raise ManifestError(f"workflow run {run_id} is not terminal")

    for row in rows:
        if not isinstance(row, dict) or set(row) != {
            "id", "name", "digest", "file", "size"
        }:
            raise ManifestError("invalid preserved artifact record")
        validate_source_rows(
            [{key: row[key] for key in ("id", "name", "digest")}]
        )
        artifact_file = (root / row["file"]).resolve()
        if root not in artifact_file.parents:
            raise ManifestError("preserved artifact path escapes its directory")
        digest = hashlib.sha256(artifact_file.read_bytes()).hexdigest()
        if f"sha256:{digest}" != row["digest"]:
            raise ManifestError(f"preserved artifact {row['id']} changed")
        if artifact_file.stat().st_size != row["size"]:
            raise ManifestError(f"preserved artifact {row['id']} size changed")
        metadata = api.metadata(row["id"])
        validate_remote(row, metadata, run_id)

    # No remote mutation occurs until every local ZIP and every remote row has
    # passed the complete preflight above.
    for row in rows:
        api.delete(row["id"])
        print(f"Deleted exact preserved artifact {row['id']} {row['name']}")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("command", choices=("preserve", "delete"))
    result.add_argument("--repository", required=True)
    result.add_argument("--run-id", required=True, type=int)
    result.add_argument("--manifest", required=True, type=Path)
    result.add_argument("--output", type=Path)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    token = os.environ.get("GITHUB_TOKEN", "")
    api = GitHubArtifacts(args.repository, token)
    if args.command == "preserve":
        if args.output is None:
            raise ManifestError("--output is required for preserve")
        rows = load_source_manifest(args.manifest, args.repository, args.run_id)
        record = preserve(rows, args.repository, args.run_id, args.output, api)
        print(f"Preserved {len(rows)} exact artifacts in {record}")
    else:
        if args.output is not None:
            raise ManifestError("--output is not accepted for delete")
        record = _read_json(args.manifest)
        if record.get("repository") != args.repository:
            raise ManifestError("preservation repository does not match invocation")
        if record.get("runId") != args.run_id:
            raise ManifestError("preservation runId does not match invocation")
        delete_preserved(args.manifest, api)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ManifestError, RuntimeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(2)
