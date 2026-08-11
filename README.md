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

Phase 3.2c plans a non-blocking funding-action sentinel to surface material
downward activity and source-confirmed terminations or restorations for optional
review. It will not make data refreshes or publication depend on a reviewer.
See [`docs/funding-action-sentinel.md`](docs/funding-action-sentinel.md) for the
proposed source, labeling, review, limitation, and maintenance-cost contract.

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
- `site/index.html` — the single static page that renders any node
  (`?org=nsf/mps/dms`), deployed via GitHub Pages.
- `.github/workflows/update-data.yml` — weekly incremental matrices (full
  reconciliation the first Monday of each month), rollups, deploy. NSF runs
  four leaves in parallel; NIH runs serially and the adapter enforces NIH's
  recommended one-request-per-second ceiling.
- `.github/workflows/update-obligations.yml` — registry-driven weekly current-FY
  refresh plus rotating historical reconciliation, exact GTAS checks, Program
  Activity fan-out, and atomic obligation publication. It never passes
  obligation events through award-ID deduplication.
- `scripts/plan_obligation_refresh.py` and
  `scripts/reconcile_obligation_artifacts.py` — account × FY planning and
  provenance-preserving atomic snapshot assembly.
- `docs/funding-action-sentinel.md` — Phase 3.2c specification for a planned
  non-blocking signal/status layer, optional review process, boundaries of
  automation, and estimated operating burden. The sentinel is not implemented
  yet.

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
