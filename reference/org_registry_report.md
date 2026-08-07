# NSF Organizational Registry — Report

**Status: BLOCKED. The mandated empirical procedure could not be executed.**
Only the pre-existing, already-verified DMS entry is present in
`config/orgs.json`. Every other directorate/division that NSF actually has
remains unenumerated. This report exists to explain why, precisely, so the
next session can pick this up without re-discovering the same blocker.

## (a) Unknown-code behavior finding

**Not tested — could not be tested.** Step 1 (probing `org_code_div=99999999`
and `org_code_div=03049999`) requires live requests to
`https://api.nsf.gov/services/v1/awards.json`. Every attempt to reach that
host was rejected before a single HTTP response was obtained (see "Network
access finding" below). No adapter guard can be written from this session
based on empirical evidence; do not assume unknown codes return zero records
until this is actually observed.

## Network access finding (this supersedes steps 1, 3, 4, 5)

This session has no general outbound network access. Evidence gathered:

| Method | Target | Result |
|---|---|---|
| `curl` via configured proxy | `https://api.nsf.gov/...` | `CONNECT tunnel failed, response 403` |
| `curl` via configured proxy | `https://www.nsf.gov` | `CONNECT tunnel failed, response 403` |
| `curl` via configured proxy | `https://www.google.com` | `CONNECT tunnel failed, response 403` |
| WebFetch | `https://api.nsf.gov/services/v1/awards.json?...` | `EGRESS_BLOCKED` |
| WebFetch | `https://www.nsf.gov/awardsearch/showAward?AWD_ID=1855773` | `EGRESS_BLOCKED` |
| WebFetch | `https://nsf-gov-resources.nsf.gov/files/NSF-Organizational-Chart.pdf` | `EGRESS_BLOCKED` |
| WebFetch | `https://en.wikipedia.org/wiki/National_Science_Foundation` | `EGRESS_BLOCKED` |
| WebFetch | `https://web.archive.org/web/...` | fetch failed (unreachable) |
| WebSearch | general queries | **works** — returns synthesized snippets + source links, but does not expose raw API JSON responses or full page HTML, so it cannot substitute for `curl`/WebFetch against `api.nsf.gov` or `www.nsf.gov/awardsearch/showAward` |

Checking `curl -sS "$HTTPS_PROXY/__agentproxy/status"` confirmed this is a
policy-level denial (`connect_rejected`, gateway 403), not a TLS/cert
problem, and the proxy README explicitly instructs: *"do not retry
organization policy denials (403/407) — report them instead."* This is
consistent with the evidence above being a broad egress allowlist that does
not include `api.nsf.gov`, `www.nsf.gov`, or (as far as tested) essentially
any general internet host reachable via `curl`/WebFetch in this environment.

**Consequence:** steps 1, 3 (code sweep), 4 (code→name verification via
award pages), and 5 (Sept-2016/Sept-2024 volume probes) in the task
procedure are all impossible from this session — every one of them requires
either `api.nsf.gov/services/v1/awards.json` or
`www.nsf.gov/awardsearch/showAward`, and both are unreachable by every
method available (Bash/curl and WebFetch alike).

## What was NOT fabricated

Given the mission's own governing principle — *"Never trust a single API
query to be complete... verify against independent baselines"* — and the
task's explicit instruction *"Include ONLY codes verified via step 4,"* this
session did not invent directorate/division org codes from background
knowledge to fill out the registry. NSF org codes recalled from training
data (rather than empirically confirmed against live award records) are
exactly the kind of unverified claim this project's data-integrity rules
exist to prevent, and an org-code error silently propagates into every
adapter query and every dashboard built on it. So `config/orgs.json` contains
only:

- **DMS — `03040000`** (Division of Mathematical Sciences, Directorate for
  Mathematical and Physical Sciences). This is not a new verification by
  this session; it is carried forward as the pre-existing ground truth
  already checked into the repo and independently verified against a
  hand-tallied baseline of 11,508 awards / 143 months
  (`reference/pull_nsf_dms.py`, `reference/verified_baseline.json`), per
  `CLAUDE.md`. The `checks` block matches the schema example exactly, as
  required.

No other agency, directorate, or division entries were added.

## (b) Table of verified codes

| Code | Abbrev | Name | Directorate | Sample award IDs | Sept-2016 probe | Sept-2024 probe | Active |
|---|---|---|---|---|---|---|---|
| 03040000 | DMS | Division of Mathematical Sciences | MPS | *(pre-existing baseline, not re-verified this session — see `reference/verified_baseline.json`)* | not probed this session | not probed this session | true |

No other codes were probed, so no other rows exist.

## (c) Codes with awards but unverified/unplaceable

None — because no code sweep (step 3) was run. This is distinct from "zero
found"; it is "not attempted." `config/orgs.json` carries an empty
`"unresolved": []` array as a placeholder, not as a finding.

## (d) Codes probed with zero results

Not applicable — zero codes were probed (0 of the ~420 `dd`/`vv` candidate
combinations in the specified `dd` in 1..20, `vv` in 0..20 sweep space).

## (e) Anomalies / expected-but-missing units

Every NSF unit named in the task as an expected minimum is currently
missing from the registry, purely because it could not be reached, not
because it doesn't exist:

- Directorates expected but absent: BIO, CSE, EDU (formerly EHR), ENG, GEO,
  SBE, TIP, and the Office of the Director pseudo-directorate (`od`) with
  its award-making offices (e.g. OISE, OIA/EPSCoR).
- Within MPS itself, only DMS is present; MPS's other divisions (e.g.
  Astronomical Sciences, Chemistry, Materials Research, Physics) are
  expected to exist and hold awards but have no verified codes here.

None of this is a finding about NSF's structure — it is a complete gap that
the next session must fill once network access to `api.nsf.gov` and
`www.nsf.gov` is available from the execution environment.

## Recommendation for the next session

1. Confirm (e.g. via `curl -sS "$HTTPS_PROXY/__agentproxy/status"`) that
   `api.nsf.gov` and `www.nsf.gov` are reachable before starting — if the
   same `connect_rejected`/`EGRESS_BLOCKED` errors recur, escalate to get
   those hosts added to the egress allowlist rather than re-attempting the
   sweep blind.
2. Once reachable, run the full procedure in `CLAUDE.md`'s task
   description as originally specified (steps 1–5), starting from this
   report and the existing `config/orgs.json` (which is safe to extend —
   nothing in it needs to be redone).
