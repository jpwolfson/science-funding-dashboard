# Phase 3.1b handoff

Status: complete. The base release, post-deploy QA patch, and landing-page
obligation-summary correction are merged and deployed through PRs #6–#9. CI,
desktop/mobile visual QA, and the final Pages smoke check passed. The historical
backfill, exact reconciliation, award-link normalization, and calibration-ready
gate are complete. Current live deployment:
https://jpwolfson.github.io/science-funding-dashboard/?org=obligations

## What changed

- Added a physically separate obligation ledger and documented its exact-cent
  event/store contract in `docs/obligation-ledger.md`.
- Added the DOE Office of Science `089-0222` registry with legacy PAC/PAN and
  FY2026 PARK aliases for every observed Program Activity, including an
  unknown bucket.
- Added a fail-closed USAspending custom-account adapter. File B cumulative
  CPE snapshots are differenced by reporting period for canonical dollars.
  File C TOA rows are direct signed period activity and provide award,
  recipient, and flow metadata. Assistance, Contracts, and Unlinked files are
  all ingested.
- Added explicit File B-minus-File C residual events. This preserves the exact
  account/Program Activity series while honestly separating award-linked from
  payroll, intramural, and other non-award activity.
- Added deterministic fiscal-year gzip shards, additive obligation rollups,
  exact-cent offline validation, pinned GTAS/File A baselines, and a parallel
  FY2017-present GitHub Actions backfill.
- Added a separate `data/obligations/index.json` tree and site rendering for
  signed totals, submission-period steps, positive/negative ledger entries,
  File C/net share,
  distinct linked awards, recipients, and positive/negative flows. Existing
  award dashboards still default to `kind=awards`.
- Formalized the NSF DMS USAspending count diagnostic as a ≥99.5% calibration
  invariant; the pinned result is 1,006/1,008 (99.80%) with the two known IAA
  residuals. Dollars remain intentionally non-comparable.
- Corrected the NIH Data Book gate after a separate full re-pull recovered
  13,790 records that the old funding-mechanism whitelist had excluded. The
  product still retains contracts and IAAs; each row now persists mechanism
  and activity, and the independent benchmark derives the Data Book's
  grants/OT, non-zero-dollar scope at the original tight 2% tolerance.

## Evidence and decisions

The revised roadmap assumed File C could reconcile to GTAS with a small gap.
Live FY2024 DOE data disproved that assumption:

| Source | FY2024 obligations |
|---|---:|
| GTAS/File A and File B | $9,281,790,861.20 |
| File C award-linked subset | $8,527,849,368.87 |
| Non-award residual | $753,941,492.33 |
| File C coverage | 91.8772% |

The gap is structural, not a pagination defect: USAspending describes File C
as prime-award spending, which is a subset of account spending. The
implementation therefore uses File B as canonical and File C as enrichment.
This is the only tested design that preserves both exact account reconciliation
and useful award/recipient detail.

The other roadmap exception is historical availability. Files A/B/C begin in
FY2017 Q2, so FY2015–16 are recorded as unavailable, FY2017 as partial-source
history, and FY2018 as the first full fiscal year. No award-search values are
synthesized for the unavailable years.

## Validation completed

- Full Python unit suite: 56 tests green after the post-deploy QA additions.
- Live account resolver: DOE `089-0222` dynamically resolved to internal ID
  5778 and the requested account scope echoed correctly.
- Live File B P02 probe: 146 rows, $1,123,055,113.69 cumulative obligations.
- Live File C FY2024 archive: 52,749 source rows, 4,036 canonical events,
  $8,527,849,368.87, including negative and unlinked rows.
