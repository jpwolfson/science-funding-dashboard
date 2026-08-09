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
# NSF redesigned Award Search in 2025 (bulk files converted XML -> JSON
# 2025-01) and the legacy download endpoint now serves a redirect stub to
# non-browser clients, so bulk zip URLs are RESOLVED at runtime from the
# download page itself (see resolve_bulk_urls), with these as fallbacks.
DOWNLOAD_PAGES = [
    "https://www.nsf.gov/awardsearch/download.jsp",
    "https://nsf.gov/awardsearch/download.jsp",
    "https://www.nsf.gov/awardsearch/download",
]
BULK_FALLBACK = "https://www.nsf.gov/awardsearch/download?DownloadFileName={year}&All=true"
BROWSER_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
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


def get(url, retries=4, timeout=300, binary=False, ua=None):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": ua or "science-funding-dashboard org discovery "
                                    "(github.com/jpwolfson)",
                "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
            return data if binary else data.decode("utf-8", "replace")
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)


def dir_abbr_from_name(name):
    """Map a scraped directorate name to a canonical abbrev by token
    overlap (bulk/detail names are often truncated). None if no match."""
    stop = {"directorate", "direct", "for", "of", "the", "and", "&"}
    nt = {w[:6] for w in re.findall(r"[a-z&]+", (name or "").lower())
          if w not in stop}
    if not nt:
        return None
    if "office of the director" in (name or "").lower():
        return "OD"
    best = None
    for ab, full in DIRECTORATE_NAMES.items():
        ft = {w[:6] for w in re.findall(r"[a-z&]+", full.lower()) if w not in stop}
        if not ft:
            continue
        score = len(nt & ft) / len(nt)
        if score >= 0.5 and (best is None or score > best[0]):
            best = (score, ab)
    return best[1] if best else None


def derived_abbrev(div_name):
    """Initials fallback when no abbreviation field exists (flagged in the
    report; NSF's official abbrev may differ, this only affects slugs)."""
    words = [w for w in re.findall(r"[A-Za-z]+", div_name or "")
             if w.lower() not in {"of", "the", "and", "for"}]
    return "".join(w[0].upper() for w in words)[:5] or None


def resolve_bulk_urls(years, notes, extra=()):
    """Locate the per-year bulk zip URLs from NSF's own download page.
    Returns {year: url}. Every attempt is logged into notes."""
    hrefs = [u for u in extra if re.search(r"download|\.zip", u, re.I)]
    for page_url in DOWNLOAD_PAGES:
        try:
            page = get(page_url, ua=BROWSER_UA, timeout=60)
        except Exception as e:
            notes.append(f"download page {page_url}: fetch failed ({e})")
            continue
        found = re.findall(r"""href=["']([^"']*(?:[Dd]ownload|\.zip)[^"']*)["']""",
                           page)
        notes.append(f"download page {page_url}: {len(page)} bytes, "
                     f"{len(found)} download-ish hrefs")
        if found:
            hrefs += [urllib.parse.urljoin(page_url, h) for h in found]
            break
        DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        (DEBUG_DIR / f"download_page_{urllib.parse.quote(page_url, safe='')[:60]}.html"
         ).write_text(page[:16384])
    year_urls = {}
    for y in years:
        # Prefer a scraped link that names the year; else the legacy pattern.
        candidates = [h for h in hrefs if str(y) in h]
        year_urls[y] = candidates[0] if candidates else BULK_FALLBACK.format(year=y)
    if hrefs:
        sample = [h for h in hrefs[:8]]
        notes.append("scraped hrefs sample: " + "; ".join(sample))
    else:
        notes.append("no hrefs scraped; using legacy URL pattern with "
                     "browser User-Agent for all years")
    return year_urls


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


