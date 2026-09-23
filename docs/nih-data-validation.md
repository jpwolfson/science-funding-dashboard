# NIH data validation

The NIH pipeline uses layered, fail-closed checks. A green pull means the
committed data are internally complete relative to RePORTER's declared result
universe and remain within independently published NIH aggregate benchmarks.

## Extraction contract

Every administering institute/center and fiscal year is paged twice by
application ID, once ascending and once descending. Publication requires:

1. `meta.total` remains constant on every page;
2. each pass returns exactly `meta.total` unique application IDs;
3. the ascending and descending ID sets are identical;
4. every row matches the requested fiscal year and administering component;
5. every row is a parent record with a non-intramural funding mechanism; and
6. the fiscal-year result set remains below RePORTER's 15,000-row pagination
   ceiling.

The whole fiscal-year snapshot is retried after a transient inconsistency and
the unit is not written after a persistent failure. The unique-count check
specifically detects the cross-page duplicate displacement observed in the NSF
API: a repeated row can no longer silently replace a missing row.

## Store and aggregation contract (source-current semantics)

RePORTER re-dates, retracts, and un-retracts records between weekly pulls.
This is normal source behavior, not a pipeline defect, so the pipeline
publishes it legibly instead of hiding it behind a per-month "allowed
shrink" exception (the pre-2026-09-17 design; see
`docs/phase-3.2d-remediation-brief.md` and the HIGH-1 finding in
`docs/reviews/2026-09-15-phase-3.2d-independent-review.md` for why it broke).

A stored award id is **never deleted** from the physical store
(`adapters.common.write_store`): every pull only ever adds to, or
overwrites fields on, an existing row. Two committed ledgers make source
churn auditable:

- **Exclusions ledger** (`reference/nih_reporter_exclusions.json`, schema
  `{schemaVersion, records: [{id, unit, classification, reason, decidedOn,
  status}]}`, `status` in `{excluded, returned}`) is a reviewed, human-
  curated **soft delete**. `status: "excluded"` means the adapter pull,
  `scripts/rollup.py`, and `scripts/reaggregate.py` all skip that id from
  every aggregate (`totalAwards`, monthly, fiscal-year, and cumulative
  series) -- but the physical store keeps the row. If a live pull ever
  re-emits an id currently marked `excluded`, the pull flips its status to
  `returned`, re-includes it in every aggregate, and prints a `NOTICE` --
  this is expected source behavior and never fails the pull.
- **Move ledger** (`data/nih/<ic>/<ic>/changes.csv.gz`, columns
  `pullDate,id,field,old,new`, append-only, sorted by `(pullDate, id,
  field)`, gzip with a fixed mtime for reproducible bytes) records every
  overwrite a pull makes to an already-stored id's `date`, `amount`,
  `title`, or `type`. It cannot be produced offline (only a live pull
  appends to it); its absence is not an error.

`scripts/validate_nih.py` checks all committed NIH stores without contacting an
API by default:

- gzip shards are readable, their rows belong to the named fiscal year, and
  the manifest record count and year list are exact;
- IDs are unique within and across institutes and use the `nih:` namespace;
- leaf dashboard totals equal the store's rows **minus** currently-excluded
  ids; the NIH agency rollup and the award root equal the same
  exclusion-aware union;
