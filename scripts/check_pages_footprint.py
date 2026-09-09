#!/usr/bin/env python3
"""Warn or stop before a GitHub Pages artifact approaches its 1 GB limit."""

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from scripts.assemble_pages_site import assembled_content_contract  # noqa: E402


PAGES_LIMIT_BYTES = 1_000_000_000
PAGES_WARNING_BYTES = 850_000_000
PAGES_STOP_BYTES = 950_000_000


def measure_tree(root):
    root = Path(root)
    if not root.is_dir():
        raise ValueError(f"Pages site root is not a directory: {root}")
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Pages artifact must not contain symlinks: {path}")
        if path.is_file():
            files.append(path)
    return {
        "fileCount": len(files),
        "totalBytes": sum(path.stat().st_size for path in files),
    }


def classify(total_bytes, warning_bytes=PAGES_WARNING_BYTES,
             stop_bytes=PAGES_STOP_BYTES):
    if not 0 < warning_bytes < stop_bytes <= PAGES_LIMIT_BYTES:
        raise ValueError(
            "thresholds must satisfy 0 < warning < stop <= 1,000,000,000"
        )
    if total_bytes >= stop_bytes:
        return "stop"
    if total_bytes >= warning_bytes:
        return "warning"
    return "ok"


def report(root, warning_bytes=PAGES_WARNING_BYTES,
           stop_bytes=PAGES_STOP_BYTES, repo=REPO):
    result = measure_tree(root)
    result.update({
        "status": classify(result["totalBytes"], warning_bytes, stop_bytes),
        "warningThresholdBytes": warning_bytes,
        "stopThresholdBytes": stop_bytes,
        "pagesLimitBytes": PAGES_LIMIT_BYTES,
        "headroomBytes": PAGES_LIMIT_BYTES - result["totalBytes"],
        "linkIntegrity": assembled_content_contract(repo, root),
    })
    return result


def write_github_summary(result, message):
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    link = result["linkIntegrity"]
    with open(summary_path, "a", encoding="utf-8") as handle:
        handle.write("## GitHub Pages artifact footprint\n\n")
        handle.write(f"- **Status:** {result['status']}\n")
        handle.write(f"- **Assembled artifact:** {result['totalBytes']} bytes ")
        handle.write(f"across {result['fileCount']} files\n")
        handle.write(f"- **Warning / stop / limit:** ")
        handle.write(f"{result['warningThresholdBytes']} / ")
        handle.write(f"{result['stopThresholdBytes']} / ")
        handle.write(f"{result['pagesLimitBytes']} bytes\n")
        handle.write(f"- **NSF award CSVs retained:** ")
        handle.write(f"{link['nsfAwardCsvArtifactCount']} / ")
        handle.write(f"{link['nsfAwardCsvSourceCount']}\n")
        handle.write(f"- **Obligation event archives in Pages:** ")
        handle.write(f"{link['obligationEventArchiveArtifactCount']} / ")
        handle.write(f"{link['obligationEventArchiveSourceCount']}\n\n")
        handle.write(f"`{message}`\n\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-root", type=Path, default=Path("_site"))
    parser.add_argument("--repo", type=Path, default=REPO)
    parser.add_argument("--warning-bytes", type=int, default=PAGES_WARNING_BYTES)
    parser.add_argument("--stop-bytes", type=int, default=PAGES_STOP_BYTES)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args(argv)

    result = report(
        args.site_root, args.warning_bytes, args.stop_bytes, repo=args.repo
    )
    if args.json:
        args.json.write_text(json.dumps(result, indent=2) + "\n")

    message = (
        f"GitHub Pages footprint {result['status']}: "
        f"{result['totalBytes']} bytes across {result['fileCount']} files; "
        f"warning={result['warningThresholdBytes']}, "
        f"stop={result['stopThresholdBytes']}, "
        f"limit={result['pagesLimitBytes']}, "
        f"headroom={result['headroomBytes']}"
    )
    print(message)
    if os.environ.get("GITHUB_ACTIONS") == "true":
        if result["status"] == "warning":
            print(f"::warning title=GitHub Pages footprint::{message}")
        elif result["status"] == "stop":
            print(f"::error title=GitHub Pages footprint::{message}")
        write_github_summary(result, message)
    return 1 if result["status"] == "stop" else 0


if __name__ == "__main__":
    raise SystemExit(main())