def scan_spa_for_endpoints(notes):
    """The redesigned Award Search is a JS app; its bundles reference the
    real data endpoints (award detail API, bulk zip locations). Fetch the
    app shell + bundles and harvest endpoint-ish URLs. Everything found is
    logged; heads are dumped for offline diagnosis."""
    found = set()
    for page_url in ["https://www.nsf.gov/awardsearch/simple-search",
                     "https://www.nsf.gov/funding/award-search"]:
        try:
            page = get(page_url, ua=BROWSER_UA, timeout=60)
        except Exception as e:
            notes.append(f"spa {page_url}: fetch failed ({e})")
            continue
        notes.append(f"spa {page_url}: {len(page)} bytes")
        DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        (DEBUG_DIR / ("spa_" + re.sub(r"[^a-z0-9]+", "_", page_url[8:])[:50] + ".html")
         ).write_text(page[:16384])
        found.update(re.findall(r"https?://[^\s\"'<>\\]+", page))
        srcs = re.findall(r"""(?:src|href)=["']([^"']+\.m?js[^"']*)["']""", page)
        for s in srcs[:12]:
            u = urllib.parse.urljoin(page_url, s)
            try:
                js = get(u, ua=BROWSER_UA, timeout=120)
            except Exception:
                continue
            hits = set()
            for mm in re.findall(
                    r"""["'`](https?://[^"'`\s]{8,200}|/[A-Za-z0-9_\-./]{3,120}"""
                    r"""(?:api|award|download|zip|search)[A-Za-z0-9_\-./?=&{}:]{0,80})["'`]""",
                    js):
                if re.search(r"api|award|download|zip", mm, re.I):
                    hits.add(urllib.parse.urljoin(u, mm))
            notes.append(f"bundle {u}: {len(js)} bytes, {len(hits)} endpoint-ish strings")
            found.update(hits)
    interesting = sorted(h for h in found
                         if re.search(r"api|award|download|zip", h, re.I)
                         and "w3.org" not in h and "schema.org" not in h)
    if interesting:
        DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        (DEBUG_DIR / "spa_endpoints.txt").write_text("\n".join(interesting))
        notes.append(f"spa scan: {len(interesting)} candidate endpoints "
                     "(full list in discover_debug/spa_endpoints.txt); "
                     "sample: " + "; ".join(interesting[:6]))
    else:
        notes.append("spa scan: no candidate endpoints found")
    return interesting


DETAIL_ENDPOINTS = [
    "https://api.nsf.gov/services/v1/awards/{id}.json",
    "https://www.research.gov/awardapi-service/v1/awards/{id}.json",
]
EXTRA_FIELDS = ("id,date,title,transType,fundProgramName,primaryProgram,"
                "division,divisionCode,directorate,directorateCode,orgCode,"
                "fundOrg,nsfOrganization,awardAgencyCode,fundAgencyCode")


