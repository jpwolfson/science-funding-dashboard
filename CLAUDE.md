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

## Roadmap / status

- [x] Kickoff: repo created, regime + API lessons documented, DMS pipeline
      and verified baseline seeded under `reference/` (2026-08-07)
- [ ] Phase 1 — NSF-wide: org registry for all directorates/divisions,
      generalized NSF adapter, matrix CI, rollups, site with nav.
      DMS numbers must reproduce the reference baseline exactly.
- [ ] Phase 2 — NIH via RePORTER API (institutes/centers as the
      directorate tier). Forces the year-shard/compression storage format
      at realistic volume.
- [ ] Phase 3 — USAspending adapter for agencies without good native APIs
      (DOE SC, NASA SMD, DOD research offices, USDA NIFA, ...) plus the
      cross-validation layer for all existing units.
