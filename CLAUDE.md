# science-funding-dashboard

Self-updating public dashboards of federal science funding, organized
agency → directorate → division (NSF nomenclature; each agency's own
equivalent tiers). Successor to `jpwolfson/fed-funding-dashboard` (NSF DMS
only), which stays live and untouched until this repo reaches parity for
that division.

## Working regime — read first, follow in every session

The owner is on a usage-limited plan where premium-model (Fable) tokens are
the scarce resource; wall-clock time and GitHub Actions minutes are not.

1. **Model routing.** The main thread does architecture, API diagnosis, and
   data-integrity reasoning only. Delegate mechanical breadth — per-division
   verification sweeps, adapter boilerplate, CI log triage, config
   authoring — to subagents running Sonnet (`model: "sonnet"` on the Agent
   tool / workflow `agent()` calls).
2. **Long pulls run on CI, never in-session.** Kick off the workflow run,
   schedule a check-in (`send_later`, ~30 min), and end the turn. Never
   poll, sleep, or run multi-hour pulls in the session itself.
3. **One phase per session.** Start each phase in a fresh session; long
   conversations re-send accumulated context every turn. Before ending a
   phase, update the Status section below so the next session can start
   cold from this file.
4. **Data integrity rules** (each one bought with a real bug in the DMS
   project):
   - Never trust a single API query to be complete; union results at every
     level of partitioning. An ineffective partition may only waste
     requests, never lose records.
   - Never delete stored awards on a re-pull. Retain and warn.
   - Verify against independent baselines; per-unit counts may only grow.
     A zero-warning run is the release bar.
   - When counts come up short in a systematic pattern, treat the pattern
     as diagnostic (exactly-one-short-per-window ⇒ pagination offset bug).

## NSF Award Search API defects (empirically confirmed 2026-08)

Encode all of these in any adapter touching `api.nsf.gov/services/v1/awards`:

- **`offset` is 0-based** despite documentation suggesting 1-based.
  Paginating from offset=1 silently skips each query's first record.
- **Cross-page duplicate displacement:** queries spanning many pages return
  duplicate records, each silently displacing a record that is never
  returned. Keep result sets ≤ ~60 (`SAFE_WINDOW`) by recursive date
  bisection; partition heavy single days by `transType`, then
  `awardeeStateCode`.
- **Date-filter off-by-one:** unpadded month windows each returned exactly
  one award short. Pad ±1 day and attribute records by their own `date`
  field. The filter may also not operate on the returned `date` field —
  query a wider horizon than the series and attribute by record date.
- **Undocumented params silently ignored:** partition only by documented
  parameters; union everything so an ignored filter cannot lose data.

The working implementation of all of this is `reference/pull_nsf_dms.py`
(verbatim from fed-funding-dashboard), verified exact against a hand-tallied
baseline (`reference/verified_baseline.json`, 11,508 awards, 143/143 months).

## Target architecture

- `config/orgs.json` — registry of org units: agency → directorate →
  division, each leaf carrying its source adapter name + params (e.g.
  NSF `org_code_div`, NIH IC code, USAspending sub-agency/office codes)
  and display names.
- `adapters/` — one module per source: `nsf.py` (generalize
  `reference/pull_nsf_dms.py`), `nih_reporter.py` (Phase 2),
  `usaspending.py` (Phase 3, also the cross-validation source).
- `data/<agency>/<directorate>/<division>/` — per-leaf `awards.csv`
  (year-sharded and/or gzipped once large) + `dashboard.json`; rollup
  `dashboard.json` at directorate, agency, and root levels. Aggregates
  stay small; the site reads only JSON.
- `site/` — static, one page template reading a node's `dashboard.json`,
  nav from a generated `index.json`. Deployed via GitHub Pages
  (owner enables once: Settings → Pages → Source "GitHub Actions").
- CI — weekly incremental matrix (one job per agency or directorate, each
  committing only its own data subtree; the rebase `-X theirs` retry push
  from fed-funding-dashboard is already concurrency-safe). Full
  reconciliation rotates across units rather than running everywhere at
  once; Actions jobs cap at 6 h.
- Validation — every unit cross-checked against USAspending within
  tolerance; invariant failures and divergences auto-file a GitHub issue
  rather than publishing silently.

## Environment constraint (discovered 2026-08-07)

The remote dev environment has NO egress to api.nsf.gov / www.nsf.gov
(proxy policy 403). Every API-touching task — pulls, probes, org
discovery — must run on GitHub Actions, which has full egress. Two
consequences already encoded:

- `scripts/discover_orgs.py` + `.github/workflows/discover-orgs.yml` do the
  empirical org-registry discovery/verification on CI and commit
  `config/orgs.json` + `reference/org_registry_report.md` back.
- `workflow_dispatch` may be unreliable on non-default branches, so both
  workflows also fire on pushes to `claude/**` that touch their trigger
  file (`.github/triggers/update.json` / `discover.json`); the trigger
  file's JSON fields mirror the dispatch inputs. On `main`, use normal
  dispatch/schedule.

## Roadmap / status

- [x] Kickoff: repo created, regime + API lessons documented, DMS pipeline
      and verified baseline seeded under `reference/` (2026-08-07)
