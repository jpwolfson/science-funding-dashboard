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

## Owner decision required

The recommended path is to redesign the source/store around USAspending File C
financial-account and Program Activity allocation events, then decide how
award counts and allocation-flow dollars coexist in the UI. That preserves the
AAAS-account-structured, ex-post framing.

The alternatives are to change the product definition to “whole-award
exposure touching this account,” or publish a grants-only extramural subset.
Neither alternative is equivalent to Office of Science funding, and neither
should be compared directly with GTAS obligations or enacted budgets.

Official references:

- [Award-search contract](https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/search/spending_by_award.md)
- [Award-count contract](https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/search/spending_by_award_count.md)
- [DOE Science federal account](https://api.usaspending.gov/api/v2/federal_accounts/089-0222/?fiscal_year=2024)
- [DOE Science Program Activities](https://api.usaspending.gov/api/v2/federal_accounts/089-0222/program_activities/)
