#!/usr/bin/env python3
"""Empirically discover and verify the NSF org registry (config/orgs.json).

Runs on CI (the interactive session cannot reach api.nsf.gov). Two
independent empirical sources are cross-checked:

1. API sweep: probe candidate org codes DDVV0000 via org_code_div on the
   Award Search API (existence only; the API's pagination faults don't
   matter for existence).
2. NSF bulk award downloads (per-year zips of per-award XML from
   nsf.gov/awardsearch/download): each award record carries its 8-digit
   org Code plus Division/Directorate abbreviation and long name. This is
   NSF's own authoritative mapping - no HTML scraping.

Checks performed:
- Param semantics: sample award ids returned by the API under
  org_code_div=X must carry code X in the bulk records (catches the filter
  matching on something other than the code we think).
- Identity: each code's division/directorate = consensus over all bulk
  records carrying that code.
- Completeness both ways: codes in bulk data that the sweep missed are
  probed directly; codes the API accepts but bulk never mentions are
  flagged; bulk codes the API refuses are listed prominently (their awards
  would be invisible to our pulls).
- Ground truth: 03040000 must resolve to DMS or nothing is written.

v1 of this script verified identity by scraping showAward HTML; that
parser (written blind - no egress here) failed on every page on CI, so it
was replaced by the bulk-download source above.

Outputs: config/orgs.json + reference/org_registry_report.md (+ debug
dumps under reference/discover_debug/ on parse trouble). The report is
written even when the registry is withheld, so failures are diagnosable.

Usage: python scripts/discover_orgs.py [--dd-max 20] [--vv-max 25]
       [--year-from 2014]
"""

import argparse
import io
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
API = "https://api.nsf.gov/services/v1/awards.json"
BULK = "https://www.nsf.gov/awardsearch/download?DownloadFileName={year}&All=true"
SLEEP = 0.15

WINDOWS = [("10/01/2014", "09/30/2019"), ("10/01/2019", "12/31/2026")]
ACTIVE_SINCE = date(2024, 7, 1)  # newest award on/after this => active unit
SERIES_START = date(2014, 10, 1)

# Display-name canonicalization only (bulk long names are truncated, e.g.
# "Direct For Mathematical & Physical Scien"). Keyed by NSF abbreviation;
# unknown abbreviations fall back to the cleaned bulk long name.
DIRECTORATE_NAMES = {
    "MPS": "Directorate for Mathematical and Physical Sciences",
    "BIO": "Directorate for Biological Sciences",
    "CSE": "Directorate for Computer and Information Science and Engineering",
    "EDU": "Directorate for STEM Education",
    "EHR": "Directorate for Education and Human Resources",
    "ENG": "Directorate for Engineering",
    "GEO": "Directorate for Geosciences",
    "SBE": "Directorate for Social, Behavioral and Economic Sciences",
    "TIP": "Directorate for Technology, Innovation and Partnerships",
    "OD": "Office of the Director",
}

DMS_CODE, DMS_ABBREV = "03040000", "DMS"
DMS_CHECKS = {"min_total": 9000, "max_total": 30000, "max_monthly": 600,
              "baseline": "reference/verified_baseline.json"}

DEBUG_DIR = REPO_ROOT / "reference" / "discover_debug"


def get(url, retries=4, timeout=300, binary=False):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent":
                "science-funding-dashboard org discovery (github.com/jpwolfson)"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
            return data if binary else data.decode("utf-8", "replace")
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)


def api_awards(params):
    time.sleep(SLEEP)
    url = API + "?" + urllib.parse.urlencode(params)
    body = json.loads(get(url, timeout=60))
    return body.get("response", {}).get("award", []) or []


def probe(code, window, fields="id,date"):
    return api_awards({"org_code_div": code, "printFields": fields,
                       "rpp": 25, "dateStart": window[0], "dateEnd": window[1]})


