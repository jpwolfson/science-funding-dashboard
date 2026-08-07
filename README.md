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
