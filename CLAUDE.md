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
- [~] Phase 1 — NSF-wide (code landed 2026-08-07 on `claude/phase-1-50i2eh`;
      awaiting CI results):
      - Done: `adapters/common.py` (aggregation regression-verified EXACT
        against fed-funding-dashboard's committed dashboard.json),
        `adapters/nsf.py` (all API-defect workarounds + org-filter probe +
        per-unit plausibility caps from `config/orgs.json` `checks`),
        `scripts/pull_unit.py`, `scripts/rollup.py` (id-deduped rollups,
        child summaries, `data/index.json`), `scripts/verify_dms_baseline.py`
        (exact-parity gate), `scripts/discover_orgs.py`, both workflows,
        `site/index.html` (multi-node port of the old page).
      - In flight (kicked off 2026-08-07 ~22:32 UTC, on the phase branch):
        run 31224153926 "Update data" = DMS full pull + exact baseline
        verify (still pulling at 23:20 UTC — full history takes ~1h+).
        Discovery run 31224153930 FAILED as anticipated: the API sweep
        worked (59 live codes, 461 empty; unknown org codes return EMPTY,
        so the adapter's bogus-code abort guard is fully armed), but the
        blind-written showAward HTML parser parsed nothing and the
        ground-truth gate refused to write. Reworked (commit 93779a9):
        discovery now verifies identity via NSF bulk award XML downloads
        (award records carry org Code + Division/Directorate names),
        adds param-semantics + two-way completeness checks, always writes
        the report, and the workflow commits diagnostics on failure.
        Re-fired via trigger bump — check the newest "Discover NSF org
        registry" run.
      - Next session / check-in: (1) confirm DMS verify-dms job PASSED —
        that is the Phase 1 release bar; (2) review the discovered
        config/orgs.json against reference/org_registry_report.md (check
        unresolved list, directorate grouping anomalies, parse-failure
        debug dumps; sanity-check division count ~30-45 incl. defunct);
        (3) fire the all-units backfill by committing
        `.github/triggers/update.json` = {"units":"all","full_refresh":true}
        (~35 division jobs, max-parallel 4, hours of wall-clock — check in
        via send_later, never in-session); (4) after rollups land, eyeball
        site with real data, then open the Phase 1 PR to main; owner
        enables Pages (Settings → Pages → Source "GitHub Actions"); deploy
        job only runs on main.
      - Known open items: if bulk-XML discovery also fails, diagnose from
        reference/discover_debug/ dumps (now committed even on failure)
        and re-fire via `.github/triggers/discover.json`. Watch the
        report's "not queryable via the API" section — any bulk code the
        API refuses means awards invisible to our pulls. Site review of a
        node with many children (root/agency) once real multi-division
        data exists. Weekly schedule only activates once merged to main.
- [ ] Phase 2 — NIH via RePORTER API (institutes/centers as the
      directorate tier). Forces the year-shard/compression storage format
      at realistic volume.
- [ ] Phase 3 — USAspending adapter for agencies without good native APIs
      (DOE SC, NASA SMD, DOD research offices, USDA NIFA, ...) plus the
      cross-validation layer for all existing units.