def clean_name(name):
    if not name:
        return None
    name = re.sub(r"\s+", " ", name).strip(" :")
    small = {"of", "the", "and", "for", "in", "on"}
    words = []
    for i, w in enumerate(name.split(" ")):
        lw = w.lower()
        if lw in small and i > 0:
            words.append(lw)
        elif w.isupper() and len(w) <= 5:
            words.append(w)  # acronyms
        else:
            words.append(w[:1].upper() + w[1:].lower() if w else w)
    return " ".join(words)


def parse_award_xml(blob):
    """One bulk per-award XML -> (award_id, eff_date, [org dicts]) or None."""
    try:
        root = ET.fromstring(blob)
    except ET.ParseError:
        return None
    aid_el = root.find(".//AwardID")
    if aid_el is None or not (aid_el.text or "").strip():
        return None
    aid = aid_el.text.strip()
    eff = None
    d_el = root.find(".//AwardEffectiveDate")
    if d_el is not None and d_el.text:
        try:
            t = time.strptime(d_el.text.strip(), "%m/%d/%Y")
            eff = date(t.tm_year, t.tm_mon, t.tm_mday)
        except ValueError:
            pass
    orgs = []
    for org in root.findall(".//Organization"):
        code_el = org.find("Code")
        code = (code_el.text or "").strip() if code_el is not None else ""
        def sub(tag, field):
            el = org.find(f"{tag}/{field}")
            return (el.text or "").strip() if el is not None and el.text else ""
        orgs.append({
            "code": code,
            "dir_abbr": sub("Directorate", "Abbreviation").replace("/", ""),
            "dir_name": sub("Directorate", "LongName"),
            "div_abbr": sub("Division", "Abbreviation").replace("/", ""),
            "div_name": sub("Division", "LongName"),
        })
    return aid, eff, orgs


def load_bulk(years):
    """Download + parse NSF bulk award zips. Returns
    (by_award: id -> [orgs], code_stats: code -> {...}, notes)."""
    by_award = {}
    code_stats = defaultdict(lambda: {"n": 0, "latest": None,
                                      "div": Counter(), "dir": Counter()})
    notes = []
    for year in years:
        url = BULK.format(year=year)
        try:
            blob = get(url, binary=True)
        except Exception as e:
            notes.append(f"bulk {year}: download FAILED ({e})")
            continue
        try:
            zf = zipfile.ZipFile(io.BytesIO(blob))
        except zipfile.BadZipFile:
            notes.append(f"bulk {year}: not a zip ({len(blob)} bytes)")
            DEBUG_DIR.mkdir(parents=True, exist_ok=True)
            (DEBUG_DIR / f"bulk_{year}_head.bin").write_bytes(blob[:4096])
            continue
        parsed = failed = 0
        for name in zf.namelist():
            if not name.lower().endswith(".xml"):
                continue
            rec = parse_award_xml(zf.read(name))
            if rec is None:
                failed += 1
                if failed == 1:
                    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
                    (DEBUG_DIR / f"bulk_{year}_{Path(name).name}").write_bytes(
                        zf.read(name)[:8192])
                continue
            aid, eff, orgs = rec
            parsed += 1
            by_award[aid] = orgs
            for o in orgs:
                if not o["code"]:
                    continue
                st = code_stats[o["code"]]
                st["n"] += 1
                if eff and (st["latest"] is None or eff > st["latest"]):
                    st["latest"] = eff
                if o["div_abbr"] or o["div_name"]:
                    st["div"][(o["div_abbr"], o["div_name"])] += 1
                if o["dir_abbr"] or o["dir_name"]:
                    st["dir"][(o["dir_abbr"], o["dir_name"])] += 1
        print(f"bulk {year}: {parsed} awards parsed, {failed} XML failures")
        if parsed == 0:
            notes.append(f"bulk {year}: zip fetched but 0 awards parsed "
                         f"({failed} failures) - schema drift? sample dumped")
    return by_award, code_stats, notes


