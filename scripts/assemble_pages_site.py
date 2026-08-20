#!/usr/bin/env python3
"""Assemble the exact runtime-only GitHub Pages artifact.

The browser consumes dashboard/provenance JSON, not the normalized obligation
event archives.  Keep those ``*.csv.gz`` shards in Git as durable audit input,
but do not duplicate them into the Pages artifact.
"""

import argparse
import shutil
from pathlib import Path
from urllib.parse import unquote, urlparse


REPO = Path(__file__).resolve().parent.parent


def excluded_from_pages(relative_path):
    """Return whether a repository-relative path is an audit event archive."""
    parts = Path(relative_path).parts
    return (
        len(parts) >= 4
        and parts[0] == "data"
        and parts[1] == "obligations"
        and parts[-2] == "events"
        and parts[-1].endswith(".csv.gz")
    )


def iter_pages_source_files(repo=REPO):
    """Yield ``(source, destination-relative)`` runtime files deterministically."""
    repo = Path(repo)
    index = repo / "site" / "index.html"
    data = repo / "data"
    if not index.is_file():
        raise ValueError(f"missing Pages entry point: {index}")
    if not data.is_dir():
        raise ValueError(f"missing Pages data tree: {data}")

    yield index, Path("index.html")
    for source in sorted(data.rglob("*")):
        if source.is_symlink():
            raise ValueError(f"Pages source must not contain symlinks: {source}")
        if not source.is_file():
            continue
        relative = source.relative_to(repo)
        if excluded_from_pages(relative):
            continue
        yield source, relative


def pages_source_summary(repo=REPO):
    files = list(iter_pages_source_files(repo))
    return {
        "fileCount": len(files),
        "totalBytes": sum(source.stat().st_size for source, _ in files),
    }


def assembled_content_contract(repo, site_root):
    """Prove the runtime artifact retained every Pages-hosted download.

    NSF award CSVs are intentional Pages-relative downloads.  Normalized
    obligation event CSV archives are durable Git evidence and must never be
    copied into the Pages tree.
    """
    repo = Path(repo)
    site_root = Path(site_root)
    nsf_sources = sorted((repo / "data" / "nsf").glob("**/awards.csv"))
    missing_nsf = [
        str(source.relative_to(repo))
        for source in nsf_sources
        if not (site_root / source.relative_to(repo)).is_file()
    ]
    if missing_nsf:
        raise ValueError(
            "assembled Pages artifact omitted NSF award CSV downloads: "
            + ", ".join(missing_nsf[:5])
        )

    obligation_sources = sorted(
        (repo / "data" / "obligations").glob("**/events/*.csv.gz")
    )
    leaked_obligation = [
        str(source.relative_to(repo))
        for source in obligation_sources
        if (site_root / source.relative_to(repo)).exists()
    ]
    if leaked_obligation:
        raise ValueError(
            "assembled Pages artifact contains excluded obligation archives: "
            + ", ".join(leaked_obligation[:5])
        )
    return {
        "nsfAwardCsvSourceCount": len(nsf_sources),
        "nsfAwardCsvArtifactCount": len(nsf_sources) - len(missing_nsf),
        "obligationEventArchiveSourceCount": len(obligation_sources),
        "obligationEventArchiveArtifactCount": len(leaked_obligation),
    }


def rendered_link_problems(hrefs, site_root):
    """Return broken or publication-policy-violating rendered links."""
    site_root = Path(site_root).resolve()
    problems = []
    for href in hrefs:
        parsed = urlparse(href)
        path = unquote(parsed.path)
        is_obligation_archive = (
            path.endswith(".csv.gz")
            and "/data/obligations/" in "/" + path.lstrip("/")
            and "/events/" in "/" + path.lstrip("/")
        )
        if parsed.scheme in {"http", "https"}:
            if is_obligation_archive and parsed.hostname != "github.com":
                problems.append(
                    f"obligation event archive is not linked through github.com: {href}"
                )
            continue
        if parsed.scheme or parsed.netloc:
            problems.append(f"unsupported public link scheme: {href}")
            continue
        if "localhost" in href or href.startswith("file:"):
            problems.append(f"non-public link remains: {href}")
            continue
        if is_obligation_archive:
            problems.append(
                f"obligation event archive is Pages-relative instead of github.com: {href}"
            )
            continue
        relative = Path(path.lstrip("/")) if path not in {"", "/"} else Path("index.html")
        target = (site_root / relative).resolve()
        try:
            target.relative_to(site_root)
        except ValueError:
            problems.append(f"relative link escapes assembled artifact: {href}")
            continue
        if not target.is_file():
            problems.append(f"relative link missing from assembled artifact: {href}")
    return problems


def assemble_pages_site(repo=REPO, output=None):
    repo = Path(repo)
    output = Path(output or (repo / "_site"))
    if output.exists():
        raise ValueError(f"Pages output already exists; refusing stale merge: {output}")

    copied_files = 0
    copied_bytes = 0
    try:
        output.mkdir(parents=True)
        for source, relative in iter_pages_source_files(repo):
            target = output / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            copied_files += 1
            copied_bytes += source.stat().st_size
    except Exception:
        shutil.rmtree(output, ignore_errors=True)
        raise
    contract = assembled_content_contract(repo, output)
    return {"fileCount": copied_files, "totalBytes": copied_bytes, **contract}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=REPO)
    parser.add_argument("--output", type=Path, default=Path("_site"))
    args = parser.parse_args(argv)
    summary = assemble_pages_site(args.repo, args.output)
    print(
        "Pages site assembled: "
        f"{summary['fileCount']} files, {summary['totalBytes']} bytes; "
        "obligation event CSV archives retained in Git only"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
