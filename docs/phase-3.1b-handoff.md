# Phase 3.1b handoff

Status at PR creation: implementation and local validation complete; remote
historical backfill/release gate pending.

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
  signed totals, submission-period steps, de-obligations, File C coverage,
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

## Validation completed locally

- Full Python unit suite: 42 tests green.
- Live account resolver: DOE `089-0222` dynamically resolved to internal ID
  5778 and the requested account scope echoed correctly.
- Live File B P02 probe: 146 rows, $1,123,055,113.69 cumulative obligations.
- Live File C FY2024 archive: 52,749 source rows, 4,036 canonical events,
  $8,527,849,368.87, including negative and unlinked rows.
- JavaScript syntax and whitespace checks passed. Local Playwright could not
  launch Chrome inside the desktop sandbox, so browser layout remains part of
  the remote release bar.

## Remaining gate and takeover steps

1. Let `Backfill obligation ledger` complete on the PR branch. It fans out one
   fiscal year per job, rebuilds the unified store, and must reconcile every
   pinned year exactly.
2. Review any live schema drift or USAspending transient-download failure. The
   adapter retries 429/5xx/disconnects and refuses unknown status states,
   archive hosts, row-count mismatches, scope mismatches, unmapped Program
   Activities, or cent differences.
3. Run the browser smoke against obligation root, DOE, account, and at least
   one positive/negative Program Activity in light and dark mode; require zero
   console errors and verify the legacy award root is unchanged.
4. Only after those checks pass, change
   `reference/usaspending_calibration.json` to `status=ready`,
   `onboardingAllowed=true`, and `obligationLedger.status=passed`. The
   validator rejects an early flip.
5. Merge, confirm the Pages deployment, and record run/PR/deploy links in this
   handoff and the Phase 3.1b roadmap entry.

The NIH grants-scope adapter/validator change requires one more full 28-IC
re-pull so every deterministic shard carries the new structured mechanism
detail. Until that run validates and rebuilds rollups, NIH leaf data may show
the corrected 708,233-record universe while NIH/root rollups still show the
old 694,443 total. This mixed state is intentionally blocked from publication.

Do not replace canonical File B dollars with File C-only totals, do not route
events through `adapters/common.py` or `scripts/rollup.py`, and do not fabricate
monthly or FY2015–16 data.

## CI run history and current blockers

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
  orphan buckets still fail. Attempt 5 is the next full reconciliation run.
