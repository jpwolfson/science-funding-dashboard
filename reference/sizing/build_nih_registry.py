#!/usr/bin/env python3
"""Phase 3.2e provenance generator: NIH obligation-account registry entries
and scaffold baselines, built from every
``reference/sizing/nih_registry_discovery_*.json`` chunk present.

This is a scratch/provenance script, not part of the runtime pipeline. It is
committed so the exact derivation of the 27 NIH registry entries + scaffold
baselines is reproducible, and so it can be re-run once discovery chunks 2
and 3 land (it is idempotent over however many chunks currently exist on
disk -- it never requires all 27 accounts to be present).

What it does, in order:
  1. Merge every discovery chunk's ``accounts`` map (each federal account
     must appear in exactly one chunk -- a duplicate is a hard error).
  2. For each discovered account, derive its registry ``programActivities``
     from the union of ``officialProgramActivities`` and every discovery
     fiscal year's File B identities (see ``build_program_activities``).
  3. Append any not-yet-registered account to
     ``config/obligation_accounts.json`` (existing entries are never
     reordered or modified).
  4. Write that account's schema-v2 scaffold baseline (NSF Phase 3.2d
     precedent shape: unavailable FY2015-16, partial FY2017.. without
     ``obligationsCents`` -- the CI backfill pins exact values). A baseline
     that already carries backfilled data (any fiscal year has
     ``obligationsCents``) is left untouched by a rerun.
  5. Self-check: build ``adapters.usaspending_obligations.alias_map`` from
     every generated account's ``programActivities`` and resolve every
     single observed (code, name, PARK) identity from the discovery data
     (plus the official per-account Program Activity list) through the
     same ``_pa`` logic the adapter uses at pull time. Any identity that
     does not resolve raises immediately -- this is the fail-closed
     alias-drift gate the docs/phase-3.2e-handoff.md task calls for,
     run here at generation time instead of only at first-backfill time.

Usage:
    python reference/sizing/build_nih_registry.py
    python reference/sizing/build_nih_registry.py --check   # verify only

``--check`` runs steps 1-2 and 5 (derivation + self-check) and reports which
accounts from the full 27-account scope are still missing discovery data,
without writing anything.
"""
import argparse
import glob
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from adapters.usaspending_obligations import alias_map, _pa  # noqa: E402

CONFIG_PATH = REPO_ROOT / "config" / "obligation_accounts.json"
DISCOVERY_GLOB = str(REPO_ROOT / "reference" / "sizing" / "nih_registry_discovery_*.json")

