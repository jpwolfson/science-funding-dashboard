# USAspending Phase 3.1 calibration decision

Status: **BLOCKED before agency onboarding** (2026-08-10).

Phase 3.1 deliberately required calibration against known NSF and NIH data
before USAspending became any agency's sole source. That gate worked: the
award-search representation cannot support the dashboard's stated ex-post,
appropriations-account framing for DOE Office of Science.

The machine-readable evidence is in
`reference/usaspending_calibration.json`; CI enforces the stop state with
`scripts/validate_usaspending_calibration.py`.

## Selected and tested award semantics

The core adapter uses the official award-search endpoint and makes every
choice explicit:

- identity: one prime base award, keyed by `generated_internal_id`;
- date: `Base Obligation Date`, with `date_type=new_awards_only` on every
  fiscal-year filter;
- amount: `Award Amount`, USAspending's current total obligation for the
  entire prime award;
- completeness: separate award-type groups, independent count queries before
  and after paging, ascending and descending cursor traversals, and exact ID
  plus amount/date agreement;
- persistence: incremental refreshes never delete stored awards.

This is a coherent *new-base-award/current-whole-award* dataset. It is not an
annual account-obligation dataset.

## Calibration results

For NSF DMS FY2024, exact award-ID matching found 1,006 of 1,008 dashboard
records (99.80%). The two characterized residuals are NSF Interagency
Agreements absent from every supported USAspending assistance group. Dollar
coverage was 81.59%, reflecting the different intended-versus-current amount
definitions. This makes USAspending a useful count diagnostic for DMS, but
not a like-for-like dollar validator.

For NIH NIGMS FY2024, RePORTER contains 7,450 application-year records and
$3.098B. USAspending returns 1,266 new base awards touching account 075-0851
and $1.380B of current whole-award obligations. Counts and dollars are only
16.99% and 44.55% of the dashboard values. No tolerance can reconcile an
annual application record with a base award without changing the measured
thing.

## Why DOE onboarding stopped

DOE Office of Science is cleanly identified in the accounting hierarchy by
federal account `089-0222` and its Program Activity codes. It is not cleanly
represented as exclusive award leaves:

- authoritative FY2024 account obligations: $9.282B;
- new base awards touching the account: 1,022 awards with $3.397B in current
  whole-award obligations (36.60% of account flow);
- account-filtered transaction search: $37.342B (402.31% of account flow),
  because transactions/awards can contain other financial-account dollars;
- eight research Program Activities: 660 award memberships but 575 distinct
  awards; 33 awards touch multiple programs and one touches all eight;
- grants-only still double-counts program dollars by 6.91% and omits the
  national-laboratory contracts central to DOE science.

Consequently, summing award records into DOE program offices would materially
double-count dollars, while annual account totals would be neither the new
award cohort nor the filtered whole-transaction series.

## Phase 3.1b resolution

The owner selected the separate obligation-ledger design. Live FY2024 custom-
account testing then established a second critical boundary: File C totals
$8,527,849,368.87, only 91.8772% of the exact $9,281,790,861.20 File A/GTAS
account total. USAspending documents File C as prime-award spending, a subset
of account spending. It therefore cannot be the canonical ledger by itself.

Phase 3.1b uses File B cumulative Program Activity balances, differenced by
submission period, for canonical dollars. File C supplies award-linked
recipient and flow detail. A visible residual (`File B - File C`) retains all
non-award account activity and makes both identities exact. See
`docs/obligation-ledger.md`.

The calibration remains blocked only until the dedicated FY2017-present
backfill, exact GTAS checks, and browser/deploy release bar finish. FY2015–16
are officially unavailable; FY2017 begins with the first DATA Act submission.

Official references:

- [Award-search contract](https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/search/spending_by_award.md)
- [Award-count contract](https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/search/spending_by_award_count.md)
- [DOE Science federal account](https://api.usaspending.gov/api/v2/federal_accounts/089-0222/?fiscal_year=2024)
- [DOE Science Program Activities](https://api.usaspending.gov/api/v2/federal_accounts/089-0222/program_activities/)
- [Custom Account download contract](https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/download/accounts.md)
- [USAspending About the Data](https://www.usaspending.gov/data/about-the-data-download.pdf)