def code_identity(code, code_stats):
    """Consensus identity for a code from bulk records.
    Returns (div_abbr, div_name, dir_abbr, dir_name, agreement) or None."""
    st = code_stats.get(code)
    if not st or st["n"] == 0:
        return None
    if st["div"]:
        (div_abbr, div_name), div_n = st["div"].most_common(1)[0]
        agree = div_n / sum(st["div"].values())
    else:
        div_abbr = div_name = ""
        agree = 1.0
    if st["dir"]:
        (dir_abbr, dir_name), _ = st["dir"].most_common(1)[0]
    else:
        dir_abbr = dir_name = ""
    if not div_abbr and not div_name:
        # Office with no division tier: treat the directorate/office itself
        # as the leaf identity.
        div_abbr, div_name = dir_abbr, dir_name
    return div_abbr, div_name, dir_abbr, dir_name, agree


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-") or "unk"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dd-max", type=int, default=20)
    ap.add_argument("--vv-max", type=int, default=25)
    ap.add_argument("--year-from", type=int, default=2014)
    args = ap.parse_args()
    today = date.today()
    report = ["# NSF org registry discovery report", "",
              f"Generated {today.isoformat()} by scripts/discover_orgs.py on CI.",
              ""]
    fatal = None

    # 1. Unknown-code behavior (an adapter guard depends on this finding).
    unk1 = probe("99999999", WINDOWS[0])
    unk2 = probe("03049999", WINDOWS[0])
    unknown_ignored = bool(unk1 or unk2)
    report += ["## Unknown-code behavior", "",
               f"- org_code_div=99999999 over {WINDOWS[0]}: {len(unk1)} records",
               f"- org_code_div=03049999 over {WINDOWS[0]}: {len(unk2)} records",
               f"- **Unknown codes {'are silently IGNORED' if unknown_ignored else 'return empty (filter validates codes)'}**",
               ""]
    print(f"unknown codes ignored: {unknown_ignored}")

    # 2. API existence sweep.
    live = {}
    zero = 0
    for dd in range(1, args.dd_max + 1):
        for vv in range(0, args.vv_max + 1):
            code = f"{dd:02d}{vv:02d}0000"
            samples = []
            for w in WINDOWS:
                try:
                    samples += probe(code, w)
                except Exception as e:
                    print(f"  sweep error {code} {w}: {e}", file=sys.stderr)
            if samples:
                live[code] = samples
                print(f"  {code}: {len(samples)} sample rows")
            else:
                zero += 1
    print(f"sweep: {len(live)} live codes, {zero} empty")

    # 3. Bulk downloads: NSF's own code -> division/directorate mapping.
    years = list(range(args.year_from, today.year + 1))
    by_award, code_stats, bulk_notes = load_bulk(years)
    report += ["## Bulk download source", "",
               f"- Years loaded: {years[0]}..{years[-1]}; "
               f"{len(by_award)} awards parsed; {len(code_stats)} distinct org codes seen"]
    report += [f"- {n}" for n in bulk_notes] + [""]

    # Ground truth gate #1: the bulk parse itself must reproduce DMS.
    dms_ident = code_identity(DMS_CODE, code_stats)
    if not by_award:
        fatal = "bulk download produced no parsed awards; cannot verify anything"
    elif dms_ident is None or dms_ident[0] != DMS_ABBREV:
        fatal = (f"ground truth violated: bulk records resolve {DMS_CODE} to "
                 f"{dms_ident}, expected {DMS_ABBREV}")

    verified, unresolved, anomalies = {}, [], []
    if fatal is None:
        # 4. Verify each API-live code: identity from bulk consensus, plus
        # the param-semantics check on the API's own sample award ids.
        for code, samples in sorted(live.items()):
            ident = code_identity(code, code_stats)
            sample_ids = [str(a["id"]) for a in samples]
            matched = mismatched = 0
            for aid in sample_ids:
                orgs = by_award.get(aid)
                if orgs is None:
                    continue
                if any(o["code"] == code for o in orgs):
                    matched += 1
                else:
                    mismatched += 1
            if ident is None:
                unresolved.append({"code": code, "reason":
                                   "API returns awards but code never appears "
                                   "in bulk records", "samples": sample_ids[:5]})
                continue
            if matched == 0 and mismatched > 0:
                unresolved.append({"code": code, "reason":
                                   f"param semantics FAILED: 0/{mismatched} "
                                   "sampled awards carry this code in bulk "
                                   "records", "samples": sample_ids[:5]})
                continue
            div_abbr, div_name, dir_abbr, dir_name, agree = ident
            if agree < 0.9:
                anomalies.append(f"{code}: division consensus only {agree:.0%}")
            st = code_stats[code]
            verified[code] = {
                "abbrev": div_abbr or f"U{code[:4]}",
                "name": clean_name(div_name) or f"NSF org {code}",
                "dir_abbr": dir_abbr or "OD",
                "dir_name": clean_name(dir_name) or "",
                "bulk_n": st["n"],
                "sem_ok": matched,
                "active": bool(st["latest"] and st["latest"] >= ACTIVE_SINCE),
                "latest": st["latest"].isoformat() if st["latest"] else "?",
            }
            print(f"  verified {code} -> {verified[code]['abbrev']} "
                  f"({verified[code]['name']}) dir={dir_abbr} "
                  f"bulk_n={st['n']} sem={matched}/{matched + mismatched} "
                  f"active={verified[code]['active']}")

        # 5. Completeness, both directions.
        bulk_recent = {c for c, st in code_stats.items()
                       if st["latest"] and st["latest"] >= SERIES_START
                       and re.fullmatch(r"\d{8}", c)}
        missed = sorted(bulk_recent - set(live))
        not_queryable = []
        for code in missed:
            hits = []
            for w in WINDOWS:
                try:
                    hits += probe(code, w, fields="id")
                except Exception:
                    pass
            if hits:
                ident = code_identity(code, code_stats)
                if ident:
                    div_abbr, div_name, dir_abbr, dir_name, _ = ident
                    st = code_stats[code]
                    verified[code] = {
                        "abbrev": div_abbr or f"U{code[:4]}",
                        "name": clean_name(div_name) or f"NSF org {code}",
                        "dir_abbr": dir_abbr or "OD",
                        "dir_name": clean_name(dir_name) or "",
                        "bulk_n": st["n"], "sem_ok": 0,
                        "active": bool(st["latest"] and st["latest"] >= ACTIVE_SINCE),
                        "latest": st["latest"].isoformat() if st["latest"] else "?",
                    }
                    anomalies.append(f"{code}: found only via bulk (sweep "
                                     "missed it); added after direct probe")
            else:
                st = code_stats[code]
                not_queryable.append(
                    f"{code} ({code_identity(code, code_stats) or '?'}, "
                    f"{st['n']} bulk awards, latest {st['latest']}): API "
                    "returns nothing for org_code_div - THESE AWARDS ARE "
                    "INVISIBLE TO OUR PULLS")

        # Ground truth gate #2 on the final assembly.
        if DMS_CODE not in verified or verified[DMS_CODE]["abbrev"] != DMS_ABBREV:
            fatal = (f"ground truth violated in final assembly: {DMS_CODE} -> "
                     f"{verified.get(DMS_CODE)}")
        elif len(verified) < 15:
            fatal = (f"only {len(verified)} codes verified - NSF has far more "
                     "divisions; refusing to write a registry that would "
                     "silently omit most of NSF")

    # 6. Assemble config (only when nothing fatal).
    if fatal is None:
        groups = defaultdict(list)
        for code, v in sorted(verified.items()):
            groups[v["dir_abbr"]].append(code)
        directorates_out = []
        for dir_abbr in sorted(groups):
            codes = groups[dir_abbr]
            dir_name = DIRECTORATE_NAMES.get(dir_abbr)
            if dir_name is None:
                dir_name = next((verified[c]["dir_name"] for c in codes
                                 if verified[c]["dir_name"]),
                                f"NSF unit {dir_abbr}")
                anomalies.append(f"directorate {dir_abbr!r} not in the "
                                 "canonical name table; using bulk long name")
            prefixes = {c[:2] for c in codes}
            if len(prefixes) > 1:
                anomalies.append(f"directorate {dir_abbr} spans code prefixes "
                                 f"{sorted(prefixes)}")
            divisions = []
            seen_slugs = {}
            for code in codes:
                v = verified[code]
                leaf = {"slug": slugify(v["abbrev"]), "abbrev": v["abbrev"],
                        "name": v["name"], "params": {"org_code_div": code},
                        "active": v["active"]}
                if not v["active"]:
                    leaf["note"] = (f"No awards after {v['latest']}; "
                                    "likely renamed or dissolved.")
                if code == DMS_CODE:
                    leaf["checks"] = DMS_CHECKS
                if leaf["slug"] in seen_slugs:
                    leaf["slug"] = f"{leaf['slug']}-{code[:4]}"
                    anomalies.append(f"slug collision in {dir_abbr}: {code} "
                                     f"renamed to {leaf['slug']}")
                seen_slugs[leaf["slug"]] = True
                divisions.append(leaf)
            directorates_out.append({"slug": slugify(dir_abbr),
                                     "abbrev": dir_abbr, "name": dir_name,
                                     "divisions": divisions})
        cfg = {"seriesStart": "2014-10-01",
               "defaults": {"max_monthly": 1500, "min_total": 0,
                            "max_total": 200000},
               "agencies": [{"slug": "nsf", "abbrev": "NSF",
                             "name": "U.S. National Science Foundation",
                             "adapter": "nsf",
                             "directorates": directorates_out}]}
        if unresolved:
            cfg["unresolved"] = unresolved
        (REPO_ROOT / "config").mkdir(exist_ok=True)
        (REPO_ROOT / "config" / "orgs.json").write_text(json.dumps(cfg, indent=1))

    # 7. Report (always written, even on fatal).
    report += ["## Verified codes", "",
               "| code | abbrev | division | directorate | bulk awards | "
               "param-check | latest award | active |",
               "|---|---|---|---|---|---|---|---|"]
    for code, v in sorted(verified.items()):
        report.append(f"| {code} | {v['abbrev']} | {v['name']} | "
                      f"{v['dir_abbr']} | {v['bulk_n']} | {v['sem_ok']} | "
                      f"{v['latest']} | {v['active']} |")
    report += ["", f"## Unresolved codes ({len(unresolved)})", ""]
    report += [f"- {u['code']}: {u['reason']} (samples {u['samples']})"
               for u in unresolved] or ["- none"]
    if fatal is None:
        report += ["", f"## Bulk codes not queryable via the API "
                   f"({len(not_queryable)})", ""]
        report += [f"- {n}" for n in not_queryable] or ["- none"]
    report += ["", "## Stats", "",
               f"- Sweep: dd 01..{args.dd_max:02d} x vv 00..{args.vv_max:02d}; "
               f"{len(live)} live, {zero} empty",
               f"- Verified into registry: {len(verified)}",
               "", "## Anomalies", ""]
    report += [f"- {a}" for a in anomalies] or ["- none"]
    if fatal:
        report = report[:4] + [f"**FATAL: {fatal} - config/orgs.json NOT "
                               "written.**", ""] + report[4:]
    (REPO_ROOT / "reference" / "org_registry_report.md").write_text(
        "\n".join(report) + "\n")

    if fatal:
        sys.exit(f"FATAL: {fatal}")
    print(f"Wrote config/orgs.json: {len(verified)} divisions across "
          f"{len(directorates_out)} directorates; {len(unresolved)} unresolved; "
          f"{len(not_queryable)} bulk-only codes not queryable")


if __name__ == "__main__":
    main()