- [Backfill run 31498087792](https://github.com/jpwolfson/science-funding-dashboard/actions/runs/31498087792)
  completed FY2017–26, rebuilt 34,387 canonical events, reconciled every
  completed GTAS year at exact cents, validated partial-year pins, and passed
  the full unit/site contract suite.
- Light/dark browser smoke passed for the obligation root, DOE, Office of
  Science account, Basic Energy Sciences Program Activity, and legacy award
  root with zero console errors. Signed negative activity and residuals remained
  visible and the legacy award dashboard was unchanged.
- The browser gate found USAspending-internal `localhost:3000/award/...`
  permalinks in File C. The adapter/store boundary and site now normalize them
  to public `https://www.usaspending.gov/award/.../` URLs. The browser check
  confirms no internal links remain and offline validation rejects regressions.

## Post-deploy QA findings and fixes

- FY2017 was correctly pinned as partial-source history but the dashboard
  renderer marked only the latest FY as partial. Rollups now consume the
  account baseline statuses, so FY2017 and FY2026 are both visibly partial.
- Program Activity dashboards previously omitted account-covered periods with
  no event. Their period charts therefore compressed time and zero-current-year
  pages appeared stale. Child rollups now materialize the account's complete
  reporting-period spine with exact zero buckets.
- Validation now rejects missing required fiscal years, corrupt/stale manifests,
  missing File B residual buckets, stale dashboards, incomplete child timelines,
  invalid signed gross decomposition, and unmapped nonblank Program Activities.
- Site copy now scopes every summary tile to the current FY, translates the
  latest submission period to a calendar month, distinguishes the signed
  File C/net ratio from a bounded completeness score, and states that recipient
  tables use only linked File C rows. The current-year top rows remain visible;
  the remaining three-year recipient/flow detail is disclosure-controlled.
- Chart accessible names, visible keyboard focus, and compliant light-theme
  secondary-text contrast were added. The award-ledger path remains backward
  compatible.

The Phase 3.1b release has no remaining steps. PR #8 released the QA hardening;
PR #9 corrected the landing-page asymmetry by adding parallel DOE obligation
summary tiles for net, gross positive, gross negative, and File C-linked award
coverage. That handoff's required workflow platformization is now complete in
Phase 3.2a: refresh planning is registry-driven and scheduled, publication is
atomic, and request/archive/replacement provenance survives reconciliation.
See `docs/phase-3.2a-handoff.md` and the revised roadmap in `CLAUDE.md`.

The separate NIH full re-pull is complete: all 28 IC shards carry structured
activity/mechanism detail, exact live RePORTER reconciliation passes, the
like-for-like Data Book subset remains within 2%, and NIH/root rollups contain
708,233 unique awards.

Do not replace canonical File B dollars with File C-only totals, do not route
events through `adapters/common.py` or `scripts/rollup.py`, and do not fabricate
monthly or FY2015–16 data.

## CI run history and resolved blockers

- Obligation backfill run `31462254962` proved the original quarterly File C
  labels (`FY2017Q2`) needed canonical period-end normalization (`P06`). That
  semantic fix is covered by a regression test.
- Retry run `31462411725` then completed FY2017 exactly. FY2018 successfully
  generated File B periods P02–P09, but USAspending disconnected on all ten
  attempts to request P10; `fail-fast` cancelled the remaining years. The
  adapter now uses a 20-second post-archive cooldown, 20 POST attempts with
  visible backoff, and a non-fail-fast year matrix. Trigger attempt 4 is the
  next run.
- The NIH full re-pull is intentionally separate from the obligation ledger.
  It must rewrite all 28 IC shards with structured activity/mechanism detail,
  pass exact live RePORTER reconciliation, pass the like-for-like Data Book
  subset at 2%, and rebuild NIH/root rollups before publication.
- NIH completed those gates at 708,233 unique awards. PR conflicts against
  `main` were limited to 22 NLM/OD gzip shards from the earlier repull; merge
  commit `5edae8c` retains the newer structured-mechanism shards, records
  `main` as the second parent, and passed the complete local CI command set.
- Obligation attempt 4 completed 9/10 account-years. FY2020 downloaded every
  File B period and all 27,301 File C rows, then correctly surfaced one File C
  unknown-PA bucket (`FY2020P03`, `0000`) with no File B bucket. The adapter
  now retains that File C overlay and offsets it with an equal negative
  residual in visible `0000`, so canonical File B net remains zero. Known-PA
  orphan buckets still fail.
- Obligation attempt 5, run `31498087792`, completed all ten fiscal-year jobs,
  exact reconciliation, dashboard generation, and its data commit. The
  subsequent release inspection normalized internal USAspending award links,
  repeated all offline checks, and completed the light/dark browser gate.