- the NIH agency rollup is marked `dataComplete`;
- every NIH leaf, IC rollup, the NIH agency rollup, and the award root
  carry the exact `methodologyNote` string (see "NIH award-ledger
  invariants" in `docs/verification-regime.md`);
- the exclusions ledger's own schema is valid, every `excluded` id is
  absent from every aggregated total, and every `returned` id present in
  the store is counted;
- the move ledger, where present, is readable, has exactly the
  `pullDate,id,field,old,new` columns, and is sorted;
- each institute remains within its configured FY2015-present volume range
  (measured on the aggregated, exclusion-filtered rows);
- monthly counts remain under the plausibility cap (same aggregated rows); and
- published dashboard warnings fail validation unless explicitly allowed.

Each normalized row also persists the RePORTER funding mechanism, activity
code, and award type in the existing `transType` detail. This makes external
benchmark scope reproducible from the committed store. Legacy rows without
that structured detail fail validation and require a full re-pull; the
validator never guesses a mechanism from the dashboard's broader award bin.

The pull itself is non-destructive: it never pops an id, even a reviewed
exclusion, from the store. A full pull's own id-level bookkeeping is
published, never silently absorbed:

- an id stored but not returned by a full pull, and not already in the
  exclusions ledger, is retained and reported in a plain-language
  `dataQualityNotes` entry on the leaf dashboard -- never a warning, never
  a failure ("N stored award records were not returned by the pull and are
  retained; NIH revises and withdraws notices");
- a re-dated record whose new, source-current date falls outside the
  record's own declared `fiscal_year` is retained, counted under that new
  date, and reported the same way, rather than silently clamped to the
  fiscal year's start (the pre-2026-09-17 behavior);
- moves (tracked-field overwrites) plus ledger returns, summed over one
  pull for one institute, are checked against two separate churn guards
  (W15, 2026-09-22; see below), each of which fails the pull closed above
  its own threshold.
- **Displacement guard.** `date` moves plus exclusion-ledger returns are
  checked against `max(20, 0.1% of store)`. Above it the pull fails
  closed, because that volume of churn is the pagination/duplicate-
  displacement bug signature (CLAUDE.md data integrity rule 4): a
  repeated row silently displacing a missing one can only ever surface as
  an id vanishing (a return) or a stable id's date jumping -- never as an
  amount, title, or type change on a record that is otherwise present and
  stably dated.
- **Value-churn guard.** `amount`, `title`, and `type` moves (excluding
  `date`) are checked separately against `max(100, 1% of store)`. Above
  it the pull fails closed with a distinct "field-parse regression"
  diagnosis, because that volume of non-date churn is more likely a
  source schema change or an adapter parse regression than ordinary
  revision. The guard is deliberately wider than the displacement guard:
  NIH revises award amounts on stable, correctly-dated ids as routine
  source behavior, and the 2026-09-21 NCI pull is the motivating case --
  148 amount-only moves in one pull, zero date moves, zero returns, which
  tripped the single combined threshold that existed before this split
  even though it carried none of the displacement signature. The other 27
  institutes that same day each had 1-17 amount moves (103 total),
  consistent with ordinary source revision at a much smaller scale.
  Below this guard, the pull still publishes; any non-date move is
  disclosed in a `NOTICE` and a plain-language `dataQualityNotes` entry
  ("N award record(s) had their amount, title, or type revised by NIH
  since the previous pull; figures reflect the source as of the pull
  date."), never silently absorbed.
- **Initializing-pull exemption.** Neither guard above is enforced on a
  unit's very first source-current pull, i.e. one for which
  `data/nih/<ic>/<ic>/changes.csv.gz` does not yet exist. Every store
  built under the pre-2026-09-17 adapter accumulated weeks of unrecorded
  field revisions, because that adapter never overwrote fields; measuring
  that backlog against thresholds sized for one week's steady-state churn
  would misfire on every unit's first pull under this contract, not just
  the ones with an actual pagination defect or parse regression. On that
  first pull, every move is appended to the ledger unconditionally --
  which is what initializes it -- and a `NOTICE` reports the move count
  and its per-field breakdown. The exemption is self-limiting, not a
  bypass flag: the committed ledger file this pull creates is itself the
  marker the adapter checks, so a given unit can take this path at most
  once, ever. From that unit's next pull onward, with the ledger already
  present, both guards apply exactly as described above. A pull that
  trips either guard (initializing or not) prints the per-field move
  counts and up to ten sample moves (`id field: old -> new`) so the drift
  is diagnosable from the CI log without a live reproduction.

Deterministic shard rewrites (`adapters.common.write_store`) also prevent a
corrected date from leaving one ID in two fiscal-year files -- verified by
`tests/test_common_store.py`.

`adapters.common.write_dashboard`'s id-count invariant is source-agnostic
and shared with NSF: a caller may pass the true physical `store_id_count`
separately from the aggregated `awards` it publishes. That physical count
is itself published on every dashboard as `storeIdCount`, and the next
run's check compares against the *previous* `storeIdCount` (falling back
to the previous `totalAwards` only on the first run after this field was
introduced) -- never against the previous aggregated `totalAwards` -- so a
legitimate aggregation-level exclusion (NIH's soft delete) never trips the
warning, while a store that lost exactly as many rows as it has excluded
ids still does.

## Orthogonal and external reconciliation

With `--live`, the validator issues one multi-year `meta.total` query per
institute. Equality is **not** required: `meta.total` is compared against
`store - excluded - retainedMissing` (the store's exclusion- and
missing-uncovered-aware expected count) within a bounded, printed gap --
see "NIH award-ledger invariants" in `docs/verification-regime.md` for the
exact tolerance. Every institute's decomposition (`store`, `excluded`,
`retainedMissing`, `expected`, `sourceTotal`, `gap`, `tolerance`) is printed
so a divergence is diagnosable, not just pass/fail. This uses a different
query shape from the per-year pagination and detects partition, registry,
union, and store-loss errors. It is same-source reconciliation, not an
independent source.

Independent reasonableness gates use NIH Data Book reports 400 and 401. Those
reports are produced through NIH's monthly extramural-awards publication path,
while RePORTER refreshes weekly. FY2022-FY2025 award counts must remain within
2% and award dollars within 2% of the pinned values in
`reference/nih_databook_baseline.json`.

This comparison is deliberately like-for-like rather than a check of the
dashboard's complete product total. The benchmark subset contains parent
grants and Other Transactions with non-zero award dollars and excludes R&D
contracts, interagency agreements, intramural projects, and loan-repayment
activity codes. The dashboard and its RePORTER exact-count gate continue to
include contracts and interagency agreements. The machine-readable validation
report publishes both `fiscalYears` (complete product scope) and
`dataBookScopeFiscalYears` (benchmark scope), so the exclusion is auditable.

Sources:

- <https://report.nih.gov/nihdatabook/report/400>
- <https://report.nih.gov/nihdatabook/report/401>
- <https://report.nih.gov/faqs>
- <https://report.nih.gov/exporter-data-dictionary>
- <https://grants.nih.gov/funding/activity-codes>

## Award refresh, freshness, and publication (W17)

Phase 3.2d remediation W17 is the award-ledger analogue of the obligation
ledger's per-account atomicity contract (`docs/obligation-ledger.md`,
"Refresh, freshness, and publication", W12). Before W17, one refused unit
in `update-data.yml`'s `pull-nsf`/`pull-nih` matrix (a pull refused by the
source, a timeout, a lost push, or the runner itself failing) made
`validate_nih.py --live` error on that unit's now-stale live gap, which
failed the `rollup` job before it committed and skipped `deploy` -- leaving
`main` with some units freshly refreshed under a stale rollup and no
disclosure of which unit had not actually refreshed (2026-09-21, run
35621987484). W17 makes a failed unit's pull a *published, disclosed
stale state* instead of a run-wide failure:

