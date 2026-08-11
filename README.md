# science-funding-dashboard

Self-updating public dashboards of U.S. federal science funding, organized
by agency, directorate, and division (or each agency's equivalent).

Successor to [fed-funding-dashboard](https://github.com/jpwolfson/fed-funding-dashboard)
(NSF Division of Mathematical Sciences only), generalizing its
API-defect-hardened pull pipeline across NSF and NIH. Later phases add other
agencies through the USAspending API.

Data updates automatically via GitHub Actions: weekly incremental pulls
plus rotating full reconciliations that pick up award amendments without
ever deleting stored history.

See `CLAUDE.md` for architecture, roadmap, and the empirically confirmed
NSF API defects the pipeline defends against.

Phase 3.2b records a dated, reviewed AAAS FY 2026 R&D Appropriations
crosswalk as reference-only research. Federal accounts remain canonical, AAAS
labels are retained as alternate framing, and the completed Phase 3.2a
technical prerequisite does not authorize automatic account onboarding or
production remapping. See
[`docs/aaas-federal-account-crosswalk.md`](docs/aaas-federal-account-crosswalk.md).

Phase 3.2c-1 implements a non-blocking funding-action sentinel that surfaces
material gross-negative File C activity without calling it a cancellation.
Its versioned financial-observation, sourced-event, optional-review, and episode
stores publish durable unreviewed/confirmed/reviewed/superseded/restored states.
The structured NSF and DOE source pilots remain scoped to Phase 3.2c-2. See
[`docs/funding-action-sentinel.md`](docs/funding-action-sentinel.md) for the
labeling, review, limitation, and maintenance-cost contract.

## Layout

- `config/orgs.json` — org registry (agency → directorate → division), each
  leaf carrying its source-adapter params. Discovered and verified
  empirically by `scripts/discover_orgs.py` (runs on CI).
- `adapters/` — one module per data source (`nsf.py` wraps the NSF Award
  Search API with all known-defect workarounds; `nih_reporter.py` pages the
  NIH RePORTER v2 API by administering institute/center and fiscal year;
  `common.py` holds store/aggregation logic shared with rollups).
- `scripts/pull_unit.py` — pull one division; `scripts/rollup.py` — build
  directorate/agency/root dashboards plus the nav index;
  `scripts/verify_dms_baseline.py` — exact-parity gate against the
  hand-verified DMS baseline; `scripts/validate_nih.py` — shard, dedup,
  rollup, plausibility, live-count, and NIH Data Book reconciliation gate.
- `data/<agency>/<directorate>/<division>/` — per-leaf store of record plus
  `dashboard.json`. NSF retains a single `awards.csv`; NIH uses deterministic
  `awards/FY####.csv.gz` shards and a manifest. Stores are never pruned.
  Rollup `dashboard.json` files exist at every level, with `data/index.json`
  for navigation.
- `config/obligation_accounts.json`, `adapters/usaspending_obligations.py`, and
  `data/obligations/` — a physically separate appropriation-obligation ledger.
  Canonical dollars come from File B reporting-period deltas; File C provides
  award-linked recipient/flow detail and the residual remains visible.
- `config/funding_sentinel.json`, `adapters/funding_sentinel.py`, and
  `data/sentinel/` — the separate funding-action signal/status layer. The
  detector reads gross-negative File C components, excludes File B residuals,
  and joins every signal back to stable obligation event IDs.
- `site/index.html` — the single static page that renders any node
  (`?org=nsf/mps/dms`, `?org=obligations`, or `?org=sentinel`), deployed via
  GitHub Pages.
- `.github/workflows/update-data.yml` — weekly incremental matrices (full
  reconciliation the first Monday of each month), rollups, deploy. NSF runs
  four leaves in parallel; NIH runs serially and the adapter enforces NIH's
  recommended one-request-per-second ceiling.
- `.github/workflows/update-obligations.yml` — registry-driven weekly current-FY
  refresh plus rotating historical reconciliation, exact GTAS checks, Program
  Activity fan-out, and atomic obligation publication. It never passes
  obligation events through award-ID deduplication.
- `.github/workflows/update-sentinel.yml` — independent weekly downstream build,
  validation, rendered-browser check, and commit. It has no dependency edge
  from award or obligation refreshes and no review queue.
- `scripts/plan_obligation_refresh.py` and
  `scripts/reconcile_obligation_artifacts.py` — account × FY planning and
  provenance-preserving atomic snapshot assembly.
- `reference/aaas_rd_appropriations_2026-08-11.json` and
  `reference/aaas_federal_account_crosswalk.{json,csv}` — dated AAAS source
  inventory and reviewed reference-only federal-account mappings; neither is a
  production registry or ingestion input.
- `docs/aaas-federal-account-crosswalk.md` — Phase 3.2b source provenance,
  classification rules, many-to-many review results, evidence model, and the
  reviewed account-onboarding boundary.
- `docs/funding-action-sentinel.md` and `docs/phase-3.2c1-handoff.md` — the
  sentinel contract, implemented core, boundaries of automation, source-pilot
  handoff, and estimated operating burden.

## NIH data semantics

The NIH branch of the dashboard uses the 28 current administrative components
listed by RePORTER as the institute/center tier. Each RePORTER application ID
is one award record for one fiscal year. Subprojects and intramural (`IM`)
records are excluded: subprojects would double-count parent awards, while
intramural records generally carry neither award amounts nor award notice
dates. Grants, cooperative agreements, contracts, and interagency agreements
remain included.

Each institute/year is fetched twice, sorted by application ID in opposite
directions. Both unique ID sets must exactly match each other and RePORTER's
`meta.total`; otherwise the pull retries and ultimately refuses to publish.
Award IDs are namespaced (`nih:<application_id>`) in the common store so NIH
and NSF identifiers cannot collide in federal rollups.

The complete product includes R&D contracts and interagency agreements. Its
independent NIH Data Book gate compares a derived grants/Other-Transactions
subset at the same 2% count and dollar tolerance, matching the benchmark's
published exclusions instead of weakening the tolerance to absorb a scope
difference. Funding mechanism and activity code are persisted on every NIH
row so that subset remains reproducible offline.

See [`docs/nih-data-validation.md`](docs/nih-data-validation.md) for the
fail-closed extraction contract, post-backfill checks, independent published
benchmarks, tolerances, and reproducible validation commands.
