#!/usr/bin/env python3
"""scripts/verify.py -- the single verification entry point, four tiers.

GOVERNING PRINCIPLE (owner directive): the verification regime is uniform
across agencies. The verifier contains universal invariants only; every
agency-specific fact is a declared parameter in that account's registry
entry (config/obligation_accounts.json) or baseline file
(reference/*_obligation_baseline.json) -- one schema is the entire
specialization surface. No agency-conditional code paths in any verifier.
If an account needs something the schema cannot express, that is a schema
extension landed once by the coordinator, never a code fork.

See docs/verification-regime.md for the full contract: the tier table, the
JSON result schema, the specialization schema, and the schema-extension
rule.

Usage:
    python scripts/verify.py [--tier registry|fast|rendered|screens]
                              [--account <path>] [--json <path>]
                              [--out <dir>] [--chrome <executable>]

Exit codes: 0 pass, 1 fail (registry/fast/rendered only -- screens never
fails), 2 usage error.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from collections import defaultdict
from datetime import datetime, timezone
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from scripts.smoke_obligation_pages import (  # noqa: E402
    QuietHandler, account_registry, chrome_path, render_page,
)

SCHEMA_VERSION = 1
ONE_GIBIBYTE = 1024 ** 3
FOOTPRINT_APPROACH_THRESHOLD = int(0.9 * ONE_GIBIBYTE)

ACCOUNT_PATH_RE = re.compile(r"^[a-z0-9]+(?:/[a-z0-9-]+)+$")
FEDERAL_ACCOUNT_RE = re.compile(r"^\d{3}-\d{4}$")
REQUIRED_ACCOUNT_FIELDS = (
    "path", "name", "abbrev", "agency", "federalAccount", "agencyIdentifier",
    "adapter", "baseline", "availability", "programActivities",
)
REQUIRED_AVAILABILITY_FIELDS = (
    "firstFiscalYear", "firstFiscalYearPeriod", "regularFirstPeriod",
)
# The registry historically uses "complete"/"partial"/"unavailable" for
# per-FY baseline status; "available" is accepted as a synonym for
# "complete" so the schema tolerates either spelling.
VALID_BASELINE_STATUSES = {"complete", "available", "partial", "unavailable"}


class UsageError(Exception):
    """Raised for a verify.py invocation that is malformed, not merely a
    failing check -- results in exit code 2."""


def _check(name, passed, evidence, seconds=0.0):
    return {
        "name": name,
        "passed": bool(passed),
        "evidence": str(evidence),
        "seconds": round(seconds, 3),
    }


def _run_command(name, cmd, cwd=REPO):
    start = time.monotonic()
    result = subprocess.run(
        cmd, cwd=str(cwd), capture_output=True, text=True,
    )
    elapsed = time.monotonic() - start
    combined = (result.stdout or "") + (result.stderr or "")
    lines = [line.strip() for line in combined.splitlines() if line.strip()]
    if result.returncode == 0:
        evidence = lines[-1] if lines else "(no output)"
    else:
        # A collapsed unittest summary such as ``FAILED (errors=1)`` is not
        # actionable in CI.  Preserve a bounded failure tail in both console
        # and JSON evidence so the exact test and traceback survive the job.
        evidence = "\n".join(lines[-80:]) if lines else "(no output)"
    return _check(name, result.returncode == 0, evidence, elapsed)


# --------------------------------------------------------------------------
# Tier: registry -- pre-backfill lint of registry entries + baselines.
# --------------------------------------------------------------------------

def _load_registry(repo):
    return json.loads((repo / "config" / "obligation_accounts.json").read_text())


def _load_crosswalk_rows(repo):
    path = repo / "reference" / "aaas_federal_account_crosswalk.json"
    if not path.exists():
        return []
    return json.loads(path.read_text()).get("rows", [])


def _lint_account(repo, account, crosswalk_rows):
    checks = []
    path = account.get("path", "<missing path>")

    federal_account = str(account.get("federalAccount", ""))
    agency_identifier = str(account.get("agencyIdentifier", ""))
    format_ok = bool(FEDERAL_ACCOUNT_RE.match(federal_account)) and (
        federal_account.split("-")[0] == agency_identifier)
    checks.append(_check(
        f"{path}: account code format", format_ok,
        f"federalAccount={federal_account!r} agencyIdentifier={agency_identifier!r}",
    ))

    path_ok = bool(ACCOUNT_PATH_RE.match(path))
    checks.append(_check(
        f"{path}: registry path format", path_ok, f"path={path!r}",
    ))

    missing = [field for field in REQUIRED_ACCOUNT_FIELDS if not account.get(field)]
    availability = account.get("availability") or {}
    missing_availability = [
        field for field in REQUIRED_AVAILABILITY_FIELDS
        if availability.get(field) is None
    ]
    activities = account.get("programActivities") or []
    slugs = [pa.get("slug") for pa in activities]
    canonical_pairs = [
        (str(pa.get("code", "")).zfill(4), str(pa.get("name", "")).strip().lower())
        for pa in activities
    ]
    park_tokens = [
        token
        for pa in activities
        for token in ([pa.get("park")] + list(pa.get("parkAliases") or []))
        if token
    ]
    code_name_aliases = [
        alias
        for pa in activities
        for alias in (pa.get("codeNameAliases") or [])
    ]
    source_pairs = canonical_pairs + [
        (str(alias.get("code", "")).zfill(4),
         str(alias.get("name", "")).strip().lower())
        for alias in code_name_aliases
    ]
    activities_ok = bool(activities) and all(
        pa.get("slug") and pa.get("code") and pa.get("name")
        and isinstance(pa.get("parkAliases", []), list)
        and all(isinstance(alias, str) and alias for alias in pa.get("parkAliases", []))
        and isinstance(pa.get("codeNameAliases", []), list)
        and all(isinstance(alias, dict) and alias.get("code") and alias.get("name")
                for alias in pa.get("codeNameAliases", []))
        for pa in activities
    ) and (
        len(slugs) == len(set(slugs))
        and len(canonical_pairs) == len(set(canonical_pairs))
        and len(park_tokens) == len(set(park_tokens))
        and len(source_pairs) == len(set(source_pairs))
    )
    fields_ok = not missing and not missing_availability and activities_ok
    evidence = "all required fields present" if fields_ok else (
        f"missing={missing} missing-availability={missing_availability} "
        f"programActivities-incomplete={not activities_ok}"
    )
    checks.append(_check(f"{path}: per-account checks present", fields_ok, evidence))

    baseline_rel = account.get("baseline")
    baseline_path = (repo / baseline_rel) if baseline_rel else None
    if not baseline_path or not baseline_path.exists():
        checks.append(_check(
            f"{path}: baseline file exists", False,
            f"missing baseline at {baseline_rel!r}",
        ))
        return checks
    try:
        baseline = json.loads(baseline_path.read_text())
    except json.JSONDecodeError as error:
        checks.append(_check(
            f"{path}: baseline file exists", False,
            f"{baseline_rel}: invalid JSON ({error})",
        ))
        return checks
    checks.append(_check(f"{path}: baseline file exists", True, str(baseline_rel)))

    citation = baseline.get("source")
    citation_ok = isinstance(citation, str) and bool(citation.strip())
    checks.append(_check(
        f"{path}: baseline source citation", citation_ok,
        f"source={citation!r}" if citation_ok
        else f"{baseline_rel} has no non-empty 'source' citation",
    ))

    fiscal_years = baseline.get("fiscalYears") or {}
    fy_problems = []
    for fiscal_year, row in fiscal_years.items():
        status = row.get("status")
        if status not in VALID_BASELINE_STATUSES:
            fy_problems.append(f"FY{fiscal_year}: invalid status {status!r}")
        elif status == "unavailable" and not row.get("reason"):
            fy_problems.append(f"FY{fiscal_year}: unavailable status has no reason")
    fy_map_ok = bool(fiscal_years) and not fy_problems
    checks.append(_check(
        f"{path}: baseline per-FY status map", fy_map_ok,
        "; ".join(fy_problems) if fy_problems else
        f"{len(fiscal_years)} fiscal year(s) statused, reasons present where required",
    ))

    matches = [
        row for row in crosswalk_rows
        if any(fa.get("code") == federal_account
               for fa in (row.get("federal_accounts") or []))
    ]
    if not matches:
        checks.append(_check(
            f"{path}: crosswalk correspondence", True,
            "no crosswalk row references this federal account (not required)",
        ))
    else:
        resolved = [row.get("aaas_row_key") for row in matches
                    if row.get("status") == "resolved"]
        deferred = [row.get("aaas_row_key") for row in matches
                    if row.get("status") != "resolved"]
        checks.append(_check(
            f"{path}: crosswalk correspondence", bool(resolved),
            (f"{len(resolved)} resolved corresponding row(s); "
             f"deferred provisional/unresolved rows={deferred}"
             if resolved else
             f"no resolved corresponding row; deferred rows={deferred}"),
        ))
    return checks


def tier_registry(repo=REPO, account_filter=None):
    repo = Path(repo)
    registry = _load_registry(repo)
    checks = []
    schema_ok = registry.get("schemaVersion") == 2
    checks.append(_check(
        "registry: schemaVersion", schema_ok,
        f"schemaVersion={registry.get('schemaVersion')}",
    ))

    accounts = registry.get("accounts", [])
    paths = [account.get("path") for account in accounts]
    dup_paths = sorted({p for p in paths if p and paths.count(p) > 1})
    checks.append(_check(
        "registry: no duplicate account paths", not dup_paths,
        f"duplicates={dup_paths}" if dup_paths else f"{len(paths)} account path(s), all unique",
    ))
    federal_accounts = [account.get("federalAccount") for account in accounts]
    dup_federal = sorted({f for f in federal_accounts if f and federal_accounts.count(f) > 1})
    checks.append(_check(
        "registry: no duplicate federal accounts", not dup_federal,
        f"duplicates={dup_federal}" if dup_federal
        else f"{len(federal_accounts)} federal account(s), all unique",
    ))

    if account_filter:
        selected = [a for a in accounts if a.get("path") == account_filter]
        if not selected:
            raise UsageError(
                f"--account {account_filter!r} not found in "
                "config/obligation_accounts.json"
            )
    else:
        selected = accounts

    crosswalk_rows = _load_crosswalk_rows(repo)
    for account in selected:
        checks.extend(_lint_account(repo, account, crosswalk_rows))
    return checks


# --------------------------------------------------------------------------
# Tier: fast -- full unit suite + every offline validator (default tier).
# --------------------------------------------------------------------------

def tier_fast(repo=REPO):
    repo = Path(repo)
    py = sys.executable
    return [
        _run_command("unit-tests",
                     [py, "-m", "unittest", "discover", "-s", "tests"], cwd=repo),
        _run_command("validate-obligations",
                     [py, "scripts/validate_obligations.py", "--allow-empty"], cwd=repo),
        _run_command("validate-nih",
                     [py, "scripts/validate_nih.py"], cwd=repo),
        _run_command("validate-usaspending-calibration",
                     [py, "scripts/validate_usaspending_calibration.py"], cwd=repo),
        _run_command("validate-funding-sentinel",
                     [py, "scripts/validate_funding_sentinel.py"], cwd=repo),
        _run_command("verify-dms-baseline",
                     [py, "scripts/verify_dms_baseline.py"], cwd=repo),
        _run_command("validate-award-invariants",
                     [py, "scripts/validate_award_invariants.py"], cwd=repo),
    ]


# --------------------------------------------------------------------------
# Tier: rendered -- browser smoke matrices, incl. --all-accounts.
# --------------------------------------------------------------------------

def tier_rendered(repo=REPO, chrome=None):
    repo = Path(repo)
    py = sys.executable
    chrome_args = ["--chrome", chrome] if chrome else []
    return [
        _run_command("smoke-obligation-pages",
                     [py, "scripts/smoke_obligation_pages.py", *chrome_args], cwd=repo),
        _run_command("smoke-obligation-pages-all-accounts",
                     [py, "scripts/smoke_obligation_pages.py", "--all-accounts",
                      *chrome_args], cwd=repo),
        _run_command("smoke-sentinel-page",
                     [py, "scripts/smoke_sentinel_page.py", *chrome_args], cwd=repo),
    ]


# --------------------------------------------------------------------------
# Tier: screens -- reader-review screenshot pack. Never pass/fail.
# --------------------------------------------------------------------------

def _screens_targets(repo):
    """Every page the reader-review release-bar item (working-regime #5 /
    3.2d cross-cutting gates) asks for, discovered from the registry --
    never a hardcoded account list."""
    accounts = account_registry(repo)
    targets = [
        ("award-root", ""),
        ("obligations-landing", "obligations"),
    ]
    for account in accounts:
        slug = account["path"].replace("/", "-")
        targets.append((f"obligations-account-{slug}", f"obligations/{account['path']}"))
    by_agency = {}
    for account in accounts:
        agency_slug = account["path"].split("/")[0]
        by_agency.setdefault(agency_slug, account)
    for agency_slug, account in sorted(by_agency.items()):
        activities = account.get("programActivities") or []
        if activities:
            pa = activities[0]
            targets.append((
                f"obligations-pa-{agency_slug}-{pa['slug']}",
                f"obligations/{account['path']}/{pa['slug']}",
            ))
    targets.append(("sentinel", "sentinel"))
    return targets


def tier_screens(repo=REPO, out_dir=None, chrome=None):
    repo = Path(repo)
    out_dir = Path(out_dir) if out_dir else Path(tempfile.gettempdir()) / (
        "verification-screens-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    executable = chrome_path(chrome)
    assembly = tempfile.TemporaryDirectory()
    assembly_path = Path(assembly.name)
    shutil.copy2(repo / "site" / "index.html", assembly_path / "index.html")
    os.symlink(repo / "data", assembly_path / "data", target_is_directory=True)
    handler = partial(QuietHandler, directory=str(assembly_path))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    manifest = []
    try:
        for label, org_path in _screens_targets(repo):
            query = f"?org={quote(org_path, safe='/')}" if org_path else ""
            url = f"http://127.0.0.1:{server.server_port}/index.html{query}"
            out_path = out_dir / f"{label}.png"
            start = time.monotonic()
            note = "ok"
            try:
                render_page(executable, url, 1100, 900, "light", screenshot_path=out_path)
            except Exception as error:  # best-effort: this tier never fails
                note = f"capture failed: {error}"
            manifest.append({
                "label": label,
                "orgPath": org_path,
                "file": str(out_path),
                "note": note,
                "seconds": round(time.monotonic() - start, 3),
            })
    finally:
        server.shutdown()
        server.server_close()
        assembly.cleanup()
    return manifest, out_dir


# --------------------------------------------------------------------------
# Footprint: fold repo/store size and 52-week trajectory into every result.
# --------------------------------------------------------------------------

def _tracked_files(repo):
    result = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "-z"],
        capture_output=True, check=True,
    )
    return [p for p in result.stdout.decode().split("\0") if p]


def _per_tree_bytes(repo, files):
    totals = defaultdict(int)
    for rel in files:
        try:
            size = (repo / rel).stat().st_size
        except OSError:
            continue
        top = rel.split("/", 1)[0]
        totals[top] += size
    return dict(sorted(totals.items()))


def _gzipped_store_bytes(repo, files):
    return sum(
        (repo / rel).stat().st_size for rel in files
        if rel.startswith("data/") and rel.endswith(".gz") and (repo / rel).exists()
    )


def _tree_bytes_at(repo, ref, subpath):
    result = subprocess.run(
        ["git", "-C", str(repo), "ls-tree", "-r", "-l", ref, "--", subpath],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    total = 0
    for line in result.stdout.splitlines():
        meta = line.split("\t", 1)[0]
        fields = meta.split()
        if len(fields) >= 4 and fields[1] == "blob":
            try:
                total += int(fields[3])
            except ValueError:
                pass
    return total


def _first_commit_touching(repo, subpath):
    result = subprocess.run(
        ["git", "-C", str(repo), "log", "--reverse", "--format=%H %cI", "--", subpath],
        capture_output=True, text=True,
    )
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        return None, None
    sha, iso = lines[0].split(" ", 1)
    return sha, iso


def compute_footprint(repo=REPO):
    repo = Path(repo)
    files = _tracked_files(repo)
    per_tree = _per_tree_bytes(repo, files)
    gzipped = _gzipped_store_bytes(repo, files)
    trajectory = None
    first_sha, first_iso = _first_commit_touching(repo, "data")
    if first_sha:
        bytes_first = _tree_bytes_at(repo, first_sha, "data")
        bytes_now = _tree_bytes_at(repo, "HEAD", "data")
        if bytes_first is not None and bytes_now is not None:
            try:
                first_date = datetime.fromisoformat(first_iso)
            except ValueError:
                first_date = None
            if first_date is not None:
                now = datetime.now(timezone.utc)
                weeks = max((now - first_date).total_seconds() / (7 * 86400), 1.0)
                weekly_rate = max(bytes_now - bytes_first, 0) / weeks
                projected = bytes_now + weekly_rate * 52
                trajectory = {
                    "method": (
                        "linear extrapolation of the data/ tree's committed byte "
                        "total from the first commit that touched data/ to HEAD, "
                        "projected 52 weeks forward"
                    ),
                    "note": (
                        "the sampled history to date is dominated by one-time "
                        "historical backfills (Phases 1-3.2c), not steady-state "
                        "weekly incremental refreshes, so this rate is a "
                        "conservative UPPER BOUND, not a steady-state forecast; "
                        "re-derive after several weeks of pure incremental "
                        "refresh history exist"
                    ),
                    "firstDataCommit": first_sha,
                    "firstDataCommitDate": first_iso,
                    "weeksElapsed": round(weeks, 2),
                    "currentDataTreeBytes": bytes_now,
                    "weeklyGrowthBytesUpperBound": round(weekly_rate),
                    "projected52WeekBytesUpperBound": round(projected),
                    "thresholdBytes": FOOTPRINT_APPROACH_THRESHOLD,
                    "approachesOneGigabyte": projected >= FOOTPRINT_APPROACH_THRESHOLD,
                }
    return {
        "perTreeBytes": per_tree,
        "totalTrackedBytes": sum(per_tree.values()),
        "gzippedStoreBytes": gzipped,
        "trajectory": trajectory,
    }


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _print_checks(checks):
    for item in checks:
        status = "PASS" if item["passed"] else "FAIL"
        print(f"{status} [{item['seconds']:.2f}s] {item['name']}: {item['evidence']}")


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="verify.py",
        description="Uniform verification entry point: registry, fast "
                     "(default), rendered, and screens tiers.",
    )
    parser.add_argument(
        "--tier", choices=["registry", "fast", "rendered", "screens"],
        default="fast",
    )
    parser.add_argument(
        "--account",
        help="registry tier only: lint a single account path, as it "
             "appears in config/obligation_accounts.json (e.g. <agency>/<account>)",
    )
    parser.add_argument(
        "--json", dest="json_path", type=Path,
        help="write the machine-readable result to this path",
    )
    parser.add_argument(
        "--out", type=Path,
        help="screens tier only: directory for the screenshot pack "
             "(default: OS temp dir)",
    )
    parser.add_argument(
        "--chrome",
        help="rendered/screens tiers: headless Chrome/Chromium executable",
    )
    args = parser.parse_args(argv)

    if args.account and args.tier != "registry":
        parser.error("--account is only valid with --tier registry")
    if args.out and args.tier != "screens":
        parser.error("--out is only valid with --tier screens")

    start = time.monotonic()
    is_screens = args.tier == "screens"
    try:
        if args.tier == "registry":
            checks = tier_registry(account_filter=args.account)
        elif args.tier == "fast":
            checks = tier_fast()
        elif args.tier == "rendered":
            checks = tier_rendered(chrome=args.chrome)
        else:
            manifest_rows, out_dir = tier_screens(out_dir=args.out, chrome=args.chrome)
    except UsageError as error:
        print(f"USAGE ERROR: {error}", file=sys.stderr)
        return 2

    elapsed = time.monotonic() - start
    footprint = compute_footprint()

    if is_screens:
        print(f"Screenshot pack written to {out_dir}")
        print("Manifest:")
        for row in manifest_rows:
            print(f"  {row['label']}: org={row['orgPath'] or '(root)'} -> "
                  f"{row['file']} [{row['note']}]")
        result = {
            "schemaVersion": SCHEMA_VERSION,
            "tier": args.tier,
            "account": None,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "durationSeconds": round(elapsed, 3),
            "passed": True,
            "screens": {"outDir": str(out_dir), "manifest": manifest_rows},
            "footprint": footprint,
        }
        if args.json_path:
            args.json_path.parent.mkdir(parents=True, exist_ok=True)
            args.json_path.write_text(json.dumps(result, indent=1) + "\n")
        print(f"\n{args.tier} tier: {len(manifest_rows)} screenshot(s) captured "
              f"({elapsed:.1f}s) -- this tier never fails")
        return 0

    _print_checks(checks)
    passed = all(item["passed"] for item in checks)
    result = {
        "schemaVersion": SCHEMA_VERSION,
        "tier": args.tier,
        "account": args.account,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "durationSeconds": round(elapsed, 3),
        "passed": passed,
        "checks": checks,
        "footprint": footprint,
    }
    if args.json_path:
        args.json_path.parent.mkdir(parents=True, exist_ok=True)
        args.json_path.write_text(json.dumps(result, indent=1) + "\n")

    summary = f"{sum(item['passed'] for item in checks)}/{len(checks)} checks"
    print(f"\n{args.tier} tier: {'PASS' if passed else 'FAIL'} "
          f"({summary}, {elapsed:.1f}s)")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