# Static per-account metadata the discovery data cannot itself supply: the
# institute's proper title-case name, standard abbreviation, and the IC
# slug used to build both the registry path (``hhs/nih-<ic_slug>``) and the
# baseline filename (``reference/hhs_nih_<ic_slug>_obligation_baseline.json``).
# ARPA-H is the one path/baseline exception (docs/phase-3.2e-handoff.md).
#
# federal_account -> (ic_slug, name, abbrev, path_override, baseline_override)
ACCOUNT_META = {
    "075-0807": ("nlm", "National Library of Medicine", "NLM", None, None),
    "075-0819": ("fic", "John E. Fogarty International Center", "FIC", None, None),
    "075-0837": ("arpa-h", "Advanced Research Projects Agency for Health", "ARPA-H",
                 "hhs/arpa-h", "reference/hhs_arpa_h_obligation_baseline.json"),
    "075-0838": ("bf", "NIH Buildings and Facilities", "NIH B&F", None, None),
    "075-0843": ("nia", "National Institute on Aging", "NIA", None, None),
    "075-0844": ("nichd",
                 "Eunice Kennedy Shriver National Institute of Child Health "
                 "and Human Development", "NICHD", None, None),
    "075-0846": ("od", "NIH Office of the Director", "NIH OD", None, None),
    "075-0849": ("nci", "National Cancer Institute", "NCI", None, None),
    "075-0851": ("nigms", "National Institute of General Medical Sciences", "NIGMS", None, None),
    "075-0862": ("niehs", "National Institute of Environmental Health Sciences", "NIEHS", None, None),
    "075-0872": ("nhlbi", "National Heart, Lung, and Blood Institute", "NHLBI", None, None),
    "075-0873": ("nidcr", "National Institute of Dental and Craniofacial Research", "NIDCR", None, None),
    "075-0875": ("ncats", "National Center for Advancing Translational Sciences", "NCATS", None, None),
    "075-0884": ("niddk",
                 "National Institute of Diabetes and Digestive and Kidney Diseases",
                 "NIDDK", None, None),
    "075-0885": ("niaid", "National Institute of Allergy and Infectious Diseases", "NIAID", None, None),
    "075-0886": ("ninds", "National Institute of Neurological Disorders and Stroke", "NINDS", None, None),
    "075-0887": ("nei", "National Eye Institute", "NEI", None, None),
    "075-0888": ("niams",
                 "National Institute of Arthritis and Musculoskeletal and Skin Diseases",
                 "NIAMS", None, None),
    "075-0889": ("ninr", "National Institute of Nursing Research", "NINR", None, None),
    "075-0890": ("nidcd",
                 "National Institute on Deafness and Other Communication Disorders",
                 "NIDCD", None, None),
    "075-0891": ("nhgri", "National Human Genome Research Institute", "NHGRI", None, None),
    "075-0892": ("nimh", "National Institute of Mental Health", "NIMH", None, None),
    "075-0893": ("nida", "National Institute on Drug Abuse", "NIDA", None, None),
    "075-0894": ("niaaa", "National Institute on Alcohol Abuse and Alcoholism", "NIAAA", None, None),
    "075-0896": ("nccih",
                 "National Center for Complementary and Integrative Health",
                 "NCCIH", None, None),
    "075-0897": ("nimhd",
                 "National Institute on Minority Health and Health Disparities",
                 "NIMHD", None, None),
    "075-0898": ("nibib",
                 "National Institute of Biomedical Imaging and Bioengineering",
                 "NIBIB", None, None),
}

# The full Phase 3.2e scope (docs/phase-3.2e-handoff.md); used only to report
# which accounts are still awaiting a discovery chunk.
FULL_SCOPE = set(ACCOUNT_META)


def _slugify(text):
    text = text.lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return re.sub(r"-{2,}", "-", text)


def _normalize_code(code):
    code = (code or "").strip()
    return code.zfill(4) if code else "0000"


def _normalize_name(name):
    return re.sub(r"\s+", " ", (name or "").strip()).lower()


def load_discovery_chunks():
    merged = {}
    sources = {}
    for path in sorted(Path(p) for p in glob.glob(DISCOVERY_GLOB)):
        chunk = json.loads(path.read_text())
        for code, account in chunk.get("accounts", {}).items():
            if code in merged:
                raise ValueError(
                    f"{code} present in more than one discovery chunk "
                    f"({sources[code]} and {path.name})"
                )
            merged[code] = account
            sources[code] = path.name
    return merged, sources


def _is_zero(code, park):
    """True when a File B / official identity is the unknown/zero bucket:
    an explicit PAC/PAN code of ``0000``, or a PARK of exactly ``0000``
    (the FY2026 zero-obligation PARK seen on several accounts).

    A *blank* code is not itself zero/unknown -- a FY2026 PARK-only row
    always reports a blank ``program_activity_code`` (and blank name) even
    though it carries a perfectly good, real institute PARK; ``_pa()``
    already gives PARK absolute priority over a blank/zero code for
    exactly this reason (docs/obligation-ledger.md), and this helper must
    agree with that priority instead of normalizing the blank code to
    ``"0000"`` the way ``_normalize_code`` does for display purposes.
    """
    park = (park or "").strip()
    if park:
        return park == "0000"
    code = (code or "").strip()
    return code.zfill(4) == "0000" if code else False


