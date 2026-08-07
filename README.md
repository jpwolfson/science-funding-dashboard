# science-funding-dashboard

Self-updating public dashboards of U.S. federal science funding, organized
by agency, directorate, and division (or each agency's equivalent).

Successor to [fed-funding-dashboard](https://github.com/jpwolfson/fed-funding-dashboard)
(NSF Division of Mathematical Sciences only), generalizing its
API-defect-hardened pull pipeline across NSF and, in later phases, NIH and
other agencies via the USAspending API.

Data updates automatically via GitHub Actions: weekly incremental pulls
plus rotating full reconciliations that pick up award amendments without
ever deleting stored history.

See `CLAUDE.md` for architecture, roadmap, and the empirically confirmed
NSF API defects the pipeline defends against.

## Layout

- `config/orgs.json` — org registry (agency → directorate → division), each
  leaf carrying its source-adapter params. Discovered and verified
  empirically by `scripts/discover_orgs.py` (runs on CI).
- `adapters/` — one module per data source (`nsf.py` wraps the NSF Award
  Search API with all known-defect workarounds; `common.py` holds the
  store/aggregation logic shared with rollups).
- `scripts/pull_unit.py` — pull one division; `scripts/rollup.py` — build
  directorate/agency/root dashboards plus the nav index;
  `scripts/verify_dms_baseline.py` — exact-parity gate against the
  hand-verified DMS baseline.
- `data/<agency>/<directorate>/<division>/` — per-division `awards.csv`
  (store of record; never pruned) and `dashboard.json`; rollup
  `dashboard.json` at every level; `data/index.json` for navigation.
- `site/index.html` — the single static page that renders any node
  (`?org=nsf/mps/dms`), deployed via GitHub Pages.
- `.github/workflows/update-data.yml` — weekly incremental matrix (full
  reconciliation the first Monday of each month), rollups, deploy.