- **Success markers.** After a `pull-nsf`/`pull-nih` matrix job's
  commit/push step succeeds (a "No data changes" run still counts -- it
  succeeded, it just had nothing new to commit), it writes
  `_pull_ok/<slug>.json` (`{"unit": "<unit path>", "completedAt": "<UTC
  ISO timestamp>"}`, `slug` = the unit path with `/` replaced by `__`) and
  uploads it as a short-retention `pull-ok-<slug>` artifact. A job that
  fails at any earlier step uploads nothing.
- **`data/refresh_status.json`** (schema 1; the award-tree analogue of
  `data/obligations/refresh_status.json`) is built by
  `scripts/award_refresh_status.py` in the `rollup` job, from this run's
  planned units (`nsf_matrix` + `nih_matrix`) and its downloaded
  `pull-ok-*` markers, BEFORE `scripts/rollup.py` runs. A unit this run
  did not plan keeps its prior entry unchanged; a planned unit with a
  marker is `fresh`; a planned unit with no marker is `stale`, carrying a
  `staleSince` date (preserved unchanged across repeated failures) and a
  `reason`. The one hard failure is every planned unit coming up with no
  marker at all -- that run refuses to publish rather than mark every unit
  silently stale. Shared logic lives in `adapters/award_refresh.py`.