def build_program_activities(federal_account, discovery_account):
    """Union officialProgramActivities + every discovery FY's File B rows
    into a registry ``programActivities`` list. Returns
    ``(entries_without_institute_or_reimbursable, institute_group,
    reimbursable_group, warnings)`` where the last three are consumed by
    the caller to attach the account's known institute/0801 identities and
    surface anything unexpected.
    """
    warnings = []

    # ---- Unknown/zero bucket: uniform house style across every account,
    # per the hhs/ahrq precedent, regardless of what this account's own
    # data happens to show. ----
    zero_names = {"UNKNOWN/OTHER"}

    def note_zero_name(name):
        name = (name or "").strip()
        if name:
            zero_names.add(name)

    official = discovery_account.get("officialProgramActivities") or []
    for item in official:
        code = item["code"] if item.get("type") != "PARK" else None
        park = item["code"] if item.get("type") == "PARK" else None
        if _is_zero(code, park):
            note_zero_name(item.get("name"))

    for fy_row in (discovery_account.get("fiscalYears") or {}).values():
        file_b = fy_row.get("fileB")
        if not file_b:
            continue
        for pa in file_b.get("programActivities", []):
            if _is_zero(pa.get("code"), pa.get("park")):
                note_zero_name(pa.get("name"))

    unknown_entry = {
        "slug": "unknown-other",
        "code": "0000",
        "name": "Unknown / other",
        "park": "0000",
        "codeNameAliases": [
            {"code": "0000", "name": name} for name in sorted(zero_names)
        ],
    }

    # ---- Named groups (institute PA, 0801 reimbursable, and any drift) ----
    # Keyed by normalized name; the official per-account snapshot is the
    # authoritative PARK<->PAC/PAN bridge (a PARK and its PAC/PAN share the
    # identical official ``name``), so it seeds the groups before any
    # historical File B row is folded in.
    groups = {}  # norm_name -> {"names": set, "pac": code4|None, "park": token|None}

    def touch(norm):
        return groups.setdefault(norm, {"names": set(), "pac": None, "park": None})

    for item in official:
        code, name, kind = item.get("code"), item.get("name") or "", item.get("type")
        if kind == "PARK":
            if _is_zero(None, code):
                continue
        else:
            if _is_zero(code, None):
                continue
        norm = _normalize_name(name)
        if not norm:
            continue
        group = touch(norm)
        group["names"].add(name.strip())
        if kind == "PARK":
            if group["park"] not in (None, code):
                raise ValueError(
                    f"{federal_account}: conflicting PARK for {name!r} "
                    f"({group['park']!r} vs {code!r})"
                )
            group["park"] = code
        else:
            code4 = _normalize_code(code)
            if group["pac"] not in (None, code4):
                raise ValueError(
                    f"{federal_account}: conflicting PAC/PAN for {name!r} "
                    f"({group['pac']!r} vs {code4!r})"
                )
            group["pac"] = code4

    park_to_norm = {g["park"]: norm for norm, g in groups.items() if g["park"]}
    code_to_norm = {}
    for norm, g in groups.items():
        if g["pac"]:
            code_to_norm.setdefault(g["pac"], set()).add(norm)

    for fy, fy_row in sorted((discovery_account.get("fiscalYears") or {}).items()):
        file_b = fy_row.get("fileB")
        if not file_b:
            continue
        for pa in file_b.get("programActivities", []):
            code = pa.get("code") or ""
            raw_name = (pa.get("name") or "").strip()
            park = (pa.get("park") or "").strip()
            if _is_zero(code, park):
                continue
            if park:
                norm = park_to_norm.get(park)
                if norm is None:
                    raise ValueError(
                        f"{federal_account} FY{fy}: PARK {park!r} observed in "
                        "File B is not in officialProgramActivities -- "
                        "unregistered PARK, refusing to guess its identity"
                    )
                if raw_name:
                    groups[norm]["names"].add(raw_name)
                continue
            code4 = _normalize_code(code)
            norms = code_to_norm.get(code4)
            if not norms:
                norm = _normalize_name(raw_name) or code4
                groups[norm] = {
                    "names": ({raw_name} if raw_name else set()),
                    "pac": code4, "park": None,
                }
                code_to_norm[code4] = {norm}
                warnings.append(
                    f"{federal_account} FY{fy}: PAC/PAN {code4!r} ({raw_name!r}) "
                    "observed in File B but not in officialProgramActivities -- "
                    "added as its own entry; review name/slug by hand"
                )
                continue
            if len(norms) > 1:
                raise ValueError(
                    f"{federal_account}: ambiguous PAC/PAN code {code4!r} maps "
                    f"to multiple names {norms!r}"
                )
            norm = next(iter(norms))
            if raw_name:
                groups[norm]["names"].add(raw_name)

    return unknown_entry, groups, warnings