def strings_in(obj, path=""):
    """Yield (json_path, string_value) for every string in a JSON tree."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from strings_in(v, f"{path}.{k}" if path else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from strings_in(v, f"{path}[{i}]")
    elif isinstance(obj, str):
        yield path, obj


def award_org_fields(detail_json):
    """Org identity from an award-detail record. The api.nsf.gov detail
    endpoint (confirmed from a committed raw dump, run 4) carries explicit
    fields: divAbbr, dirAbbr, orgCodeDiv, orgCodeDir, orgLongName
    (directorate), orgLongName2 (division). Falls back to value-pattern
    scanning for unexpected shapes. Returns a dict or None."""
    recs = detail_json
    if isinstance(detail_json, dict):
        recs = (detail_json.get("response", {}) or {}).get("award") or detail_json
    if isinstance(recs, dict):
        recs = [recs]
    if not isinstance(recs, list) or not recs or not isinstance(recs[0], dict):
        return None
    a = recs[0]
    out = {
        "div_abbr": str(a.get("divAbbr") or "").strip().replace("/", "") or None,
        "div_name": str(a.get("orgLongName2") or "").strip() or None,
        "dir_abbr": str(a.get("dirAbbr") or "").strip().replace("/", "") or None,
        "dir_name": str(a.get("orgLongName") or "").strip() or None,
        "org_code_div": str(a.get("orgCodeDiv") or "").strip() or None,
        "date": str(a.get("date") or "").strip() or None,
    }
    if out["div_abbr"] or out["div_name"] or out["org_code_div"]:
        return out
    # Fallback: value-pattern scan (kept for endpoint-shape drift).
    div_name = dir_name = div_abbr = None
    for path, s in strings_in(detail_json):
        sv, low, pl = s.strip(), s.strip().lower(), path.lower()
        if div_name is None and re.match(r"(division|office) of .{3,}", low) \
                and "director" not in low:
            div_name = sv
        if dir_name is None and ("directorate" in low or
                                 re.match(r"direct for .{3,}", low) or
                                 low.startswith("office of the director")):
            dir_name = sv
        if div_abbr is None and re.fullmatch(r"[A-Z]{2,5}", sv) \
                and re.search(r"abbr|org|div", pl) and "dir" not in pl:
            div_abbr = sv
    if div_abbr or div_name:
        return {"div_abbr": div_abbr, "div_name": div_name, "dir_abbr": None,
                "dir_name": dir_name, "org_code_div": None, "date": None}
    return None


def probe_detail_endpoints(sample_id, extra_candidates, notes):
    """Find a per-award detail source that exposes division/directorate.
    Returns a fetch(id)->json callable or None. Raw heads are dumped."""
    candidates = list(DETAIL_ENDPOINTS)
    candidates.append(DETAIL_ENDPOINTS[0] + "?printFields=" + EXTRA_FIELDS)
    for c in extra_candidates:
        if "{id}" in c or re.search(r"award", c, re.I):
            t = c if "{id}" in c else None
            if t is None and re.search(r"[?&](awd_id|id|awardId)=", c):
                t = re.sub(r"([?&](?:awd_id|id|awardId))=[^&]*", r"\1={id}", c)
            if t:
                candidates.append(t)
    tried = []
    for tmpl in candidates[:12]:
        url = tmpl.replace("{id}", str(sample_id))
        try:
            body = get(url, ua=BROWSER_UA, timeout=60)
        except Exception as e:
            tried.append(f"{tmpl} -> fetch failed ({e})")
            continue
        DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        (DEBUG_DIR / ("detail_" + re.sub(r"[^a-z0-9]+", "_", tmpl[8:])[:60] + ".json")
         ).write_text(body[:8192])
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            tried.append(f"{tmpl} -> non-JSON ({len(body)} bytes)")
            continue
        f = award_org_fields(data) or {}
        abbr, div = f.get("div_abbr"), f.get("div_name")
        tried.append(f"{tmpl} -> JSON, identity=({abbr}, {div}, "
                     f"{f.get('dir_abbr')}, code={f.get('org_code_div')})")
        if abbr == DMS_ABBREV or (div and "mathematical" in div.lower()):
            notes.append(f"detail endpoint SELECTED: {tmpl}")
            notes.extend(f"detail probe: {t}" for t in tried)

            def fetch_detail(aid, _tmpl=tmpl):
                time.sleep(SLEEP)
                return json.loads(get(_tmpl.replace("{id}", str(aid)),
                                      ua=BROWSER_UA, timeout=60))
            return fetch_detail
    notes.extend(f"detail probe: {t}" for t in tried)
    return None


def parse_award_json(obj):
    """One award record from a post-2025-01 bulk JSON file ->
    (award_id, eff_date, [org dicts]) or None. Known schema keys:
    awd_id, org_code, dir_abbr, org_dir_long_name, div_abbr,
    org_div_long_name, awd_eff_date."""
    if not isinstance(obj, dict):
        return None
    aid = str(obj.get("awd_id") or obj.get("AwardID") or "").strip()
    if not aid:
        return None
    eff = None
    for k in ("awd_eff_date", "awd_effective_date", "AwardEffectiveDate"):
        v = obj.get(k)
        if v:
            try:
                t = time.strptime(str(v).strip(), "%m/%d/%Y")
                eff = date(t.tm_year, t.tm_mon, t.tm_mday)
                break
            except ValueError:
                pass
    org = {
        "code": str(obj.get("org_code") or "").strip(),
        "dir_abbr": str(obj.get("dir_abbr") or "").strip().replace("/", ""),
        "dir_name": str(obj.get("org_dir_long_name") or "").strip(),
        "div_abbr": str(obj.get("div_abbr") or "").strip().replace("/", ""),
        "div_name": str(obj.get("org_div_long_name") or "").strip(),
    }
    if not any(org.values()):
        return None
    return aid, eff, [org]


def parse_bulk_entry(name, blob):
    """A zip member -> list of (award_id, eff, orgs). Handles per-award XML,
    per-award JSON, and whole-year JSON arrays."""
    low = name.lower()
    if low.endswith(".xml"):
        rec = parse_award_xml(blob)
        return [rec] if rec else []
    if low.endswith(".json"):
        try:
            data = json.loads(blob.decode("utf-8", "replace"))
        except json.JSONDecodeError:
            return []
        objs = data if isinstance(data, list) else [data]
        out = []
        for obj in objs:
            rec = parse_award_json(obj)
            if rec:
                out.append(rec)
        return out
    return []


def load_bulk(year_urls):
    """Download + parse NSF bulk award zips. Returns
    (by_award: id -> [orgs], code_stats: code -> {...}, notes)."""
    by_award = {}
    code_stats = defaultdict(lambda: {"n": 0, "latest": None,
                                      "div": Counter(), "dir": Counter()})
    notes = []
    for year, url in sorted(year_urls.items()):
        try:
            blob = get(url, binary=True, ua=BROWSER_UA)
        except Exception as e:
            notes.append(f"bulk {year}: download FAILED ({e}) [{url}]")
            continue
        try:
            zf = zipfile.ZipFile(io.BytesIO(blob))
        except zipfile.BadZipFile:
            notes.append(f"bulk {year}: not a zip ({len(blob)} bytes) [{url}]")
            DEBUG_DIR.mkdir(parents=True, exist_ok=True)
            (DEBUG_DIR / f"bulk_{year}_head.bin").write_bytes(blob[:4096])
            continue
        parsed = failed = 0
        for name in zf.namelist():
            blob_e = zf.read(name)
            recs = parse_bulk_entry(name, blob_e)
            if not recs and name.lower().endswith((".xml", ".json")):
                failed += 1
                if failed == 1:
                    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
                    (DEBUG_DIR / f"bulk_{year}_{Path(name).name}"
                     ).write_bytes(blob_e[:8192])
                continue
            for aid, eff, orgs in recs:
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
        print(f"bulk {year}: {parsed} awards parsed, {failed} entry failures")
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
    bulk_notes = []
    spa_candidates = scan_spa_for_endpoints(bulk_notes)
    year_urls = resolve_bulk_urls(years, bulk_notes, extra=spa_candidates)
    by_award, code_stats, load_notes = load_bulk(year_urls)
    bulk_notes += load_notes
    report += ["## Bulk download source", "",
               f"- Years loaded: {years[0]}..{years[-1]}; "
               f"{len(by_award)} awards parsed; {len(code_stats)} distinct org codes seen"]
    report += [f"- {n}" for n in bulk_notes] + [""]

    mode = None
    fetch_detail = None
    if by_award:
        # Ground truth gate #1: the bulk parse must reproduce DMS, both by
        # code consensus and on known DMS award ids from our verified store.
        dms_ident = code_identity(DMS_CODE, code_stats)
        if dms_ident is None or dms_ident[0] != DMS_ABBREV:
            fatal = (f"ground truth violated: bulk records resolve {DMS_CODE} "
                     f"to {dms_ident}, expected {DMS_ABBREV}")
        else:
            mode = "bulk"
            store_csv = REPO_ROOT / "data" / "nsf" / "mps" / "dms" / "awards.csv"
            if store_csv.exists():
                import csv as _csv
                with open(store_csv, newline="") as fh:
                    store_ids = [row["id"] for row in _csv.DictReader(fh)]
                hits = wrong = 0
                for aid in store_ids:
                    orgs = by_award.get(str(aid))
                    if orgs is None:
                        continue
                    if any(o["code"] == DMS_CODE or o["div_abbr"] == DMS_ABBREV
                           for o in orgs):
                        hits += 1
                    else:
                        wrong += 1
                report += [f"- DMS store cross-check: {hits} of {len(store_ids)} "
                           f"verified store awards matched in bulk as DMS; "
                           f"{wrong} matched with a DIFFERENT org", ""]
                if hits < 100 or wrong > hits * 0.02:
                    fatal = (f"ground truth violated: DMS store cross-check "
                             f"hits={hits} wrong={wrong}")
                    mode = None
    if fatal is None and mode is None:
        # No usable bulk source: fall back to a per-award detail endpoint,
        # located empirically and gated on the DMS ground truth.
        dms_sample = None
        store_csv = REPO_ROOT / "data" / "nsf" / "mps" / "dms" / "awards.csv"
        if store_csv.exists():
            import csv as _csv
            with open(store_csv, newline="") as fh:
                rows = list(_csv.DictReader(fh))
            if rows:
                dms_sample = rows[-1]["id"]
        if dms_sample is None and DMS_CODE in live:
            dms_sample = live[DMS_CODE][0]["id"]
        fetch_detail = probe_detail_endpoints(dms_sample, spa_candidates,
                                              bulk_notes)
        if fetch_detail is None:
            fatal = ("no bulk zips reachable and no award-detail endpoint "
                     "exposing division info; see reference/discover_debug/")
        else:
            mode = "detail"
    report += [f"**Verification source: {mode or 'NONE'}**", ""]

    verified, unresolved, anomalies = {}, [], []
    not_queryable = []
    if fatal is None and mode == "detail":
        # Verify each API-live code by fetching a few of its own sample
        # awards' detail records. Identity = value-pattern extraction,
        # trusted only because the DMS ground-truth id resolved correctly.
        for code, samples in sorted(live.items()):
            ids = [str(a["id"]) for a in samples]
            picks = list(dict.fromkeys(
                [ids[0], ids[len(ids) // 3], ids[2 * len(ids) // 3], ids[-1]]))
            fields, sem_ok, sem_bad, latest = [], 0, 0, None
            for aid in picks:
                try:
                    data = fetch_detail(aid)
                except Exception as e:
                    print(f"  detail {aid} failed: {e}", file=sys.stderr)
                    continue
                f = award_org_fields(data)
                if f is None:
                    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
                    (DEBUG_DIR / f"unresolved_{code}_{aid}.json").write_text(
                        json.dumps(data)[:8192])
                    continue
                fields.append(f)
                if f["org_code_div"] == code:
                    sem_ok += 1
                elif f["org_code_div"]:
                    sem_bad += 1
                if f["date"]:
                    latest = max(latest or f["date"][-4:] + f["date"][:5],
                                 f["date"][-4:] + f["date"][:5])
            names = Counter((f["div_abbr"], f["div_name"]) for f in fields
                            if f["div_abbr"] or f["div_name"])
            if not names:
                unresolved.append({"code": code, "reason":
                                   "no detail record exposed org fields "
                                   "(raw samples dumped)", "samples": picks})
                continue
            if sem_ok == 0 and sem_bad > 0:
                unresolved.append({"code": code, "reason":
                                   f"param semantics FAILED: sampled awards "
                                   f"carry orgCodeDiv != {code}",
                                   "samples": picks})
                continue
            (div_abbr, div_name), div_n = names.most_common(1)[0]
            if div_n < max(1, len(fields) * 0.75):
                anomalies.append(f"{code}: division consensus only "
                                 f"{div_n}/{len(fields)}")
            if not div_abbr:
                div_abbr = derived_abbrev(div_name) or f"U{code[:4]}"
                anomalies.append(f"{code}: no abbreviation field; derived "
                                 f"'{div_abbr}' from name initials")
            dir_ab = next((f["dir_abbr"] for f in fields if f["dir_abbr"]), None)
            dir_name = next((f["dir_name"] for f in fields if f["dir_name"]), "")
            if not dir_ab:
                dir_ab = dir_abbr_from_name(dir_name) or "OD"
            # Active flags cannot be derived reliably here (run 4's
            # recent-window probes inexplicably returned empty for every
            # code); ship all-active and derive flags from our own pulled
            # award data after the backfill.
            verified[code] = {"abbrev": div_abbr,
                              "name": clean_name(div_name) or f"NSF org {code}",
                              "dir_abbr": dir_ab,
                              "dir_name": clean_name(dir_name) or "",
                              "bulk_n": 0, "sem_ok": sem_ok,
                              "active": True,
                              "latest": latest or "?"}
            print(f"  verified {code} -> {div_abbr} ({div_name}) dir={dir_ab} "
                  f"sem={sem_ok}/{len(picks)} latest={latest}")
        if DMS_CODE not in verified or \
                verified[DMS_CODE]["abbrev"] != DMS_ABBREV or \
                "mathematical" not in verified[DMS_CODE]["name"].lower():
            fatal = (f"ground truth violated (detail mode): {DMS_CODE} -> "
                     f"{verified.get(DMS_CODE)}")
        elif len(verified) < 15:
            fatal = (f"only {len(verified)} codes verified via detail mode; "
                     "refusing to write a mostly-empty registry")
        else:
            anomalies.append("detail mode: active flags NOT derived (set "
                             "true everywhere); regenerate from pulled award "
                             "data post-backfill")
            anomalies.append("detail mode: bulk-side completeness check not "
                             "available (no bulk code universe to compare)")

    if fatal is None and mode == "bulk":
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
                    leaf["note"] = ("No recent awards"
                                    + (f" after {v['latest']}" if v["latest"] != "?" else "")
                                    + "; likely renamed or dissolved.")
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
