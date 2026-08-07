#!/usr/bin/env python3
"""Empirically discover and verify the NSF org registry (config/orgs.json).

Runs on CI (the interactive session cannot reach api.nsf.gov). Protocol:

1. Probe how the API treats unknown org codes (an adapter guard depends on
   whether unknown codes return empty or are silently ignored).
2. Sweep candidate 8-digit codes DDVV0000 (DD=directorate, VV=division —
   pattern confirmed by DMS = 03040000) with two existence windows spanning
   FY2015..present. Existence only; the API's pagination faults don't
   matter here.
3. For every code with awards, verify code -> org identity from NSF's own
   award pages (awardsearch/showAward), which state the awarding org's
   abbreviation and division/directorate names. A code is included ONLY if
   its sampled award pages agree. Nothing is taken from memory except
   display-name canonicalization for well-known directorates, and that is
   validated against the scraped names.
4. Classify active/inactive by a recent-awards probe.

Outputs: config/orgs.json + reference/org_registry_report.md. On parsing
failure, raw sample pages are dumped under reference/discover_debug/ so the
parser can be fixed without re-running the sweep blind.

Usage: python scripts/discover_orgs.py [--dd-max 20] [--vv-max 25]
"""

import argparse
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
API = "https://api.nsf.gov/services/v1/awards.json"
SHOW = "https://www.nsf.gov/awardsearch/showAward?AWD_ID="
SLEEP = 0.15

# Existence windows (dateStart, dateEnd) covering the series.
WINDOWS = [("10/01/2014", "09/30/2019"), ("10/01/2019", "12/31/2026")]
RECENT = ("07/01/2024", "12/31/2026")

# Display-name canonicalization only. Membership and codes are empirical;
# each canonical match is validated against the scraped directorate string.
DIRECTORATES = {
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
STOPWORDS = {"directorate", "direct", "for", "of", "the", "and", "&", "dir",
             "office", "sciences", "science", "scien"}

# The DMS ground truth: discovery must reproduce this or abort.
DMS_CODE, DMS_ABBREV = "03040000", "DMS"
DMS_CHECKS = {"min_total": 9000, "max_total": 30000, "max_monthly": 600,
              "baseline": "reference/verified_baseline.json"}


def get(url, retries=4, timeout=60):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent":
                "science-funding-dashboard org discovery (github.com/jpwolfson)"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", "replace")
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)


def api_awards(params):
    time.sleep(SLEEP)
    url = API + "?" + urllib.parse.urlencode(params)
    body = json.loads(get(url))
    return body.get("response", {}).get("award", []) or []


def probe(code, window, fields="id,date"):
    return api_awards({"org_code_div": code, "printFields": fields,
                       "rpp": 25, "dateStart": window[0], "dateEnd": window[1]})


def strip_tags(page):
    return html.unescape(re.sub(r"<[^>]+>", "\n", page))


def parse_show_award(page_text):
    """Extract (org_abbrev, division_name, directorate_name) from a
    showAward page. Returns None on failure. Written defensively against
    markup drift: works on tag-stripped text lines."""
    text = strip_tags(page_text)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    abbrev = div_name = dir_name = None
    for i, ln in enumerate(lines):
        low = ln.lower().rstrip(":")
        nxt = lines[i + 1:i + 4]
        if low in ("nsf org", "nsf organization") and nxt:
            m = re.match(r"^([A-Z]{2,5}[0-9]?)$", nxt[0])
            if m:
                abbrev = m.group(1)
            # Division long name often follows the abbreviation.
            for cand in nxt:
                if re.search(r"(division|office|div\b|off\b)", cand, re.I) \
                        and not re.search(r"director", cand, re.I):
                    div_name = cand
                    break
        if re.match(r"^(division|div)\b", low) and div_name is None:
            for cand in nxt:
                if len(cand) > 3 and not cand.endswith(":"):
                    div_name = cand
                    break
        if re.match(r"^(directorate|direct for|dir\b)", low) or "director" in low.split(":")[0]:
            for cand in ([ln] + nxt):
                if re.search(r"(direct|office of the director)", cand, re.I) and len(cand) > 8:
                    dir_name = cand
                    break
    # Fallback pattern scan over the whole text.
    if div_name is None:
        m = re.search(r"^(Division [Oo]f .{3,60}|Office [Oo]f .{3,60}|"
                      r"Div [Oo]f .{3,60}|OSI .{0,40})$", text, re.M)
        if m:
            div_name = m.group(1).strip()
    if dir_name is None:
        m = re.search(r"^(Direct(?:orate)? [Ff]or .{3,60}|Office [Oo]f [Tt]he Director.{0,20})$",
                      text, re.M)
        if m:
            dir_name = m.group(1).strip()
    if abbrev is None and div_name is None:
        return None
    return abbrev, clean_name(div_name), clean_name(dir_name)