def _titleize(raw):
    stop = {"of", "and", "the", "for", "on", "in", "to", "a", "an"}
    words = raw.strip().split()
    out = []
    for index, word in enumerate(words):
        lower = word.lower()
        if word.isupper() and len(word) <= 5 and word.isalpha() and index != 0:
            out.append(word)
        elif lower in stop and index != 0:
            out.append(lower)
        else:
            out.append(word.capitalize())
    return " ".join(out)


def build_account_entry(federal_account, discovery_account, meta):
    ic_slug, name, abbrev, path_override, baseline_override = meta
    path = path_override or f"hhs/nih-{ic_slug}"
    baseline_rel = baseline_override or f"reference/hhs_nih_{ic_slug.replace('-', '_')}_obligation_baseline.json"

    unknown_entry, groups, warnings = build_program_activities(federal_account, discovery_account)

    reimbursable_group = groups.pop("nih reimbursable - other", None)
    # A defensive alternate spelling check (case/space only -- exact name
    # equality is what the loop above already normalized on).
    if reimbursable_group is None:
        for key in list(groups):
            if key.replace("-", " ").strip() == "nih reimbursable other":
                reimbursable_group = groups.pop(key)
                break

    remaining = list(groups.items())
    institute_group = None
    extra_entries = []
    if remaining:
        # The institute's own Program Activity is expected to be the single
        # largest remaining identity by observed dollars; anything else
        # left over is genuine drift this account's task brief did not
        # anticipate, and is still emitted (never dropped) with a loud
        # warning for manual review.
        def total_cents(norm):
            total = 0
            for fy_row in (discovery_account.get("fiscalYears") or {}).values():
                file_b = fy_row.get("fileB")
                if not file_b:
                    continue
                for pa in file_b.get("programActivities", []):
                    if _is_zero(pa.get("code"), pa.get("park")):
                        continue
                    pa_norm = None
                    park = (pa.get("park") or "").strip()
                    if park:
                        for g_norm, g in groups.items():
                            if g["park"] == park:
                                pa_norm = g_norm
                    else:
                        code4 = _normalize_code(pa.get("code"))
                        for g_norm, g in groups.items():
                            if g["pac"] == code4:
                                pa_norm = g_norm
                    if pa_norm == norm:
                        total += pa.get("cents", 0)
            return total

        remaining.sort(key=lambda item: total_cents(item[0]), reverse=True)
        institute_norm, institute_group = remaining[0]
        for extra_norm, extra_group in remaining[1:]:
            raw_name = sorted(extra_group["names"])[0] if extra_group["names"] else extra_norm
            slug = _slugify(raw_name) or extra_norm
            entry = {
                "slug": slug,
                "code": extra_group["pac"] or "0000",
                "name": _titleize(raw_name),
            }
            if extra_group["park"]:
                entry["park"] = extra_group["park"]
            if len(extra_group["names"]) > 1:
                entry["codeNameAliases"] = [
                    {"code": extra_group["pac"] or "0000", "name": n}
                    for n in sorted(extra_group["names"]) if n != raw_name
                ]
            extra_entries.append(entry)
            warnings.append(
                f"{federal_account}: extra Program Activity beyond institute/0801 "
                f"emitted as slug={slug!r} name={entry['name']!r} -- verify by hand"
            )

    if institute_group is None:
        raise ValueError(
            f"{federal_account}: no non-zero, non-0801 Program Activity found "
            "-- cannot identify the institute's own activity"
        )

    institute_entry = {
        "slug": _slugify(name),
        "code": institute_group["pac"] or "0000",
        "park": institute_group["park"] or "",
        "name": name,
    }
    if not institute_entry["park"]:
        del institute_entry["park"]

    program_activities = [unknown_entry, institute_entry]
    if reimbursable_group is not None:
        reimbursable_entry = {
            "slug": "nih-reimbursable-other",
            "code": reimbursable_group["pac"] or "0801",
            "name": "NIH reimbursable – other",
        }
        if reimbursable_group["park"]:
            reimbursable_entry["park"] = reimbursable_group["park"]
        program_activities.append(reimbursable_entry)
    program_activities.extend(extra_entries)

    first_fy = discovery_account["firstActiveFiscalYear"]
    first_period = discovery_account["fiscalYears"][str(first_fy)]["firstNonEmptyPeriod"]

    account_entry = {
        "path": path,
        "name": name,
        "abbrev": abbrev,
        "agency": "Department of Health and Human Services",
        "federalAccount": federal_account,
        "agencyIdentifier": "075",
        "adapter": "usaspending_obligations",
        "baseline": baseline_rel,
        "availability": {
            "firstFiscalYear": first_fy,
            "firstFiscalYearPeriod": first_period,
            "regularFirstPeriod": 2,
        },
        "programActivities": program_activities,
    }
    return account_entry, warnings