- [x] Phase 1 — NSF-wide (completed 2026-08-10):
      - Done: `adapters/common.py` (aggregation regression-verified EXACT
        against fed-funding-dashboard's committed dashboard.json),
        `adapters/nsf.py` (all API-defect workarounds + org-filter probe +
        per-unit plausibility caps from `config/orgs.json` `checks`),
        `scripts/pull_unit.py`, `scripts/rollup.py` (id-deduped rollups,
        child summaries, `data/index.json`), `scripts/verify_dms_baseline.py`
        (exact-parity gate), `scripts/discover_orgs.py`, both workflows,
        `site/index.html` (multi-node port of the old page).
      - **RELEASE BAR MET 2026-08-08 00:02 UTC**: run 31224153926 pull +
        rollup + verify-dms ALL GREEN — fresh full pull = 11,508 awards,
        0 warnings, exact parity with the hand-verified baseline. Owner
        has enabled Pages (Settings done); deploy fires on merge to main.
      - Discovery: run 1 (showAward HTML parser) failed → run 2 (bulk XML,
        commit 93779a9) failed because NSF redesigned Award Search: the
        legacy download endpoint serves a 128-byte meta-refresh stub to
        non-browser clients, and bulk files converted XML→JSON 2025-01.
        v3 proved the ENTIRE legacy /awardsearch/ path — download.jsp
        included, browser UA or not — serves only a 128-byte redirect
        stub; bulk zips remain unreachable. v4 SUCCEEDED via detail-API
        fallback (44 divisions) but review found 3 defects: 16 unresolved
        codes incl. all of TIP (value-pattern extraction missed names
        without a "Division of" prefix), ENG grouped under CSE / AST
        under OD (tie-break bug in name matcher), active=False everywhere
        (recent-window probes inexplicably empty). KEY FACT from v4's
        committed dump: api.nsf.gov/services/v1/awards/{id}.json returns
        EXPLICIT fields divAbbr, dirAbbr, orgCodeDiv, orgCodeDir,
        orgLongName (directorate), orgLongName2 (division). v5 (commit
        fc41f7c, fired 2026-08-09 ~22:10 UTC) extracts by key, checks
        param semantics via orgCodeDiv == swept code, ships all entries
        active:true (derive real flags from pulled data post-backfill).
        Sweep facts established: 59 live org codes, 461 empty, unknown
        codes return EMPTY.
      - REGISTRY DONE (v5, run committed ccb592a, reviewed 2026-08-09):
        59/59 codes verified, 0 unresolved, param semantics exact via
        orgCodeDiv, TIP + ENG + MPS grouping correct, DMS entry intact.
        14 directorate-tier groups = 8 science + OD + 5 admin (BFA, IRM,
        NCO, NNCO, OCIO — kept for completeness). All entries active:true;
        real flags to be derived from pulled data post-backfill.
      - BACKFILL COMPLETE 2026-08-10 01:35 UTC (run 31340113408): all 59
        pulls green, 0 warnings in every unit, rollup green, verify-dms
        exact-parity green post-re-pull. NSF-wide totals: 138,162 unique
        awards since FY2015 (0 cross-division id dups); FY2024 = 11,687
        awards / $8.0B intended (matches NSF's published annual volume);
        FY2026 to date = 5,308 / $4.0B.
      - Active flags derived from pulled data (scripts/derive_active_flags.py,
        24-month window): 40 active, 19 dormant admin/legacy units with
        last-award notes. Re-run after future backfills.
      - Site verified against real data in-browser (9 pages, 0 console
        errors, children tables exactly match rollup JSON). 3 sparse-unit
        display bugs found and fixed (missing tile row on no-current-FY
        units, mechanism-chart label/axis collision, "1 awards" plural);
        fixes re-verified in-browser.
      - Phase 1 exit: PR to main opened + merged by Claude (owner
        pre-approved); Pages deploy fires from update-data runs on main
        (weekly Mondays 09:13 UTC; dispatchable on demand).
      - Known open items: if bulk-XML discovery also fails, diagnose from
        reference/discover_debug/ dumps (now committed even on failure)
        and re-fire via `.github/triggers/discover.json`. Watch the
        report's "not queryable via the API" section — any bulk code the
        API refuses means awards invisible to our pulls. Site review of a
        node with many children (root/agency) once real multi-division
        data exists. Weekly schedule only activates once merged to main.
- [x] Cumulative FY-to-date overlay charts on every node (completed
      2026-08-10 per `docs/handoff-cumulative-fy-charts.md`): `fyCumulative`
      in `aggregate()`, `cumulativeChart` ×2 leading every node page,
      `scripts/reaggregate.py` (offline re-aggregation path — reusable
      whenever `aggregate()` gains keys). All acceptance checks green via
      independent verification sweep: endpoint invariant exact on 256
      year-series across 62 dashboards, DMS byte-parity with
      fed-funding-dashboard@2c211a0 incl. mid-year points, light+dark
      browser pass, awards.csv untouched. Known inherited behavior: FYs
      with zero awards in the 5-year window are absent from fyCumulative
      (fewer lines), not all-zero series.
- [ ] Phase 2 — NIH via RePORTER API (institutes/centers as the
      directorate tier). Forces the year-shard/compression storage format
      at realistic volume.
- [ ] Phase 3 — USAspending adapter for agencies without good native APIs
      (DOE SC, NASA SMD, DOD research offices, USDA NIFA, ...) plus the
      cross-validation layer for all existing units.