def clean_name(name):
    if not name:
        return None
    name = re.sub(r"\s+", " ", name).strip(" : ")
    small = {"of", "the", "and", "for", "in", "on"}
    words = []
    for i, w in enumerate(name.split(" ")):
        lw = w.lower()
        words.append(lw if (lw in small and i > 0) else (w if w.isupper() and len(w) <= 5 else w.capitalize()))
    return " ".join(words)


def tokens(s):
    return {w for w in re.findall(r"[a-z&]+", (s or "").lower()) if w not in STOPWORDS}


def match_directorate(scraped_name):
    """Map a scraped directorate string to a canonical entry, validated by
    token overlap. Returns (abbrev, canonical_name) or None."""
    st = tokens(scraped_name)
    if not st:
        return None
    if "director" in (scraped_name or "").lower() and not st - {"office"}:
        return "OD", DIRECTORATES["OD"]
    best = None
    for ab, full in DIRECTORATES.items():
        ft = tokens(full)
        if not ft:
            continue
        # Truncated scrapes ("...Physical Scien"): prefix-match tokens.
        hits = sum(1 for t in st if any(f.startswith(t[:6]) or t.startswith(f[:6]) for f in ft))
        score = hits / max(1, len(st))
        if score >= 0.6 and (best is None or score > best[0]):
            best = (score, ab, full)
    return (best[1], best[2]) if best else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dd-max", type=int, default=20)
    ap.add_argument("--vv-max", type=int, default=25)
    args = ap.parse_args()
    today = date.today()
    debug_dir = REPO_ROOT / "reference" / "discover_debug"
    report = ["# NSF org registry discovery report", "",
              f"Generated {today.isoformat()} by scripts/discover_orgs.py on CI.", ""]

    # 1. Unknown-code behavior.
    unk1 = probe("99999999", WINDOWS[0])
    unk2 = probe("03049999", WINDOWS[0])
    unknown_ignored = bool(unk1 or unk2)
    report += ["## Unknown-code behavior", "",
               f"- org_code_div=99999999 over {WINDOWS[0]}: {len(unk1)} records",
               f"- org_code_div=03049999 over {WINDOWS[0]}: {len(unk2)} records",
               f"- **Unknown codes {'are silently IGNORED (filter cannot validate codes)' if unknown_ignored else 'return empty (filter validates codes)'}**", ""]
    print(f"unknown codes ignored: {unknown_ignored}")

    # 2. Existence sweep.
    live = {}   # code -> [sample awards]
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
    if unknown_ignored and len(live) > (args.dd_max * (args.vv_max + 1)) * 0.8:
        sys.exit("FATAL: nearly every candidate code returned data - the org "
                 "filter is being ignored wholesale; discovery impossible.")

    # 3. Verify each live code via showAward pages.
    verified, unresolved, parse_failures = {}, [], 0
    for code, samples in sorted(live.items()):
        # Sample up to 3 award ids spread across the returned rows.
        ids = [a["id"] for a in samples]
        picks = sorted(set(ids[i] for i in {0, len(ids) // 2, len(ids) - 1}))
        idents = []
        for aid in picks:
            try:
                time.sleep(SLEEP)
                page = get(SHOW + urllib.parse.quote(str(aid)))
                ident = parse_show_award(page)
                if ident is None:
                    parse_failures += 1
                    debug_dir.mkdir(parents=True, exist_ok=True)
                    (debug_dir / f"{code}_{aid}.html").write_text(page)
                else:
                    idents.append(ident)
            except Exception as e:
                print(f"  showAward {aid} failed: {e}", file=sys.stderr)
        abbrevs = {i[0] for i in idents if i[0]}
        if not idents or len(abbrevs) > 1:
            unresolved.append({"code": code, "reason":
                               "no parsable samples" if not idents else
                               f"samples disagree: {sorted(abbrevs)}",
                               "sample_ids": picks})
            continue
        abbrev = (abbrevs.pop() if abbrevs else f"U{code[:4]}")
        div_name = next((i[1] for i in idents if i[1]), None) or f"NSF org {code}"
        dir_name = next((i[2] for i in idents if i[2]), None)
        try:
            recent = probe(code, RECENT, fields="id")
        except Exception:
            recent = []
        verified[code] = {"abbrev": abbrev, "name": div_name,
                          "dir_scraped": dir_name, "sample_ids": picks,
                          "active": bool(recent)}
        print(f"  verified {code} -> {abbrev} ({div_name}) dir={dir_name} "
              f"active={bool(recent)}")

    if DMS_CODE not in verified or verified[DMS_CODE]["abbrev"] != DMS_ABBREV:
        sys.exit(f"FATAL: ground truth violated - {DMS_CODE} resolved to "
                 f"{verified.get(DMS_CODE)}, expected {DMS_ABBREV}. "
                 "Parser or API is untrustworthy; refusing to write registry.")
    if len(verified) < 15:
        sys.exit(f"FATAL: only {len(verified)} codes verified - NSF has far "
                 "more divisions; parser is likely broken (see "
                 "reference/discover_debug/). Refusing to write a registry "
                 "that would silently omit most of NSF.")

    # 4. Group into directorates by code prefix, cross-checked by scraped name.
    dir_groups = {}
    anomalies = []
    for code, v in sorted(verified.items()):
        dd = code[:2]
        matched = match_directorate(v["dir_scraped"])
        g = dir_groups.setdefault(dd, {"codes": [], "matches": {}})
        g["codes"].append(code)
        key = matched if matched else ("D" + dd, v["dir_scraped"] or f"NSF directorate {dd}")
        g["matches"].setdefault(key, []).append(code)

    agencies_out = []
    directorates_out = []
    for dd, g in sorted(dir_groups.items()):
        if len(g["matches"]) > 1:
            anomalies.append(f"prefix {dd} maps to multiple directorates: "
                             + "; ".join(f"{k[0]}({','.join(v)})" for k, v in g["matches"].items()))
        (ab, full), _ = max(g["matches"].items(), key=lambda kv: len(kv[1]))
        divisions = []
        for code in g["codes"]:
            v = verified[code]
            leaf = {"slug": v["abbrev"].lower(), "abbrev": v["abbrev"],
                    "name": v["name"], "params": {"org_code_div": code},
                    "active": v["active"]}
            if not v["active"]:
                leaf["note"] = "No awards found after mid-2024; likely renamed or dissolved."
            if code == DMS_CODE:
                leaf["checks"] = DMS_CHECKS
            divisions.append(leaf)
        # Slug collisions within a directorate get the code appended.
        seen = {}
        for leafd in divisions:
            s = leafd["slug"]
            if s in seen:
                leafd["slug"] = f"{s}-{leafd['params']['org_code_div'][:4]}"
                anomalies.append(f"slug collision on '{s}' in {ab}; "
                                 f"renamed to {leafd['slug']}")
            seen[s] = True
        directorates_out.append({"slug": ab.lower(), "abbrev": ab, "name": full,
                                 "divisions": divisions})

    cfg = {
        "seriesStart": "2014-10-01",
        "defaults": {"max_monthly": 1500, "min_total": 0, "max_total": 200000},
        "agencies": [{
            "slug": "nsf", "abbrev": "NSF",
            "name": "U.S. National Science Foundation",
            "adapter": "nsf",
            "directorates": directorates_out,
        }],
    }
    if unresolved:
        cfg["unresolved"] = unresolved
    (REPO_ROOT / "config").mkdir(exist_ok=True)
    (REPO_ROOT / "config" / "orgs.json").write_text(json.dumps(cfg, indent=1))

    # 5. Report.
    report += ["## Verified codes", "",
               "| code | abbrev | division | directorate (scraped) | samples | active |",
               "|------|--------|----------|----------------------|---------|--------|"]
    for code, v in sorted(verified.items()):
        report.append(f"| {code} | {v['abbrev']} | {v['name']} | "
                      f"{v['dir_scraped'] or '?'} | "
                      f"{', '.join(map(str, v['sample_ids']))} | {v['active']} |")
    report += ["", f"## Unresolved codes ({len(unresolved)})", ""]
    for u in unresolved:
        report.append(f"- {u['code']}: {u['reason']} (samples {u['sample_ids']})")
    report += ["", "## Stats", "",
               f"- Codes swept: dd 01..{args.dd_max:02d} x vv 00..{args.vv_max:02d}",
               f"- Codes with zero results: {zero}",
               f"- showAward pages that failed to parse: {parse_failures} "
               f"(raw HTML in reference/discover_debug/ if any)",
               "", "## Anomalies", ""]
    report += [f"- {a}" for a in anomalies] or ["- none"]
    (REPO_ROOT / "reference" / "org_registry_report.md").write_text("\n".join(report) + "\n")
    print(f"Wrote config/orgs.json ({len(verified)} divisions across "
          f"{len(directorates_out)} directorates) and the report; "
          f"{len(unresolved)} unresolved")


if __name__ == "__main__":
    main()