def build_scaffold_baseline(federal_account, first_fy, first_period, source_note):
    fiscal_years = {}
    for fy in range(2015, 2017):
        fiscal_years[str(fy)] = {
            "status": "unavailable",
            "reason": "Files A/B/C begin in FY2017 Q2",
        }
    # An account whose own first active fiscal year is later than FY2017
    # (none observed so far, but ARPA-H -- created after FY2017 -- has not
    # yet been confirmed by a discovery chunk) did not exist yet in years
    # the platform itself already covers; that is a different, account-
    # specific reason from the platform-wide FY2015-16 gap.
    for fy in range(2017, first_fy):
        fiscal_years[str(fy)] = {
            "status": "unavailable",
            "reason": f"{federal_account} had no activity before FY{first_fy} "
                      "(account not yet established)",
        }
    for fy in range(max(first_fy, 2017), 2026):
        row = {"status": "partial", "asOfPeriod": 12}
        if fy == first_fy:
            row["firstPeriod"] = first_period
        fiscal_years[str(fy)] = row
    fiscal_years["2026"] = {"status": "partial", "asOfPeriod": 10}
    return {
        "schemaVersion": 2,
        "federalAccount": federal_account,
        "source": source_note,
        "fiscalYears": fiscal_years,
        "notes": [
            "Initial replaceable scaffolds intentionally omit obligationsCents "
            "until the first accepted full backfill.",
            "The atomic reconcile promotes completed P12 years and pins exact "
            "File B cents; the first active fiscal year remains partial from "
            "its first reporting period and FY2026 remains period-specific.",
        ],
    }


def self_check(entries_by_account, discovery, sources):
    """Fail-closed alias-drift gate: build alias_map() per account and
    resolve every observed (code, name, PARK) identity -- from both the
    official per-account Program Activity list and every discovery fiscal
    year's File B rows -- through the exact _pa() logic the adapter uses at
    pull time. Any identity that fails to resolve raises immediately.
    """
    for federal_account, account_entry in entries_by_account.items():
        aliases = alias_map(account_entry)
        discovery_account = discovery[federal_account]
        observed = set()
        for item in discovery_account.get("officialProgramActivities") or []:
            if item.get("type") == "PARK":
                observed.add((None, item.get("name") or "", item["code"]))
            else:
                observed.add((item["code"], item.get("name") or "", None))
        for fy_row in (discovery_account.get("fiscalYears") or {}).values():
            file_b = fy_row.get("fileB")
            if not file_b:
                continue
            for pa in file_b.get("programActivities", []):
                observed.add((pa.get("code") or "", pa.get("name") or "",
                              pa.get("park") or ""))
        for code, name, park in observed:
            row = {
                "program_activity_reporting_key": park or "",
                "program_activity_code": code or "",
                "program_activity_name": name or "",
            }
            try:
                _pa(row, aliases)
            except Exception as error:
                raise ValueError(
                    f"{federal_account} ({sources.get(federal_account)}): "
                    f"identity code={code!r} name={name!r} park={park!r} "
                    f"did not resolve through alias_map()/_pa(): {error}"
                ) from error


def _reindent(text, extra_spaces):
    prefix = " " * extra_spaces
    return "\n".join((prefix + line if line else line) for line in text.split("\n"))


ACCOUNTS_TAIL = "  }\n ]\n}\n"