- **Stale unit reason text (owner-approved, verbatim; the W12 sentence
  with "account" -> "unit", nothing else changed):** "Not refreshed since
  `<staleSince>`: the most recent scheduled pull for this unit did not
  complete; figures are the last accepted snapshot." This is both the
  unit's own `refresh_status.json` `reason` and the header note rendered
  on that unit's page.
- **Rollup stamping** (`scripts/rollup.py`, and `scripts/reaggregate.py`
  via its call into `rollup.main()` at the end, so an offline rebuild
  never erases the disclosure): a stale leaf's own `dashboard.json` gets a
  top-level `refreshStatus` (its entry plus `"unit": "<path>"`); a fresh
  leaf carries no such field. A rollup node (directorate/agency/root) that
  aggregates exactly one leaf (an NIH passthrough directorate, e.g.
  `nih/fic` over `nih/fic/fic`) republishes that leaf's own entry,
  `unit` included, so the unit's one visible page gets the header note. A
  node aggregating several leaves with `k` of `n` stale instead gets a
  non-uniform aggregate: "`k` of `n` unit(s) in this directorate/agency
  were not refreshed in the most recent scheduled pull; see the
  directorate/agency page for which unit." (root drops "in this
  dashboard" and always points to "the agency page"). A `child_summary`
  row copies its child's own `refreshStatus` verbatim, so every landing
  table shows which of its children are affected. Totals, `dataComplete`,
  warnings, and every other invariant are unaffected -- a stale leaf still
  has its last accepted store.
- **`validate_nih.py --live`** downgrades an out-of-tolerance live gap
  from an error to a `WARNING: <unit>: stale since <date> (pull did not
  complete); live gap <gap> vs tolerance <tol> not enforced` line for a
  properly disclosed stale unit (one whose `refresh_status.json` entry has
  both a `staleSince` and a `reason`; a bare `status: "stale"` does not
  count). A stale unit within tolerance still gets its normal
  decomposition note plus a distinct stale notice. Every non-live check,
  and every non-stale unit's live check, stays exactly as strict as
  before.
- **`validate_award_invariants.py`** (fast tier, every PR and every push
  to `main`) fails closed on `data/refresh_status.json` itself: schema 1,
  every stale entry has a well-formed `staleSince` and a non-empty
  `reason`, every unit key is a configured leaf, every dashboard's own
  `refreshStatus` field matches what the status file and the org registry
  say it should be (present iff at least one aggregated leaf is stale),
  and every child-row `refreshStatus` matches that child's own dashboard.
- **Workflow order** (`update-data.yml`): `pull-nsf`/`pull-nih` each
  upload their unit's marker right after their commit step; `rollup`
  downloads every `pull-ok-*` artifact (zero is tolerated --
  `award_refresh_status.py` decides whether that is publishable), builds
  `data/refresh_status.json`, builds the rollups, runs
  `validate_nih.py --live`, and commits -- exactly the existing order plus
  the two new steps in front of the rollup build. `deploy` still requires
  `rollup` to succeed and still only runs on `main`. A non-`main` branch
  run additionally does a dry-run `assemble_pages_site.py` +
  `check_pages_footprint.py` at the end of the `rollup` job, so a branch
  proves the deploy job's own build steps still succeed on a
  post-failure, partly-stale tree without actually deploying.
- **Site** (`site/index.html`, award pages only): `renderUnitStaleNote`
  renders the header note when `data.refreshStatus.status === "stale"`
  and `data.refreshStatus.unit` is present (true for a stale leaf's own
  page and for a single-leaf rollup node's own page; a multi-leaf
  rollup's aggregate carries no `unit`, so it never renders there).
  `childrenCard` gives a stale row a " †" suffix and a `staleFootnotes`
  paragraph below the table, grouped by identical `reason` text -- the
  same pattern `obligationChildrenCard` uses for accounts (W12). Neither
  is gated by agency or unit name.

## Commands

```bash
# No network: shard, manifest, dedup, dashboard, rollup, range, and Data Book checks
python scripts/validate_nih.py

# Release/refresh gate: adds exact multi-year RePORTER count reconciliation
python scripts/validate_nih.py --live
```

The live gate is run after rollup construction for any workflow that refreshes
NIH data. A validation failure makes the rollup job fail and prevents a Pages
deployment.