def append_accounts_text(raw_text, new_entries):
    """Append ``new_entries`` to the ``accounts`` array by editing the raw
    file text, never by re-serializing the whole document. Existing entries
    use a mix of hand-tuned compact and plain-``indent=1`` formatting
    accumulated across onboardings (DOE/NSF's Program Activities are
    single-line; hhs/ahrq's are fully expanded); round-tripping the file
    through ``json.dumps`` would reformat all of it. New entries are
    rendered with plain ``json.dumps(entry, indent=1)`` -- matching the
    hhs/ahrq precedent this task cites -- reindented by a constant 2 spaces
    to land at the same depth as every other ``accounts`` array element.
    """
    if not raw_text.endswith(ACCOUNTS_TAIL):
        raise ValueError(
            "config/obligation_accounts.json does not end with the expected "
            f"accounts-array closing shape {ACCOUNTS_TAIL!r}; refusing to "
            "append via text splice rather than risk corrupting the file"
        )
    head = raw_text[: -len(ACCOUNTS_TAIL)]
    rendered = [_reindent(json.dumps(entry, indent=1), 2) for entry in new_entries]
    return head + "  },\n" + ",\n".join(rendered) + "\n ]\n}\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true",
                         help="verify derivation + self-check only; no writes")
    args = parser.parse_args()

    discovery, sources = load_discovery_chunks()
    unknown_federal_accounts = sorted(set(discovery) - FULL_SCOPE)
    if unknown_federal_accounts:
        raise ValueError(
            f"discovery data contains federal accounts outside the Phase "
            f"3.2e scope: {unknown_federal_accounts}"
        )
    missing = sorted(FULL_SCOPE - set(discovery))

    config = json.loads(CONFIG_PATH.read_text())
    existing_paths = {row["path"] for row in config["accounts"]}
    existing_federal_accounts = {row["federalAccount"] for row in config["accounts"]}

    entries_by_account = {}
    all_warnings = []
    new_entries = []
    new_baselines = {}
    for federal_account in sorted(discovery):
        meta = ACCOUNT_META[federal_account]
        entry, warnings = build_account_entry(federal_account, discovery[federal_account], meta)
        entries_by_account[federal_account] = entry
        all_warnings.extend(warnings)
        if entry["path"] in existing_paths or federal_account in existing_federal_accounts:
            continue
        new_entries.append(entry)

        baseline_path = REPO_ROOT / entry["baseline"]
        if baseline_path.exists():
            existing_baseline = json.loads(baseline_path.read_text())
            if any("obligationsCents" in row for row in existing_baseline.get("fiscalYears", {}).values()):
                # Already backfilled -- never clobber accepted pins.
                continue
        first_fy = discovery[federal_account]["firstActiveFiscalYear"]
        first_period = discovery[federal_account]["fiscalYears"][str(first_fy)]["firstNonEmptyPeriod"]
        scaffold = build_scaffold_baseline(
            federal_account, first_fy, first_period,
            source_note=(
                "USAspending federal account fiscal-year snapshots (GTAS/File A); "
                "account title and source availability reviewed via "
                "scripts/discover_obligation_program_activities.py "
                f"({discovery[federal_account].get('title', federal_account)})"
            ),
        )
        new_baselines[entry["baseline"]] = scaffold

    self_check(entries_by_account, discovery, sources)

    for warning in all_warnings:
        print(f"WARNING: {warning}", file=sys.stderr)

    if missing:
        print(
            f"{len(missing)} of {len(FULL_SCOPE)} NIH accounts still await a "
            f"discovery chunk: {missing}",
            file=sys.stderr,
        )

    if args.check:
        print(
            f"OK (check-only): {len(discovery)} discovered, "
            f"{len(new_entries)} new registry entrie(s) would be written, "
            f"{len(all_warnings)} warning(s)"
        )
        return

    if new_entries:
        raw_text = CONFIG_PATH.read_text()
        CONFIG_PATH.write_text(append_accounts_text(raw_text, new_entries))
        # Baseline files are brand new (never pre-existing), so a plain
        # dump matching house style (reference/hhs_ahrq_obligation_baseline.json
        # etc. use ``json.dumps(..., indent=1)``) is safe here.
        for baseline_rel, scaffold in new_baselines.items():
            (REPO_ROOT / baseline_rel).write_text(json.dumps(scaffold, indent=1) + "\n")
        print(
            f"Wrote {len(new_entries)} new registry entrie(s) and "
            f"{len(new_baselines)} scaffold baseline(s)."
        )
    else:
        print("No new registry entries to write (all discovered accounts already registered).")


if __name__ == "__main__":
    main()
